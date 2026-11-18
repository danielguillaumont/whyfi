use std::{
    io::{self, PipeReader, Read},
    process::{Child, Command, ExitStatus, Stdio},
};

pub(crate) trait Process: Send + 'static {
    fn try_wait(&mut self) -> io::Result<Option<ExitStatus>>;
    fn kill(&mut self) -> io::Result<()>;
    fn read_stdout(&mut self, buffer: &mut [u8]) -> io::Result<usize>;
    fn read_stderr(&mut self, buffer: &mut [u8]) -> io::Result<usize>;
    fn close_pipes(&mut self);
}

pub(crate) struct Sidecar {
    child: Child,
    stdout: Option<PipeReader>,
    stderr: Option<PipeReader>,
}

impl Sidecar {
    pub(crate) fn spawn(command: Command) -> io::Result<Self> {
        let (stdout, stdout_writer) = io::pipe()?;
        let (stderr, stderr_writer) = io::pipe()?;
        Self::spawn_with_pipes(command, (stdout, stdout_writer), (stderr, stderr_writer))
    }

    pub(crate) fn spawn_with_pipes(
        mut command: Command,
        (stdout, stdout_writer): (PipeReader, io::PipeWriter),
        (stderr, stderr_writer): (PipeReader, io::PipeWriter),
    ) -> io::Result<Self> {
        let child = command
            .stdin(Stdio::null())
            .stdout(stdout_writer)
            .stderr(stderr_writer)
            .spawn()?;
        Ok(Self {
            child,
            stdout: Some(stdout),
            stderr: Some(stderr),
        })
    }
}

impl Process for Sidecar {
    fn try_wait(&mut self) -> io::Result<Option<ExitStatus>> {
        self.child.try_wait()
    }

    fn kill(&mut self) -> io::Result<()> {
        self.child.kill()
    }

    fn read_stdout(&mut self, buffer: &mut [u8]) -> io::Result<usize> {
        read_ready(self.stdout.as_mut().unwrap(), buffer)
    }

    fn read_stderr(&mut self, buffer: &mut [u8]) -> io::Result<usize> {
        read_ready(self.stderr.as_mut().unwrap(), buffer)
    }

    fn close_pipes(&mut self) {
        self.stdout.take();
        self.stderr.take();
    }
}

impl Drop for Sidecar {
    fn drop(&mut self) {
        if !matches!(self.child.try_wait(), Ok(Some(_))) {
            // Unexpected worker drop. Normal cleanup keeps ownership until wait succeeds.
            if let Err(error) = self.child.kill() {
                eprintln!("Could not terminate the dropped WHYFI sidecar: {error}");
            }
        }
    }
}

#[cfg(windows)]
fn read_ready(
    pipe: &mut (impl Read + std::os::windows::io::AsRawHandle),
    buffer: &mut [u8],
) -> io::Result<usize> {
    use std::ptr::null_mut;
    use windows_sys::Win32::{
        Foundation::{ERROR_BROKEN_PIPE, ERROR_NO_DATA},
        System::Pipes::PeekNamedPipe,
    };

    let mut available = 0;
    // The handle stays owned by the pipe. This worker is its sole reader, so
    // no other reader can consume the bytes between the peek and the read.
    let ok = unsafe {
        PeekNamedPipe(
            pipe.as_raw_handle(),
            null_mut(),
            0,
            null_mut(),
            &mut available,
            null_mut(),
        )
    };
    if ok == 0 {
        let error = io::Error::last_os_error();
        return match error.raw_os_error().map(|code| code as u32) {
            Some(ERROR_BROKEN_PIPE | ERROR_NO_DATA) => Ok(0),
            _ => Err(error),
        };
    }
    let count = buffer.len().min(available as usize);
    if count == 0 {
        return Ok(0);
    }
    pipe.read(&mut buffer[..count])
}

#[cfg(unix)]
fn read_ready(
    pipe: &mut (impl Read + std::os::fd::AsRawFd),
    buffer: &mut [u8],
) -> io::Result<usize> {
    let mut descriptor = libc::pollfd {
        fd: pipe.as_raw_fd(),
        events: libc::POLLIN,
        revents: 0,
    };
    // The descriptor belongs to the sole reader and stays open during poll.
    match unsafe { libc::poll(&mut descriptor, 1, 0) } {
        0 => Ok(0),
        -1 => {
            let error = io::Error::last_os_error();
            if error.kind() == io::ErrorKind::Interrupted {
                Ok(0)
            } else {
                Err(error)
            }
        }
        _ => pipe.read(buffer),
    }
}
