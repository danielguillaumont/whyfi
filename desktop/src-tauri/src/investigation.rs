use crate::process::Process;
use crate::sidecar_protocol::{SidecarProtocol, StderrCapture};
use serde::Serialize;
use std::{
    ffi::OsStr,
    future::{poll_fn, Future},
    io,
    pin::{pin, Pin},
    sync::{Arc, Mutex},
    task::Poll,
    time::Duration,
};
use tokio::{
    sync::oneshot,
    time::{sleep, sleep_until, timeout_at, Instant},
};

const DEFAULT_TIMEOUT_SECONDS: u64 = 120;
const CLEANUP_GRACE: Duration = Duration::from_secs(3);

const POLL_INTERVAL: Duration = Duration::from_millis(20);

fn configured_timeout(value: Option<&OsStr>) -> Option<Duration> {
    value
        .and_then(OsStr::to_str)
        .and_then(|value| value.parse::<u64>().ok())
        .filter(|seconds| (5..=600).contains(seconds))
        .map(Duration::from_secs)
}

fn timeout_or_default(value: Option<&OsStr>) -> Duration {
    configured_timeout(value).unwrap_or(Duration::from_secs(DEFAULT_TIMEOUT_SECONDS))
}

pub(crate) fn investigation_timeout() -> Duration {
    let value = std::env::var_os("WHYFI_INVESTIGATION_TIMEOUT_SECONDS");
    if value.is_some() && configured_timeout(value.as_deref()).is_none() {
        eprintln!("Invalid WHYFI_INVESTIGATION_TIMEOUT_SECONDS; using {DEFAULT_TIMEOUT_SECONDS}.");
    }
    timeout_or_default(value.as_deref())
}

#[derive(Clone, Default)]
pub(crate) struct Investigations(Arc<Mutex<InvestigationState>>);

#[derive(Default)]
struct InvestigationState {
    next_id: u64,
    active: Option<ActiveInvestigation>,
}

struct ActiveInvestigation {
    id: String,
    cancel: Option<oneshot::Sender<()>>,
    phase: Phase,
}

#[derive(PartialEq)]
enum Phase {
    Running,
    Finishing,
    ExitUnconfirmed,
}

pub(crate) struct Run {
    pub(crate) id: String,
    state: Investigations,
    cancel: oneshot::Receiver<()>,
    release_on_drop: bool,
}

impl Investigations {
    pub(crate) fn start(&self) -> Result<Run, String> {
        let mut state = self.0.lock().unwrap();
        if let Some(active) = &state.active {
            return Err(match active.phase {
                Phase::Running => "An investigation is already running.".into(),
                Phase::Finishing => "The previous investigation is still finishing or cleaning up.".into(),
                Phase::ExitUnconfirmed => {
                    "WHYFI could not confirm the previous sidecar exited. Close and reopen WHYFI before trying again.".into()
                }
            });
        }
        state.next_id = state
            .next_id
            .checked_add(1)
            .ok_or("No more investigation IDs are available.")?;
        let id = state.next_id.to_string();
        let (signal, cancel) = oneshot::channel();
        state.active = Some(ActiveInvestigation {
            id: id.clone(),
            cancel: Some(signal),
            phase: Phase::Running,
        });
        Ok(Run {
            id,
            state: self.clone(),
            cancel,
            release_on_drop: true,
        })
    }

    pub(crate) fn cancel(&self, id: &str) -> bool {
        let mut state = self.0.lock().unwrap();
        let Some(active) = state
            .active
            .as_mut()
            .filter(|active| active.id == id && active.phase == Phase::Running)
        else {
            return false;
        };
        active
            .cancel
            .take()
            .is_some_and(|signal| signal.send(()).is_ok())
    }
}

impl Run {
    fn release_confirmed(mut self) {
        self.release_on_drop = true;
    }

    fn claim_outcome(&self, proposed: Outcome) -> Outcome {
        let mut state = self.state.0.lock().unwrap();
        let active = state
            .active
            .as_mut()
            .expect("investigation slot owned by run");
        debug_assert_eq!(active.id, self.id);
        active.phase = Phase::Finishing;
        // A cancellation accepted before the outcome is claimed wins.
        if active.cancel.is_none() {
            Outcome::cancelled()
        } else {
            proposed
        }
    }
}

impl Drop for Run {
    fn drop(&mut self) {
        let mut state = self.state.0.lock().unwrap();
        if let Some(active) = state.active.as_mut().filter(|active| active.id == self.id) {
            if self.release_on_drop {
                state.active = None;
            } else {
                active.phase = Phase::ExitUnconfirmed;
            }
        }
    }
}

#[derive(Debug, Serialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub(crate) enum Outcome {
    Completed { result: String },
    Cancelled { message: String },
    TimedOut { message: String },
    Failed { message: String },
}

impl Outcome {
    fn cancelled() -> Self {
        Self::Cancelled {
            message: "Investigation cancelled.".into(),
        }
    }

    fn failed(message: String) -> Self {
        Self::Failed { message }
    }

    fn after_cleanup_notice(mut self, notice: &str) -> Self {
        match &mut self {
            Self::Cancelled { message } | Self::TimedOut { message } | Self::Failed { message } => {
                message.push(' ');
                message.push_str(notice);
            }
            Self::Completed { .. } => return Self::failed(notice.into()),
        }
        self
    }
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct InvestigationResult {
    run_id: String,
    #[serde(flatten)]
    outcome: Outcome,
}

async fn read_result(
    process: &mut impl Process,
    exited: &mut bool,
    mut progress: impl FnMut(&str) -> Result<(), String>,
) -> Result<String, String> {
    let mut protocol = SidecarProtocol::default();
    let mut stderr = StderrCapture::default();
    let mut buffer = [0; 8192];
    let mut status = None;
    loop {
        if !*exited {
            status = process
                .try_wait()
                .map_err(|error| process_error("Process wait failed", &error))?;
            *exited = status.is_some();
        }
        let stdout_count = process
            .read_stdout(&mut buffer)
            .map_err(|error| process_error("Could not read sidecar stdout", &error))?;
        protocol.push(&buffer[..stdout_count], &mut progress)?;
        let stderr_count = process
            .read_stderr(&mut buffer)
            .map_err(|error| process_error("Could not read sidecar stderr", &error))?;
        stderr.push(&buffer[..stderr_count]);
        if stdout_count == 0 && stderr_count == 0 {
            if let Some(status) = status {
                return protocol.finish(status.code(), &stderr);
            }
            sleep(POLL_INTERVAL).await;
        } else {
            // Let the outer cancellation/deadline check run even on busy pipes.
            tokio::task::yield_now().await;
        }
    }
}

fn process_error(context: &str, error: &io::Error) -> String {
    let detail: String = error
        .to_string()
        .chars()
        .take(256)
        .map(|character| {
            if character.is_control() {
                ' '
            } else {
                character
            }
        })
        .collect();
    format!("{context}: {detail}.")
}

enum Work<T> {
    Ready(T),
    Cancelled,
    TimedOut,
}

async fn until_stop<T>(
    future: impl Future<Output = T>,
    cancel: &mut oneshot::Receiver<()>,
    deadline: Instant,
) -> Work<T> {
    let mut future = pin!(future);
    let mut timer = pin!(sleep_until(deadline));
    poll_fn(|context| {
        if Pin::new(&mut *cancel).poll(context).is_ready() {
            return Poll::Ready(Work::Cancelled);
        }
        if Instant::now() >= deadline || timer.as_mut().poll(context).is_ready() {
            return Poll::Ready(Work::TimedOut);
        }
        future.as_mut().poll(context).map(Work::Ready)
    })
    .await
}

fn timeout_outcome() -> Outcome {
    Outcome::TimedOut {
        message: "The investigation timed out.".into(),
    }
}

fn release(run: Run, outcome: Outcome) -> InvestigationResult {
    let run_id = run.id.clone();
    drop(run);
    InvestigationResult { run_id, outcome }
}

#[derive(Default)]
struct CleanupErrors {
    kill: Option<String>,
    wait: Option<String>,
}

async fn cleanup(run: Run, mut process: impl Process, errors: Arc<Mutex<CleanupErrors>>) -> bool {
    process.close_pipes();
    let kill_errors = errors.clone();
    let killed = tauri::async_runtime::spawn_blocking(move || {
        // The direct child may have already exited since the last poll.
        match process.try_wait() {
            Ok(Some(_)) => return None,
            Ok(None) => {}
            Err(error) => record_wait_error(&kill_errors, &error),
        }
        if let Err(error) = process.kill() {
            let message = process_error("Could not terminate the sidecar", &error);
            kill_errors.lock().unwrap().kill = Some(message.clone());
            eprintln!("{message}");
        }
        Some(process)
    })
    .await;
    match killed {
        Ok(Some(mut process)) => loop {
            match process.try_wait() {
                Ok(Some(_)) => break,
                Ok(None) => {}
                Err(error) => record_wait_error(&errors, &error),
            }
            sleep(POLL_INTERVAL).await;
        },
        Ok(None) => {}
        Err(error) => {
            let message = process_error("Sidecar cleanup worker failed", &io::Error::other(error));
            eprintln!("{message}");
            errors.lock().unwrap().kill = Some(message);
            return false;
        }
    }
    run.release_confirmed();
    true
}

fn record_wait_error(errors: &Mutex<CleanupErrors>, error: &io::Error) {
    let message = process_error("Could not confirm sidecar exit", error);
    let first = {
        let mut errors = errors.lock().unwrap();
        if errors.wait.is_some() {
            false
        } else {
            errors.wait = Some(message.clone());
            true
        }
    };
    if first {
        eprintln!("{message}");
    }
}

async fn finish_sidecar(
    run: Run,
    process: impl Process,
    mut outcome: Outcome,
    cleanup_deadline: Instant,
) -> InvestigationResult {
    let run_id = run.id.clone();
    let errors = Arc::new(Mutex::new(CleanupErrors::default()));
    let worker = tauri::async_runtime::spawn(cleanup(run, process, errors.clone()));
    let cleanup_result = timeout_at(cleanup_deadline, worker).await;
    {
        let errors = errors.lock().unwrap();
        for error in [&errors.kill, &errors.wait].into_iter().flatten() {
            outcome = outcome.after_cleanup_notice(error);
        }
    }
    if !matches!(cleanup_result, Ok(Ok(true))) {
        outcome = outcome.after_cleanup_notice(
            "Sidecar exit has not been confirmed. New investigations are blocked until cleanup completes.",
        );
    }
    InvestigationResult { run_id, outcome }
}

pub(crate) async fn investigate<P: Process>(
    mut run: Run,
    launch: impl FnOnce() -> Result<P, String> + Send + 'static,
    deadline: Instant,
    progress: impl FnMut(&str) -> Result<(), String>,
) -> InvestigationResult {
    let probe_deadline = deadline - CLEANUP_GRACE;
    if run.cancel.try_recv().is_ok() || Instant::now() >= probe_deadline {
        let outcome = run.claim_outcome(timeout_outcome());
        return release(run, outcome);
    }
    run.release_on_drop = false;
    let mut launch = tauri::async_runtime::spawn_blocking(launch);
    let process = match until_stop(&mut launch, &mut run.cancel, probe_deadline).await {
        Work::Ready(Ok(Ok(process))) => process,
        Work::Ready(Ok(Err(error))) => {
            run.release_on_drop = true;
            let outcome = run.claim_outcome(Outcome::failed(error));
            return release(run, outcome);
        }
        Work::Ready(Err(error)) => {
            let outcome = run.claim_outcome(Outcome::failed(format!(
                "Diagnostic engine launch worker failed. Close and reopen WHYFI: {error}"
            )));
            return release(run, outcome);
        }
        stop => {
            let outcome = run.claim_outcome(match stop {
                Work::Cancelled => Outcome::cancelled(),
                _ => timeout_outcome(),
            });
            let cleanup_deadline = deadline.min(Instant::now() + CLEANUP_GRACE);
            return match timeout_at(cleanup_deadline, &mut launch).await {
                Ok(Ok(Ok(process))) => {
                    finish_sidecar(run, process, outcome, cleanup_deadline).await
                }
                Ok(Ok(Err(_))) => {
                    run.release_on_drop = true;
                    release(run, outcome)
                }
                Ok(Err(error)) => release(
                    run,
                    outcome.after_cleanup_notice(&format!(
                        "Sidecar launch worker failed. Close and reopen WHYFI: {error}"
                    )),
                ),
                Err(_) => {
                    let result = InvestigationResult {
                        run_id: run.id.clone(),
                        outcome: outcome.after_cleanup_notice(
                            "Sidecar startup is still pending. New investigations are blocked until cleanup completes.",
                        ),
                    };
                    tauri::async_runtime::spawn(async move {
                        match launch.await {
                            Ok(Ok(process)) => {
                                cleanup(run, process, Arc::default()).await;
                            }
                            Ok(Err(_)) => run.release_confirmed(),
                            Err(error) => eprintln!("Sidecar launch worker failed: {error}"),
                        }
                    });
                    result
                }
            };
        }
    };

    supervise_sidecar(run, process, deadline, progress).await
}

async fn supervise_sidecar(
    mut run: Run,
    mut process: impl Process,
    deadline: Instant,
    progress: impl FnMut(&str) -> Result<(), String>,
) -> InvestigationResult {
    let probe_deadline = deadline - CLEANUP_GRACE;
    let mut exited = false;
    let proposed = match until_stop(
        read_result(&mut process, &mut exited, progress),
        &mut run.cancel,
        probe_deadline,
    )
    .await
    {
        Work::Ready(_) if Instant::now() >= probe_deadline => timeout_outcome(),
        Work::Ready(Ok(result)) => Outcome::Completed { result },
        Work::Ready(Err(error)) => Outcome::failed(error),
        Work::Cancelled => Outcome::cancelled(),
        Work::TimedOut => timeout_outcome(),
    };
    let outcome = run.claim_outcome(proposed);
    if exited {
        drop(process);
        run.release_on_drop = true;
        return release(run, outcome);
    }
    finish_sidecar(
        run,
        process,
        outcome,
        deadline.min(Instant::now() + CLEANUP_GRACE),
    )
    .await
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::process::Sidecar;
    use std::{
        io::Write,
        process::{Command, ExitStatus},
        sync::Barrier,
        thread,
    };
    use tauri::async_runtime::{block_on, spawn};

    const RESULT: &str = r#"{"type":"result","diagnosis":{"code":"unknown","title":"Inconclusive","confidence":null,"summary":"Unavailable","evidence":[],"recommendation":null},"details":{}}"#;

    fn deadline() -> Instant {
        Instant::now() + Duration::from_secs(10)
    }

    struct FakeProcess {
        wait: Box<dyn FnMut() -> io::Result<Option<ExitStatus>> + Send>,
        kill: Option<Box<dyn FnOnce() -> io::Result<()> + Send>>,
        output: Option<Vec<u8>>,
    }

    impl Process for FakeProcess {
        fn try_wait(&mut self) -> io::Result<Option<ExitStatus>> {
            (self.wait)()
        }
        fn kill(&mut self) -> io::Result<()> {
            (self.kill.take().unwrap())()
        }
        fn read_stdout(&mut self, buffer: &mut [u8]) -> io::Result<usize> {
            let Some(output) = self.output.take() else {
                return Ok(0);
            };
            buffer[..output.len()].copy_from_slice(&output);
            Ok(output.len())
        }
        fn read_stderr(&mut self, _: &mut [u8]) -> io::Result<usize> {
            Ok(0)
        }
        fn close_pipes(&mut self) {}
    }

    fn exit_status() -> ExitStatus {
        #[cfg(unix)]
        use std::os::unix::process::ExitStatusExt;
        #[cfg(windows)]
        use std::os::windows::process::ExitStatusExt;
        ExitStatus::from_raw(0)
    }

    #[test]
    fn timeout_values() {
        assert_eq!(timeout_or_default(None).as_secs(), 120);
        for (value, expected) in [
            ("5", 5),
            ("600", 600),
            ("4", 120),
            ("601", 120),
            ("", 120),
            ("-5", 120),
            ("5.5", 120),
            ("invalid", 120),
        ] {
            assert_eq!(
                timeout_or_default(Some(OsStr::new(value))).as_secs(),
                expected
            );
        }
    }

    #[test]
    fn simultaneous_starts_and_stale_cancellation() {
        let manager = Investigations::default();
        let previous = manager.start().unwrap().id.clone();
        let barrier = Barrier::new(2);
        let (first, second) = thread::scope(|scope| {
            let first = scope.spawn(|| {
                barrier.wait();
                manager.start()
            });
            let second = scope.spawn(|| {
                barrier.wait();
                manager.start()
            });
            (first.join().unwrap(), second.join().unwrap())
        });
        let run = match (first, second) {
            (Ok(run), Err(_)) | (Err(_), Ok(run)) => run,
            _ => panic!("exactly one start should succeed"),
        };
        assert!(!manager.cancel(&previous));
        assert!(manager.cancel(&run.id));
        assert!(!manager.cancel(&run.id));
    }

    #[test]
    fn cancellation_and_completion_claim_orders() {
        let manager = Investigations::default();
        let completed = || Outcome::Completed {
            result: RESULT.into(),
        };
        let first = manager.start().unwrap();
        assert!(manager.cancel(&first.id));
        assert!(matches!(
            first.claim_outcome(completed()),
            Outcome::Cancelled { .. }
        ));
        drop(first);
        let next = manager.start().unwrap();
        assert!(matches!(
            next.claim_outcome(completed()),
            Outcome::Completed { .. }
        ));
        assert!(!manager.cancel(&next.id));
    }

    #[test]
    fn cancellation_before_spawn_skips_launch() {
        block_on(async {
            let manager = Investigations::default();
            let run = manager.start().unwrap();
            assert!(manager.cancel(&run.id));
            let result =
                investigate::<FakeProcess>(run, || panic!("launch called"), deadline(), |_| Ok(()))
                    .await;
            assert!(matches!(result.outcome, Outcome::Cancelled { .. }));
            assert!(manager.start().is_ok());
        });
    }

    #[test]
    fn spawn_failure_releases_slot() {
        block_on(async {
            let manager = Investigations::default();
            let result = investigate::<FakeProcess>(
                manager.start().unwrap(),
                || Err("fixture spawn failure".into()),
                deadline(),
                |_| Ok(()),
            )
            .await;
            assert!(
                matches!(result.outcome, Outcome::Failed { message } if message.contains("fixture spawn failure"))
            );
            assert!(manager.start().is_ok());
        });
    }

    #[test]
    fn malformed_output_terminates_and_reaps_before_retry() {
        block_on(async {
            let manager = Investigations::default();
            let (killed, mut kill_signal) = oneshot::channel();
            let result = investigate(
                manager.start().unwrap(),
                move || {
                    Ok(FakeProcess {
                        wait: Box::new(move || {
                            Ok(kill_signal.try_recv().is_ok().then(exit_status))
                        }),
                        kill: Some(Box::new(move || {
                            killed.send(()).unwrap();
                            Ok(())
                        })),
                        output: Some(b"{invalid}\n".to_vec()),
                    })
                },
                deadline(),
                |_| Ok(()),
            )
            .await;
            assert!(
                matches!(result.outcome, Outcome::Failed { message } if message.contains("Invalid WHYFI sidecar JSON"))
            );
            assert!(manager.start().is_ok());
        });
    }

    #[test]
    fn direct_exit_and_retry_with_real_stdout_and_stderr_still_open() {
        block_on(async {
            let manager = Investigations::default();
            let run = manager.start().unwrap();
            let (stdout, mut stdout_writer) = io::pipe().unwrap();
            let (stderr, mut stderr_writer) = io::pipe().unwrap();
            writeln!(
                stdout_writer,
                r#"{{"type":"progress","message":"Checking DNS"}}"#
            )
            .unwrap();
            writeln!(stdout_writer, "{RESULT}").unwrap();
            stderr_writer.write_all(b"fixture stderr").unwrap();
            let child_stdout = stdout_writer.try_clone().unwrap();
            let child_stderr = stderr_writer.try_clone().unwrap();

            let mut messages = Vec::new();
            let result = investigate(
                run,
                move || {
                    #[cfg(windows)]
                    let mut command = Command::new(
                        std::path::PathBuf::from(std::env::var_os("SystemRoot").unwrap())
                            .join("System32")
                            .join("cmd.exe"),
                    );
                    #[cfg(windows)]
                    command.args(["/D", "/C", "exit 0"]);
                    #[cfg(unix)]
                    let command = {
                        let mut command = Command::new("/bin/sh");
                        command.args(["-c", "exit 0"]);
                        command
                    };
                    Sidecar::spawn_with_pipes(
                        command,
                        (stdout, child_stdout),
                        (stderr, child_stderr),
                    )
                    .map_err(|error| error.to_string())
                },
                deadline(),
                |message| {
                    messages.push(message.to_owned());
                    Ok(())
                },
            )
            .await;
            assert!(matches!(result.outcome, Outcome::Completed { result } if result == RESULT));
            assert_eq!(messages, ["Checking DNS"]);
            assert!(manager.start().is_ok());
            // Another writer stayed open on each pipe, as with inherited handles.
            drop((stdout_writer, stderr_writer));
        });
    }

    async fn expect_retry(manager: &Investigations) {
        timeout_at(deadline(), async {
            while manager.start().is_err() {
                sleep(POLL_INTERVAL).await;
            }
        })
        .await
        .unwrap();
    }

    #[test]
    fn pending_launch_keeps_slot_until_late_child_is_terminated() {
        block_on(async {
            let manager = Investigations::default();
            let run = manager.start().unwrap();
            let id = run.id.clone();
            let (entered, starting) = oneshot::channel();
            let (finish_launch, resume) = std::sync::mpsc::channel();
            let (killed, mut kill_signal) = oneshot::channel();
            let task = spawn(investigate(
                run,
                move || {
                    entered.send(()).unwrap();
                    resume.recv().map_err(|error| error.to_string())?;
                    Ok(FakeProcess {
                        wait: Box::new(move || {
                            Ok(kill_signal.try_recv().is_ok().then(exit_status))
                        }),
                        kill: Some(Box::new(move || {
                            killed.send(()).unwrap();
                            Ok(())
                        })),
                        output: None,
                    })
                },
                deadline(),
                |_| Ok(()),
            ));
            timeout_at(deadline(), starting).await.unwrap().unwrap();
            assert!(manager.cancel(&id));
            let result = timeout_at(deadline(), task).await.unwrap().unwrap();
            assert!(
                matches!(result.outcome, Outcome::Cancelled { message } if message.contains("startup is still pending"))
            );
            assert!(manager.start().is_err());
            finish_launch.send(()).unwrap();
            expect_retry(&manager).await;
        });
    }

    #[test]
    fn blocked_termination_does_not_extend_deadline_or_release_slot() {
        block_on(async {
            let manager = Investigations::default();
            let mut run = manager.start().unwrap();
            run.release_on_drop = false;
            let (entered, killing) = oneshot::channel();
            let (continue_kill, resume) = std::sync::mpsc::channel();
            let mut exited = false;
            let (killed, mut kill_signal) = oneshot::channel();
            let process = FakeProcess {
                wait: Box::new(move || {
                    exited |= kill_signal.try_recv().is_ok();
                    Ok(exited.then(exit_status))
                }),
                kill: Some(Box::new(move || {
                    entered.send(()).unwrap();
                    resume.recv().map_err(io::Error::other)?;
                    killed.send(()).unwrap();
                    Ok(())
                })),
                output: None,
            };
            let outcome = run.claim_outcome(timeout_outcome());
            let task = spawn(finish_sidecar(
                run,
                process,
                outcome,
                Instant::now() + Duration::from_millis(100),
            ));
            timeout_at(deadline(), killing).await.unwrap().unwrap();
            let result = timeout_at(deadline(), task).await.unwrap().unwrap();
            assert!(
                matches!(result.outcome, Outcome::TimedOut { message } if message.contains("blocked"))
            );
            assert!(manager.start().is_err());
            continue_kill.send(()).unwrap();
            expect_retry(&manager).await;
        });
    }

    #[test]
    fn deadline_cannot_return_queued_result_before_exit_is_confirmed() {
        block_on(async {
            let manager = Investigations::default();
            let (killed, mut kill_signal) = oneshot::channel();
            let result = investigate(
                manager.start().unwrap(),
                move || {
                    Ok(FakeProcess {
                        wait: Box::new(move || {
                            Ok(kill_signal.try_recv().is_ok().then(exit_status))
                        }),
                        kill: Some(Box::new(move || {
                            killed.send(()).unwrap();
                            Ok(())
                        })),
                        output: Some(format!("{RESULT}\n").into_bytes()),
                    })
                },
                Instant::now() + CLEANUP_GRACE + Duration::from_millis(100),
                |_| Ok(()),
            )
            .await;
            assert!(matches!(result.outcome, Outcome::TimedOut { .. }));
            assert!(manager.start().is_ok());
        });
    }

    #[test]
    fn wait_error_after_pipes_close_is_retained_and_does_not_confirm_exit() {
        block_on(async {
            let manager = Investigations::default();
            let mut run = manager.start().unwrap();
            run.release_on_drop = false;
            let (observed, saw_error) = oneshot::channel();
            let mut observed = Some(observed);
            let (allow_exit, mut exit) = oneshot::channel();
            let process = FakeProcess {
                wait: Box::new(move || {
                    if exit.try_recv().is_ok() {
                        return Ok(Some(exit_status()));
                    }
                    if let Some(observed) = observed.take() {
                        observed.send(()).unwrap();
                    }
                    Err(io::Error::other("fixture wait failed\nwith details"))
                }),
                kill: Some(Box::new(|| Ok(()))),
                output: None,
            };
            let outcome = run.claim_outcome(Outcome::cancelled());
            let task = spawn(finish_sidecar(
                run,
                process,
                outcome,
                Instant::now() + Duration::from_millis(250),
            ));
            saw_error.await.unwrap();
            let result = task.await.unwrap();
            assert!(matches!(result.outcome, Outcome::Cancelled { message }
                if message.contains("fixture wait failed with details") && message.contains("blocked")));
            assert!(manager.start().is_err());
            allow_exit.send(()).unwrap();
            expect_retry(&manager).await;
        });
    }

    #[test]
    fn cancellation_reports_kill_error_and_recovers_after_confirmed_exit() {
        block_on(async {
            let manager = Investigations::default();
            let run = manager.start().unwrap();
            let id = run.id.clone();
            let (started, ready) = oneshot::channel();
            let mut started = Some(started);
            let (allow_exit, mut exit) = oneshot::channel();
            let task = spawn(investigate(
                run,
                move || {
                    Ok(FakeProcess {
                        wait: Box::new(move || {
                            if let Some(started) = started.take() {
                                started.send(()).unwrap();
                            }
                            Ok(exit.try_recv().is_ok().then(exit_status))
                        }),
                        kill: Some(Box::new(move || {
                            allow_exit.send(()).unwrap();
                            Err(io::Error::other("fixture termination failure"))
                        })),
                        output: None,
                    })
                },
                deadline(),
                |_| Ok(()),
            ));
            ready.await.unwrap();
            assert!(manager.cancel(&id));
            let result = task.await.unwrap();
            assert!(matches!(result.outcome, Outcome::Cancelled { message }
                if message.contains("fixture termination failure") && !message.contains("blocked")));
            assert!(manager.start().is_ok());
        });
    }
}
