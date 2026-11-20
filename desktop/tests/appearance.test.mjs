import assert from "node:assert/strict";
import { test } from "node:test";
import { APPEARANCE_STORAGE_KEY, parseAppearance, resolveAppearance } from "../src/appearance.ts";

test("appearance preference accepts only known values", () => {
  assert.equal(parseAppearance("light"), "light");
  assert.equal(parseAppearance("dark"), "dark");
  for (const value of [null, undefined, "", "system", "DARK", "auto", {}, 1]) {
    assert.equal(parseAppearance(value), "system");
  }
  assert.equal(APPEARANCE_STORAGE_KEY, "whyfi.appearance");
});

test("system appearance follows Windows and explicit overrides stay fixed", () => {
  assert.equal(resolveAppearance("system", false), "light");
  assert.equal(resolveAppearance("system", true), "dark");
  assert.equal(resolveAppearance("light", true), "light");
  assert.equal(resolveAppearance("dark", false), "dark");
});
