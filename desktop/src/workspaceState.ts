import type { Diagnosis, DiagnosticDetails } from "./diagnosticTypes";

export type Destination = "diagnose" | "result" | "evidence";
export type WorkspaceState =
  | { phase: "ready" }
  | { phase: "running"; progress: string; canCancel: boolean; cancelling: boolean }
  | { phase: "cancelled" | "timed_out" | "failed"; message: string }
  | { phase: "completed"; view: Destination; diagnosis: Diagnosis; details: DiagnosticDetails | null };

export type WorkspaceAction =
  | { type: "start" | "acknowledge" | "cancelling" }
  | { type: "progress"; message: string }
  | { type: "cancelStatus"; message: string; retry: boolean }
  | { type: "interrupted"; phase: "cancelled" | "timed_out" | "failed"; message: string }
  | { type: "result"; diagnosis: Diagnosis; details: DiagnosticDetails }
  | { type: "preview"; diagnosis: Diagnosis }
  | { type: "navigate"; view: Destination };

export const initialWorkspace: WorkspaceState = { phase: "ready" };

export function canNavigate(state: WorkspaceState, view: Destination) {
  return view === "diagnose" ||
    (state.phase === "completed" && (view === "result" || state.details !== null));
}

export function workspaceReducer(state: WorkspaceState, action: WorkspaceAction): WorkspaceState {
  switch (action.type) {
    case "start":
      return state.phase === "running" ? state : {
        phase: "running", progress: "Preparing diagnostic engine…", canCancel: false, cancelling: false,
      };
    case "acknowledge":
      return state.phase === "running" ? { ...state, canCancel: true } : state;
    case "progress":
      return state.phase === "running" && !state.cancelling ? { ...state, progress: action.message } : state;
    case "cancelling":
      return state.phase === "running" && state.canCancel && !state.cancelling
        ? { ...state, canCancel: false, cancelling: true, progress: "Cancelling investigation…" } : state;
    case "cancelStatus":
      return state.phase === "running" && state.cancelling
        ? { ...state, canCancel: action.retry, cancelling: !action.retry, progress: action.message } : state;
    case "interrupted":
      return state.phase === "running" ? { phase: action.phase, message: action.message } : state;
    case "result":
      return state.phase === "running"
        ? { phase: "completed", view: "result", diagnosis: action.diagnosis, details: action.details } : state;
    case "preview":
      return state.phase !== "running"
        ? { phase: "completed", view: "result", diagnosis: action.diagnosis, details: null } : state;
    case "navigate":
      return state.phase === "completed" && canNavigate(state, action.view)
        ? { ...state, view: action.view } : state;
  }
}
