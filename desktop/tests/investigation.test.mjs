import assert from "node:assert/strict";
import test from "node:test";
import { InvestigationFlow } from "../src/investigation.ts";

test("one local attempt starts and progress requires its acknowledged ID", () => {
  const flow = new InvestigationFlow();
  const attempt = flow.begin();
  assert.ok(attempt);
  assert.equal(flow.begin(), null);
  assert.equal(flow.requestCancellation(), null);
  assert.equal(flow.acceptsProgress(attempt, "1"), false);
  assert.equal(flow.acknowledge(attempt, "1"), true);
  assert.equal(flow.acknowledge(attempt, "2"), false);
  assert.equal(flow.acceptsProgress(attempt, "1"), true);
  assert.equal(flow.acceptsProgress(attempt, "2"), false);
});

test("cancellation prevents further progress and duplicate requests until settled", () => {
  const flow = new InvestigationFlow();
  const attempt = flow.begin();
  flow.acknowledge(attempt, "1");
  assert.deepEqual(flow.requestCancellation(), { attempt, runId: "1" });
  assert.equal(flow.requestCancellation(), null);
  assert.equal(flow.acceptsProgress(attempt, "1"), false);
  assert.equal(flow.finish(attempt, "2"), false);
  assert.equal(flow.finish(attempt, "1"), true);
  assert.ok(flow.begin());
});

test("late acknowledgement, progress, or completion cannot affect the next attempt", () => {
  const flow = new InvestigationFlow();
  const previous = flow.begin();
  assert.equal(flow.finish(previous, "1"), true); // Result arrived before acknowledgement.
  const current = flow.begin();
  assert.equal(flow.acknowledge(current, "2"), true);
  assert.equal(flow.acknowledge(previous, "1"), false);
  assert.equal(flow.acceptsProgress(previous, "1"), false);
  assert.equal(flow.finish(previous, "1"), false);
  assert.equal(flow.retryCancellation(previous), false);
  assert.equal(flow.acceptsProgress(current, "2"), true);
});

test("only the current attempt can retry a failed cancellation request", () => {
  const flow = new InvestigationFlow();
  const attempt = flow.begin();
  flow.acknowledge(attempt, "1");
  assert.ok(flow.requestCancellation());
  assert.equal(flow.retryCancellation(attempt), true);
  assert.equal(flow.acceptsProgress(attempt, "1"), true);
  assert.ok(flow.requestCancellation());
  assert.equal(flow.finish(attempt, "1"), true);
});
