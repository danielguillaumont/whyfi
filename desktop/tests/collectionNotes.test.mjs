import assert from "node:assert/strict";
import test from "node:test";
import { collectionNotes } from "../src/collectionNotes.ts";

test("a target with a null toString is omitted without losing the note", () => {
  const entries = JSON.parse('[{"check":"dns","target":{"toString":null},"message":"Lookup unavailable"}]');
  assert.deepEqual(collectionNotes(entries, null), {
    rows: [{ label: "dns", value: "Lookup unavailable" }],
    fallback: undefined,
  });
});

test("invalid checks, targets and messages are never coerced", () => {
  const object = { toString: null };
  assert.deepEqual(collectionNotes([
    { check: object, target: "example.com", message: "Unavailable" },
    { check: null, message: "Missing check" },
    { check: "dns", target: false, message: "Unusable target" },
    { check: "dns", message: object },
    { check: "dns", message: 0 },
    { check: "dns", message: "  " },
    { check: "dns" },
    null,
  ], object), {
    rows: [
      { label: "Check \u2022 example.com", value: "Unavailable" },
      { label: "Check", value: "Missing check" },
      { label: "dns", value: "Unusable target" },
    ],
    fallback: undefined,
  });
});

test("valid scoped notes and the top-level fallback stay visible", () => {
  assert.deepEqual(collectionNotes([
    { check: "gateway", target: "192.0.2.1", message: "Timed out" },
  ], "Duplicate summary"), {
    rows: [{ label: "gateway \u2022 192.0.2.1", value: "Timed out" }],
    fallback: undefined,
  });
  assert.deepEqual(collectionNotes([{ message: null }], "Inventory unavailable"), {
    rows: [], fallback: "Inventory unavailable",
  });
  for (const invalid of [{ toString: null }, null, undefined, false, 0, " "]) {
    assert.deepEqual(collectionNotes([], invalid), { rows: [], fallback: undefined });
  }
});
