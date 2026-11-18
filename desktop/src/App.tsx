import { AppShell } from "./AppShell";
import { DiagnosisScreen } from "./DiagnosisScreen";
import { ResultOverview } from "./ResultOverview";
import { TechnicalEvidence } from "./TechnicalEvidence";
import { useInvestigation } from "./useInvestigation";
import "./design-tokens.css";
import "./App.css";

export default function App() {
  const { state, start, cancel, navigate, preview } = useInvestigation();

  return (
    <AppShell state={state} navigate={navigate}>
      {state.phase === "completed" && state.view === "result" ? (
        <ResultOverview
          diagnosis={state.diagnosis}
          hasEvidence={state.details !== null}
          start={start}
          showEvidence={() => navigate("evidence")}
        />
      ) : state.phase === "completed" && state.view === "evidence" && state.details ? (
        <TechnicalEvidence details={state.details} onBack={() => navigate("result")} />
      ) : (
        <DiagnosisScreen state={state} start={start} cancel={cancel} preview={preview} />
      )}
    </AppShell>
  );
}
