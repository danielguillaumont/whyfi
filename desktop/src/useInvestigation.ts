import { useReducer, useState } from "react";
import { Channel, invoke } from "@tauri-apps/api/core";
import type { Diagnosis, ResultEvent } from "./diagnosticTypes";
import { InvestigationFlow } from "./investigation";
import { initialWorkspace, workspaceReducer, type Destination } from "./workspaceState";

type InvestigationEvent =
  | { type: "started"; runId: string }
  | { type: "progress"; runId: string; message: string };

type InvestigationOutcome =
  | { type: "completed"; runId: string; result: string }
  | { type: "cancelled" | "timed_out" | "failed"; runId: string; message: string };

export function useInvestigation() {
  const [flow] = useState(() => new InvestigationFlow());
  const [state, dispatch] = useReducer(workspaceReducer, initialWorkspace);

  async function start() {
    const attempt = flow.begin();
    if (!attempt) return;
    dispatch({ type: "start" });

    let events: Channel<InvestigationEvent> | undefined;
    try {
      events = new Channel((event: InvestigationEvent) => {
        if (event.type === "started" && flow.acknowledge(attempt, event.runId)) {
          dispatch({ type: "acknowledge" });
        } else if (event.type === "progress" && flow.acceptsProgress(attempt, event.runId)) {
          dispatch({ type: "progress", message: event.message });
        }
      });
      const outcome = await invoke<InvestigationOutcome>("start_diagnosis", { events });
      if (!flow.isCurrent(attempt)) return;
      if (outcome.type === "completed") {
        const result = JSON.parse(outcome.result) as ResultEvent;
        if (result.type !== "result") throw new Error("WHYFI did not return a final diagnostic result.");
        if (flow.finish(attempt, outcome.runId)) {
          dispatch({ type: "result", diagnosis: result.diagnosis, details: result.details });
        }
      } else if (flow.finish(attempt, outcome.runId)) {
        dispatch({ type: "interrupted", phase: outcome.type, message: outcome.message });
      }
    } catch (error) {
      if (!flow.finish(attempt)) return;
      dispatch({
        type: "interrupted",
        phase: "failed",
        message: error instanceof Error ? error.message : String(error),
      });
    } finally {
      if (events) events.onmessage = () => {};
    }
  }

  async function cancel() {
    const request = flow.requestCancellation();
    if (!request) return;
    dispatch({ type: "cancelling" });
    try {
      const accepted = await invoke<boolean>("cancel_diagnosis", { runId: request.runId });
      if (!accepted && flow.isCurrent(request.attempt)) {
        dispatch({ type: "cancelStatus", message: "Finishing investigation…", retry: false });
      }
    } catch {
      if (flow.retryCancellation(request.attempt)) {
        dispatch({ type: "cancelStatus", message: "Could not request cancellation. Try Cancel again.", retry: true });
      }
    }
  }

  return {
    state, start, cancel,
    navigate: (view: Destination) => dispatch({ type: "navigate", view }),
    preview: (diagnosis: Diagnosis) => dispatch({ type: "preview", diagnosis }),
  };
}
