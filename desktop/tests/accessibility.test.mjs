import assert from "node:assert/strict";
import { after, test } from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

const vite = await createServer({
  mode: "production",
  server: { middlewareMode: true, ws: false, watch: null },
  optimizeDeps: { noDiscovery: true, include: [] },
});
after(() => vite.close());

const { DiagnosisScreen } = await vite.ssrLoadModule("/src/DiagnosisScreen.tsx");
const { ResultOverview } = await vite.ssrLoadModule("/src/ResultOverview.tsx");
const render = (Component, props) => renderToStaticMarkup(createElement(Component, props));

test("Cancel is natively disabled before acknowledgement and keeps a focusable button during cancellation", () => {
  const button = state => render(DiagnosisScreen, {
    state: { phase: "running", progress: "Current step", ...state },
  }).match(/<button[^>]*>Cancel<\/button>/)[0];
  assert.match(button({ canCancel: false, cancelling: false }), / disabled=""/);
  const pending = button({ canCancel: false, cancelling: true });
  assert.match(pending, / aria-disabled="true"/);
  assert.doesNotMatch(pending, / disabled=/);
  assert.doesNotMatch(button({ canCancel: true, cancelling: false }), /disabled/);
});

test("cancellation has a focused heading and preserves a cleanup notice without repeating the default outcome", () => {
  const cancelled = message => render(DiagnosisScreen, { state: { phase: "cancelled", message } });
  const normal = cancelled("Investigation cancelled.");
  assert.match(normal, /<h1 tabindex="-1">Investigation cancelled<\/h1>/);
  assert.doesNotMatch(normal, /diagnosis-notice|role="status"/);
  assert.match(cancelled("Investigation cancelled. Cleanup is pending."), /<span>Cleanup is pending\.<\/span>/);
  assert.match(normal, /Start diagnosis/);
});

test("the Result heading exposes the visible status as its accessible description", () => {
  for (const [code, label] of [
    ["healthy", "Healthy"], ["gateway_issue", "Problem found"], ["unknown", "Inconclusive"],
  ]) {
    const markup = render(ResultOverview, {
      diagnosis: { code, title: "Engine conclusion", summary: "Summary", confidence: null },
      details: null,
    });
    assert.match(markup, /<h1 tabindex="-1" aria-describedby="diagnosis-outcome">Engine conclusion<\/h1>/);
    assert.match(markup, new RegExp('id="diagnosis-outcome"[^>]*>.*</span>' + label + '</span>'));
  }
});
