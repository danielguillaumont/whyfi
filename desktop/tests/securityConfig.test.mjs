import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

function read(path) {
  return readFileSync(new URL(`../src-tauri/${path}`, import.meta.url), "utf8");
}

const { app } = JSON.parse(read("tauri.conf.json"));
const capability = JSON.parse(read("capabilities/default.json"));

test("production CSP limits bundled assets and network connections", () => {
  assert.deepEqual(app.security.csp, {
    "default-src": "'none'",
    "script-src": "'self'",
    "style-src": "'self'",
    "img-src": "'self'",
    "connect-src": "ipc: http://ipc.localhost",
    "base-uri": "'none'",
    "form-action": "'none'",
    "frame-ancestors": "'none'",
  });
  assert.equal(
    app.security.devCsp["connect-src"],
    "'self' ipc: http://ipc.localhost ws://localhost:1420",
  );
  assert.doesNotMatch(app.security.devCsp["script-src"], /unsafe-eval/);
});

test("the only active capability grants local main-window investigation commands", () => {
  assert.deepEqual(app.security.capabilities, [capability.identifier]);
  assert.deepEqual(app.windows.map(({ label }) => label), ["main"]);
  assert.deepEqual(capability.windows, ["main"]);
  assert.equal(capability.remote, undefined);
  assert.notEqual(capability.local, false);
  assert.deepEqual(capability.permissions, ["allow-investigation"]);
  const commands = read("permissions/investigation.toml").match(/^commands\.allow\s*=\s*(\[.*\])$/m);
  assert.ok(commands);
  assert.deepEqual(JSON.parse(commands[1]), ["start_diagnosis", "cancel_diagnosis"]);
});
