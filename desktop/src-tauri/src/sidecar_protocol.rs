use serde::Deserialize;
use serde_json::Value;

const MAX_RECORD_BYTES: usize = 1024 * 1024;
const MAX_STDERR_BYTES: usize = 8 * 1024;

#[derive(Default)]
pub(crate) struct StderrCapture {
    prefix: Vec<u8>,
    truncated: bool,
}

impl StderrCapture {
    pub(crate) fn push(&mut self, chunk: &[u8]) {
        let retain = chunk.len().min(MAX_STDERR_BYTES - self.prefix.len());
        self.prefix.extend_from_slice(&chunk[..retain]);
        self.truncated |= retain < chunk.len();
    }

    fn diagnostic(&self) -> String {
        let text = String::from_utf8_lossy(&self.prefix);
        let text = text.trim_end();
        if self.truncated {
            if text.trim().is_empty() {
                "[stderr truncated]".into()
            } else {
                format!("{text}\n[stderr truncated]")
            }
        } else {
            text.trim_start().to_owned()
        }
    }
}

#[derive(Deserialize)]
#[serde(tag = "type", rename_all = "lowercase")]
enum Event {
    Progress { message: String },
    Result { diagnosis: Value, details: Value },
    Error { message: String },
}

enum Terminal {
    Result(String),
    Error(String),
}

#[derive(Default)]
pub(crate) struct SidecarProtocol {
    pending: Vec<u8>,
    terminal: Option<Terminal>,
}

impl SidecarProtocol {
    pub(crate) fn push(
        &mut self,
        chunk: &[u8],
        mut on_progress: impl FnMut(&str) -> Result<(), String>,
    ) -> Result<(), String> {
        for part in chunk.split_inclusive(|byte| *byte == b'\n') {
            let line_end = part.strip_suffix(b"\n");
            let bytes = line_end.unwrap_or(part);
            if bytes.len() > MAX_RECORD_BYTES - self.pending.len() {
                return Err(format!(
                    "WHYFI sidecar JSON record exceeds the {MAX_RECORD_BYTES}-byte limit."
                ));
            }
            self.pending.extend_from_slice(bytes);
            if line_end.is_none() {
                break;
            }
            let line = std::str::from_utf8(&self.pending)
                .map_err(|error| format!("Invalid UTF-8 in WHYFI sidecar output: {error}"))?;
            let line = line.strip_suffix('\r').unwrap_or(line);

            if !line.trim().is_empty() {
                let event: Event = serde_json::from_str(line)
                    .map_err(|error| format!("Invalid WHYFI sidecar JSON event: {error}"))?;
                if self.terminal.is_some() {
                    return Err(match event {
                        Event::Progress { .. } => {
                            "WHYFI sidecar sent progress after a terminal event.".into()
                        }
                        _ => "WHYFI sidecar sent more than one terminal event.".into(),
                    });
                }
                match event {
                    Event::Progress { message } => {
                        if message.trim().is_empty() {
                            return Err("WHYFI sidecar sent an empty progress message.".into());
                        }
                        on_progress(line)?;
                    }
                    Event::Result { diagnosis, details } => {
                        validate_result(&diagnosis, &details)?;
                        self.terminal = Some(Terminal::Result(line.to_owned()));
                    }
                    Event::Error { message } => {
                        if message.trim().is_empty() {
                            return Err("WHYFI sidecar sent an empty error message.".into());
                        }
                        self.terminal = Some(Terminal::Error(message));
                    }
                }
            }
            self.pending.clear();
        }
        Ok(())
    }

    pub(crate) fn finish(
        self,
        exit_code: Option<i32>,
        stderr: &StderrCapture,
    ) -> Result<String, String> {
        if !self.pending.is_empty() {
            return Err("WHYFI sidecar ended with a truncated JSON line.".into());
        }
        if let Some(Terminal::Error(message)) = self.terminal {
            return Err(message);
        }
        if exit_code != Some(0) {
            let status = match exit_code {
                Some(code) => format!("exited with code {code}"),
                None => "terminated without an exit code".into(),
            };
            let stderr = stderr.diagnostic();
            return if stderr.is_empty() {
                Err(format!("WHYFI diagnostic engine {status}."))
            } else {
                Err(format!("WHYFI diagnostic engine {status}: {stderr}"))
            };
        }
        match self.terminal {
            Some(Terminal::Result(line)) => Ok(line),
            _ => Err("WHYFI sidecar did not return a final result.".into()),
        }
    }
}

fn validate_result(diagnosis: &Value, details: &Value) -> Result<(), String> {
    let diagnosis = diagnosis.as_object().ok_or_else(|| invalid("diagnosis"))?;

    for (field, path) in [
        ("code", "diagnosis.code"),
        ("title", "diagnosis.title"),
        ("summary", "diagnosis.summary"),
    ] {
        if !diagnosis
            .get(field)
            .and_then(Value::as_str)
            .is_some_and(|value| !value.trim().is_empty())
        {
            return Err(invalid(path));
        }
    }
    if !diagnosis
        .get("confidence")
        .is_some_and(|value| value.is_null() || value.as_u64().is_some_and(|n| n <= 100))
    {
        return Err(invalid("diagnosis.confidence"));
    }
    if !diagnosis
        .get("evidence")
        .and_then(Value::as_array)
        .is_some_and(|items| items.iter().all(Value::is_string))
    {
        return Err(invalid("diagnosis.evidence"));
    }
    if !diagnosis
        .get("recommendation")
        .is_some_and(|value| value.is_null() || value.is_string())
    {
        return Err(invalid("diagnosis.recommendation"));
    }
    validate_details(details)
}

fn invalid(path: &str) -> String {
    format!("Invalid WHYFI sidecar result field: {path}.")
}

type FieldCheck = (&'static str, fn(&Value) -> bool);

// Validate the presentation fields used by React. Other engine details pass through.
fn validate_fields(value: &Value, path: &str, fields: &[FieldCheck]) -> Result<(), String> {
    let object = value.as_object().ok_or_else(|| invalid(path))?;
    for (name, check) in fields {
        if let Some(field) = object.get(*name).filter(|field| !field.is_null()) {
            if !check(field) {
                return Err(invalid(&format!("{path}.{name}")));
            }
        }
    }
    Ok(())
}

fn validate_list(
    value: Option<&Value>,
    path: &str,
    nullable: bool,
    validate_item: impl Fn(&Value, &str) -> Result<(), String>,
) -> Result<(), String> {
    let Some(value) = value else { return Ok(()) };
    if nullable && value.is_null() {
        return Ok(());
    }
    let items = value.as_array().ok_or_else(|| invalid(path))?;
    for (index, item) in items.iter().enumerate() {
        validate_item(item, &format!("{path}[{index}]"))?;
    }
    Ok(())
}

fn validate_ping(value: &Value, path: &str) -> Result<(), String> {
    validate_fields(
        value,
        path,
        &[
            ("target", Value::is_string),
            ("reachable", Value::is_boolean),
            ("average_latency_ms", Value::is_number),
            ("packet_loss_percent", Value::is_number),
            ("jitter_ms", Value::is_number),
        ],
    )
}

fn validate_dns_query(value: &Value, path: &str) -> Result<(), String> {
    validate_fields(
        value,
        path,
        &[
            ("resolver", Value::is_string),
            ("success", Value::is_boolean),
            ("latency_ms", Value::is_number),
            ("error", Value::is_string),
        ],
    )
}

fn validate_details(details: &Value) -> Result<(), String> {
    let details = details.as_object().ok_or_else(|| invalid("details"))?;
    let section = |key| details.get(key).filter(|section| !section.is_null());

    if let Some(connection) = section("connection") {
        validate_fields(
            connection,
            "details.connection",
            &[
                ("adapter_name", Value::is_string),
                ("adapter_type", Value::is_string),
                ("ipv4_address", Value::is_string),
                ("gateway", Value::is_string),
                ("is_up", Value::is_boolean),
                ("speed_mbps", Value::is_number),
                ("mtu", Value::is_number),
            ],
        )?;
    }
    if let Some(gateway) = section("gateway") {
        validate_ping(gateway, "details.gateway")?;
    }
    if let Some(internet) = section("internet") {
        validate_fields(
            internet,
            "details.internet",
            &[
                ("reachable", Value::is_boolean),
                ("targets_reachable", Value::is_number),
                ("targets_tested", Value::is_number),
            ],
        )?;
        validate_list(
            internet.get("probes"),
            "details.internet.probes",
            true,
            validate_ping,
        )?;
    }
    if let Some(dns) = section("dns") {
        validate_fields(
            dns,
            "details.dns",
            &[
                ("healthy", Value::is_boolean),
                ("default_resolver", Value::is_string),
                ("error", Value::is_string),
            ],
        )?;
        if let Some(query) = dns.get("default_query").filter(|query| !query.is_null()) {
            validate_dns_query(query, "details.dns.default_query")?;
        }
        validate_list(
            dns.get("configured_queries"),
            "details.dns.configured_queries",
            false,
            validate_dns_query,
        )?;
    }
    if let Some(wifi) = section("wifi") {
        validate_fields(
            wifi,
            "details.wifi",
            &[
                ("connected", Value::is_boolean),
                ("interface_name", Value::is_string),
                ("error", Value::is_string),
                ("signal_percent", Value::is_number),
                ("radio_type", Value::is_string),
                ("channel", Value::is_number),
                ("receive_rate_mbps", Value::is_number),
                ("transmit_rate_mbps", Value::is_number),
            ],
        )?;
    }
    if let Some(local) = section("local_config") {
        validate_fields(
            local,
            "details.local_config",
            &[
                ("healthy", Value::is_boolean),
                ("likely_dhcp_issue", Value::is_boolean),
            ],
        )?;
        for name in ["active_adapters", "usable_ipv4_adapters"] {
            validate_list(
                local.get(name),
                &format!("details.local_config.{name}"),
                true,
                |item, path| {
                    if item.is_string() {
                        Ok(())
                    } else {
                        Err(invalid(path))
                    }
                },
            )?;
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    const RESULT: &str = r#"{"type": "result", "diagnosis": {"code":"unknown", "title":"Inconclusive", "confidence":null, "summary":"A probe was unavailable.", "evidence":["Probe unavailable"], "recommendation":null}, "details":{"completed":false,"extra":{"future_metric":42}}}"#;
    const ERROR: &str = r#"{"type":"error","message":"Could not collect diagnostics."}"#;

    fn push(protocol: &mut SidecarProtocol, chunk: &[u8]) -> Result<(), String> {
        protocol.push(chunk, |_| Ok(()))
    }

    fn finish(
        protocol: SidecarProtocol,
        exit_code: Option<i32>,
        stderr: &[u8],
    ) -> Result<String, String> {
        let mut capture = StderrCapture::default();
        capture.push(stderr);
        protocol.finish(exit_code, &capture)
    }

    fn padded_progress(record_bytes: usize) -> Vec<u8> {
        let mut record = br#"{"type":"progress","message":"Checking"}"#.to_vec();
        record.resize(record_bytes, b' ');
        record.push(b'\n');
        record
    }

    #[test]
    fn rejects_long_unterminated_record_before_growing_the_buffer() {
        let mut protocol = SidecarProtocol::default();
        let chunk = vec![b'x'; MAX_RECORD_BYTES / 4];
        for _ in 0..4 {
            push(&mut protocol, &chunk).unwrap();
        }
        let error = push(&mut protocol, b"x").unwrap_err();
        assert!(error.contains("JSON record exceeds"));
        assert_eq!(protocol.pending.len(), MAX_RECORD_BYTES);
    }

    #[test]
    fn rejects_oversized_terminated_record_before_buffering_or_forwarding_it() {
        let mut protocol = SidecarProtocol::default();
        let record = padded_progress(MAX_RECORD_BYTES + 1);
        let error = protocol
            .push(&record, |_| panic!("oversized progress forwarded"))
            .unwrap_err();
        assert!(error.contains("JSON record exceeds"));
        assert!(protocol.pending.is_empty());
    }

    #[test]
    fn accepts_record_at_the_limit_with_lf_or_crlf() {
        for crlf in [false, true] {
            let mut protocol = SidecarProtocol::default();
            let mut record = padded_progress(MAX_RECORD_BYTES);
            if crlf {
                record[MAX_RECORD_BYTES - 1] = b'\r';
            }
            let mut count = 0;
            for chunk in record.chunks(MAX_RECORD_BYTES / 3) {
                protocol
                    .push(chunk, |_| {
                        count += 1;
                        Ok(())
                    })
                    .unwrap();
            }
            assert_eq!(count, 1);
            assert!(protocol.pending.is_empty());
        }
    }

    #[test]
    fn accepts_multiple_records_in_one_chunk_larger_than_the_record_limit() {
        let mut protocol = SidecarProtocol::default();
        let record = padded_progress(MAX_RECORD_BYTES * 3 / 4);
        let mut chunk = record.clone();
        chunk.extend_from_slice(&record);
        chunk.extend_from_slice(format!("{RESULT}\n").as_bytes());
        assert!(chunk.len() > MAX_RECORD_BYTES);

        let mut count = 0;
        protocol
            .push(&chunk, |_| {
                count += 1;
                Ok(())
            })
            .unwrap();
        assert_eq!(count, 2);
        assert_eq!(finish(protocol, Some(0), b"").unwrap(), RESULT);
    }

    #[test]
    fn stderr_preserves_the_prefix_and_marks_truncation_only_after_the_limit() {
        let mut stderr = StderrCapture::default();
        let prefix = b"Important context: ";
        stderr.push(prefix);
        stderr.push(&vec![b'x'; MAX_STDERR_BYTES - prefix.len()]);
        assert_eq!(stderr.diagnostic().len(), MAX_STDERR_BYTES);
        for _ in 0..3 {
            stderr.push(&vec![b'y'; MAX_STDERR_BYTES]);
        }
        assert_eq!(stderr.prefix.len(), MAX_STDERR_BYTES);
        let error = SidecarProtocol::default()
            .finish(Some(1), &stderr)
            .unwrap_err();
        assert!(error.contains("exited with code 1: Important context: "));
        assert!(error.ends_with("\n[stderr truncated]"));
        assert!(!stderr.prefix.contains(&b'y'));
    }

    #[test]
    fn every_byte_boundary_preserves_progress_order_and_the_full_result() {
        let stream = format!(
            "{{\"type\":\"progress\",\"message\":\"Checking réseau\"}}\r\n\
             \n{{\"type\":\"progress\",\"message\":\"Checking DNS\"}}\n{RESULT}\r\n"
        );
        let bytes = stream.as_bytes();
        for split in 0..=bytes.len() {
            let mut protocol = SidecarProtocol::default();
            let mut messages = Vec::new();
            for chunk in [&bytes[..split], &bytes[split..]] {
                protocol
                    .push(chunk, |line| {
                        let event: Value = serde_json::from_str(line).unwrap();
                        messages.push(event["message"].as_str().unwrap().to_owned());
                        Ok(())
                    })
                    .unwrap();
            }
            assert_eq!(messages, ["Checking réseau", "Checking DNS"]);
            assert_eq!(finish(protocol, Some(0), b"").unwrap(), RESULT);
        }
    }

    #[test]
    fn rejects_malformed_json_invalid_utf8_and_unexpected_event_types() {
        for (bytes, expected) in [
            (b"{broken}\n".as_slice(), "Invalid WHYFI sidecar JSON"),
            (b"\xff\n".as_slice(), "Invalid UTF-8"),
            (b"{\"type\":\"other\"}\n".as_slice(), "unknown variant"),
            (
                b"{\"type\":\"progress\",\"message\":1}\n".as_slice(),
                "invalid type",
            ),
            (b"{\"type\":\"error\"}\n".as_slice(), "missing field"),
        ] {
            let error = SidecarProtocol::default()
                .push(bytes, |_| {
                    panic!("Invalid events must never reach the desktop")
                })
                .unwrap_err();
            assert!(error.contains(expected), "{error}");
        }
    }

    #[test]
    fn nested_type_does_not_count_as_a_result() {
        let mut protocol = SidecarProtocol::default();
        push(
            &mut protocol,
            b"{\"type\":\"progress\",\"message\":\"Check\",\"metadata\":{\"type\":\"result\"}}\n",
        )
        .unwrap();
        assert!(finish(protocol, Some(0), b"")
            .unwrap_err()
            .contains("final result"));
    }

    #[test]
    fn rejects_truncated_json_and_complete_json_without_a_newline() {
        for line in [RESULT, &RESULT[..RESULT.len() - 3]] {
            let mut protocol = SidecarProtocol::default();
            push(&mut protocol, line.as_bytes()).unwrap();
            assert!(finish(protocol, Some(0), b"")
                .unwrap_err()
                .contains("truncated"));
        }
    }

    #[test]
    fn rejects_any_duplicate_terminal_and_progress_after_terminal() {
        for first in [RESULT, ERROR] {
            for second in [RESULT, ERROR] {
                let mut protocol = SidecarProtocol::default();
                push(&mut protocol, format!("{first}\n").as_bytes()).unwrap();
                let error = push(&mut protocol, format!("{second}\n").as_bytes()).unwrap_err();
                assert!(error.contains("more than one terminal event"));
            }
            let mut protocol = SidecarProtocol::default();
            push(&mut protocol, format!("{first}\n").as_bytes()).unwrap();
            let error = protocol
                .push(b"{\"type\":\"progress\",\"message\":\"Late\"}\n", |_| {
                    panic!("Late progress must never reach the desktop")
                })
                .unwrap_err();
            assert!(error.contains("progress after a terminal event"));
        }
    }

    #[test]
    fn rejects_invalid_required_result_fields() {
        for (field, replacement) in [
            ("code", Value::Null),
            ("title", json!("")),
            ("summary", json!([])),
            ("confidence", json!(101)),
            ("evidence", json!(["valid", 1])),
            ("recommendation", json!(false)),
        ] {
            let mut result: Value = serde_json::from_str(RESULT).unwrap();
            result["diagnosis"][field] = replacement;
            let error = push(
                &mut SidecarProtocol::default(),
                format!("{result}\n").as_bytes(),
            )
            .unwrap_err();
            assert!(error.contains(&format!("diagnosis.{field}")), "{error}");
        }

        let mut result: Value = serde_json::from_str(RESULT).unwrap();
        result["diagnosis"]
            .as_object_mut()
            .unwrap()
            .remove("confidence");
        let error = push(
            &mut SidecarProtocol::default(),
            format!("{result}\n").as_bytes(),
        )
        .unwrap_err();
        assert!(error.contains("diagnosis.confidence"));

        let mut result: Value = serde_json::from_str(RESULT).unwrap();
        result["details"] = json!([]);
        let error = push(
            &mut SidecarProtocol::default(),
            format!("{result}\n").as_bytes(),
        )
        .unwrap_err();
        assert!(error.contains("details"));
    }

    #[test]
    fn rejects_malformed_technical_detail_containers_and_fields() {
        for (details, path) in [
            (Value::Null, "details"),
            (json!({"connection": 3}), "details.connection"),
            (
                json!({"connection": {"adapter_name": []}}),
                "details.connection.adapter_name",
            ),
            (
                json!({"gateway": {"packet_loss_percent": "n/a"}}),
                "details.gateway.packet_loss_percent",
            ),
            (
                json!({"internet": {"probes": "bad"}}),
                "details.internet.probes",
            ),
            (
                json!({"internet": {"probes": [null]}}),
                "details.internet.probes[0]",
            ),
            (
                json!({"internet": {"probes": [{"target": {}}]}}),
                "details.internet.probes[0].target",
            ),
            (
                json!({"dns": {"default_query": []}}),
                "details.dns.default_query",
            ),
            (
                json!({"dns": {"configured_queries": "not an array"}}),
                "details.dns.configured_queries",
            ),
            (
                json!({"dns": {"configured_queries": null}}),
                "details.dns.configured_queries",
            ),
            (
                json!({"dns": {"configured_queries": [3]}}),
                "details.dns.configured_queries[0]",
            ),
            (
                json!({"dns": {"configured_queries": [{"success": "yes"}]}}),
                "details.dns.configured_queries[0].success",
            ),
            (
                json!({"wifi": {"signal_percent": []}}),
                "details.wifi.signal_percent",
            ),
            (
                json!({"local_config": {"active_adapters": {}}}),
                "details.local_config.active_adapters",
            ),
            (
                json!({"local_config": {"usable_ipv4_adapters": [null]}}),
                "details.local_config.usable_ipv4_adapters[0]",
            ),
        ] {
            let mut result: Value = serde_json::from_str(RESULT).unwrap();
            result["details"] = details;
            let error = push(
                &mut SidecarProtocol::default(),
                format!("{result}\n").as_bytes(),
            )
            .unwrap_err();
            assert_eq!(error, invalid(path));
        }
    }

    #[test]
    fn preserves_nullable_technical_details_and_unrecognized_fields() {
        let mut result: Value = serde_json::from_str(RESULT).unwrap();
        result["details"] = json!({
            "connection": null,
            "gateway": {"reachable": null, "packet_loss_percent": null},
            "internet": {"reachable": null, "probes": [{"target": "192.0.2.1", "average_latency_ms": null}]},
            "dns": {"default_query": null, "configured_queries": [{"resolver": "192.0.2.2", "success": null, "error": null}]},
            "wifi": {"connected": null},
            "local_config": {"active_adapters": null, "usable_ipv4_adapters": []},
            "future_metric": {"status": true},
        });
        let line = result.to_string();
        let mut protocol = SidecarProtocol::default();
        push(&mut protocol, format!("{line}\n").as_bytes()).unwrap();
        assert_eq!(finish(protocol, Some(0), b"").unwrap(), line);
    }

    #[test]
    fn rejects_nonzero_exit_even_after_valid_result() {
        let mut protocol = SidecarProtocol::default();
        push(&mut protocol, format!("{RESULT}\n").as_bytes()).unwrap();
        let error = finish(protocol, Some(7), b"process failed\r\n").unwrap_err();
        assert_eq!(
            error,
            "WHYFI diagnostic engine exited with code 7: process failed"
        );
    }

    #[test]
    fn terminal_error_is_returned_without_duplicating_stderr() {
        for exit_code in [Some(0), Some(1)] {
            let mut protocol = SidecarProtocol::default();
            push(&mut protocol, format!("{ERROR}\n").as_bytes()).unwrap();
            assert_eq!(
                finish(protocol, exit_code, b"Could not collect diagnostics.").unwrap_err(),
                "Could not collect diagnostics."
            );
        }
    }
}
