import { useLayoutEffect, useRef, type ReactNode } from "react";
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
  const active = state.phase === "completed" ? state.view : "diagnose";
  const screen = `${state.phase}:${active}`;
  const previous = useRef({ screen, active });
  const main = useRef<HTMLElement>(null);

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
    <>
      <header className="workspace-header">
        <div className="workspace-brand">
          <span className="brand-mark" aria-hidden="true">W</span>
          <span>WHYFI</span>
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
      </header>
      <main className="workspace-main" ref={main}>
        {children}
      </main>
    </>
  );
}
