import assert from "node:assert/strict";
import test from "node:test";
import { canNavigate, initialWorkspace, workspaceReducer as reduce } from "../src/workspaceState.ts";

const diagnosis = { code: "unknown", title: "Inconclusive", confidence: null, summary: "", evidence: [], recommendation: null };
const details = { collection_errors: [{ check: "dns", message: "Unavailable" }] };

test("Result and Evidence unlock on completion and share the same investigation", () => {
  const running = reduce(initialWorkspace, { type: "start" });
  for (const state of [initialWorkspace, running]) {
    assert.equal(canNavigate(state, "diagnose"), true);
    for (const view of ["result", "evidence"]) {
      assert.equal(canNavigate(state, view), false);
      assert.equal(reduce(state, { type: "navigate", view }), state);
    }
  }
  const result = reduce(running, { type: "result", diagnosis, details });
  assert.equal(result.view, "result");
  assert.equal(canNavigate(result, "evidence"), true);
  const evidence = reduce(result, { type: "navigate", view: "evidence" });
  assert.equal(evidence.view, "evidence");
  assert.equal(evidence.details, details);
  assert.equal(reduce(evidence, { type: "navigate", view: "result" }).diagnosis, diagnosis);
  assert.equal(canNavigate(reduce(evidence, { type: "start" }), "evidence"), false);
});

test("acknowledgement unlocks Cancel, progress stays frozen during cancellation, and retry recovers", () => {
  const starting = reduce(initialWorkspace, { type: "start" });
  assert.equal(starting.canCancel, false);
  assert.equal(reduce(starting, { type: "start" }), starting);
  assert.equal(reduce(starting, { type: "preview", diagnosis }), starting);
  const active = reduce(starting, { type: "acknowledge" });
  assert.equal(active.canCancel, true);
  const cancelling = reduce(active, { type: "cancelling" });
  assert.equal(cancelling.canCancel, false);
  assert.equal(reduce(cancelling, { type: "progress", message: "Late progress" }), cancelling);
  const recover = reduce(cancelling, { type: "cancelStatus", retry: true, message: "Retry Cancel" });
  assert.equal(recover.canCancel, true);
  assert.equal(recover.cancelling, false);
});

test("terminal failures remain distinct and cannot be updated by stray progress", () => {
  for (const phase of ["cancelled", "timed_out", "failed"]) {
    const run = reduce(initialWorkspace, { type: "start" });
    const interrupted = reduce(run, { type: "interrupted", phase, message: "Outcome detail" });
    assert.deepEqual(interrupted, { phase, message: "Outcome detail" });
    assert.equal(reduce(interrupted, { type: "progress", message: "Late update" }), interrupted);
    assert.equal(reduce(interrupted, { type: "result", diagnosis, details }), interrupted);
    assert.equal(reduce(interrupted, { type: "start" }).phase, "running");
  }
});

test("development previews expose an overview without inventing evidence", () => {
  const preview = reduce(initialWorkspace, { type: "preview", diagnosis });
  assert.equal(preview.view, "result");
  assert.equal(canNavigate(preview, "evidence"), false);
});
