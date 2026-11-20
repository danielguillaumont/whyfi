import { AppShell } from "./AppShell";
import { DiagnosisScreen } from "./DiagnosisScreen";
import { ResultOverview } from "./ResultOverview";
import { TechnicalEvidence } from "./TechnicalEvidence";
import { useInvestigation } from "./useInvestigation";
import "./design-tokens.css";
import "./App.css";
import "./Checkline.css";

export default function App() {
  const { state, start, cancel, navigate, preview } = useInvestigation();

  return (
    <AppShell state={state} navigate={navigate}>
      {state.phase === "completed" && state.view === "result" ? (
        <ResultOverview
          diagnosis={state.diagnosis}
          details={state.details}
          start={start}
          showEvidence={() => navigate("evidence")}
        />
      ) : state.phase === "completed" && state.view === "evidence" && state.details ? (
        <TechnicalEvidence details={state.details} findings={state.diagnosis.evidence}
          onBack={() => navigate("result")} />
      ) : (
        <DiagnosisScreen state={state} start={start} cancel={cancel} preview={preview} />
      )}
    </AppShell>
  );
}
