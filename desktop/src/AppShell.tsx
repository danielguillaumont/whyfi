import { useLayoutEffect, useRef, type ReactNode } from "react";
import { useAppearance } from "./useAppearance";
import { canNavigate, type Destination, type WorkspaceState } from "./workspaceState";

const destinations = [
  { id: "diagnose", label: "Diagnose" },
  { id: "result", label: "Result" },
  { id: "evidence", label: "Evidence" },
] as const;

export function AppShell({ state, navigate, children }: {
  state: WorkspaceState;
  navigate: (view: Destination) => void;
  children: ReactNode;
}) {
  const { appearance, updateAppearance } = useAppearance();
  const active = state.phase === "completed" ? state.view : "diagnose";
  const screen = `${state.phase}:${active}`;
  const previous = useRef({ screen, active });
  const main = useRef<HTMLElement>(null);

  // Preserve the existing focus contract, including return to the evidence trigger.
  useLayoutEffect(() => {
    const last = previous.current;
    previous.current = { screen, active };
    if (last.screen === screen) return;
    window.scrollTo(0, 0);
    if (last.active === "evidence" && active === "result") {
      const evidenceButton = main.current?.querySelector<HTMLButtonElement>("[data-evidence-entry]");
      if (evidenceButton) {
        evidenceButton.focus();
        return;
      }
    }
    main.current?.querySelector("h1")?.focus({ preventScroll: true });
  }, [active, screen]);

  return (
    <div className="checkline-app">
      <header className="workspace-header">
        <div className="checkline-header-inner">
          <div className="workspace-brand">
            <img className="brand-mark" src="/whyfi.svg" width={38} height={38} alt="" aria-hidden="true" />
            <div className="checkline-brand-name">
              <span>WHYFI</span>
              <small>Find where the connection fails.</small>
            </div>
          </div>
          <nav className="workspace-nav" aria-label="Workspace">
            {destinations.map(({ id, label }) => (
              <button
                className="nav-button"
                key={id}
                type="button"
                aria-current={id === active ? "page" : undefined}
                disabled={!canNavigate(state, id)}
                onClick={() => navigate(id)}
              >
                {label}
              </button>
            ))}
          </nav>
          <div className="checkline-header-end">
            <div className="checkline-header-context">
              <span className="checkline-context-dot" aria-hidden="true" />
              <span>Local to your device</span>
            </div>
            <label className="checkline-appearance">
              <span>Appearance</span>
              <select aria-label="Appearance" value={appearance} onChange={event => updateAppearance(event.currentTarget.value as typeof appearance)}>
                <option value="system">System</option>
                <option value="light">Light</option>
                <option value="dark">Dark</option>
              </select>
            </label>
          </div>
        </div>
      </header>
      <main className="workspace-main" ref={main}>
        {children}
      </main>
    </div>
  );
}
