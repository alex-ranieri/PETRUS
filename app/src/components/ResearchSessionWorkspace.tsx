import { useState } from "react";
import { useTranslation } from "react-i18next";
import ResearchEvidenceWorkspace from "./ResearchEvidenceWorkspace";
import ResearchTrail from "./ResearchTrail";
import Findings from "./Findings";
export default function ResearchSessionWorkspace(props: {
  sessionId: number;
  onPaper: (id: number) => void;
  onLibrary: (id: number) => void;
  onError: (message: string) => void;
  onChanged: () => Promise<void>;
}) {
  const { t } = useTranslation();
  const [tab, setTab] = useState<"evidence" | "trail" | "findings">("evidence");
  const [focus, setFocus] = useState<number | undefined>();
  const [claimFocus, setClaimFocus] = useState<number | undefined>();
  const openClaim = (id: number) => {
    setClaimFocus(id);
    setTab("findings");
  };
  const openEvidence = (id: number) => {
    setFocus(id);
    setTab("evidence");
  };
  return (
    <div className="research-session-workspace">
      <div
        className="tabs"
        role="tablist"
        aria-label={t("trail.workspaceTabs")}
      >
        <button
          role="tab"
          aria-selected={tab === "evidence"}
          onClick={() => setTab("evidence")}
        >
          {t("research.evidence")}
        </button>
        <button
          role="tab"
          aria-selected={tab === "trail"}
          onClick={() => setTab("trail")}
        >
          {t("trail.title")}
        </button>
        <button
          role="tab"
          aria-selected={tab === "findings"}
          onClick={() => setTab("findings")}
        >
          {t("claims.title")}
        </button>
      </div>
      {tab === "evidence" ? (
        <ResearchEvidenceWorkspace
          {...props}
          focusEvidenceId={focus}
          onClaim={openClaim}
        />
      ) : tab === "findings" ? (
        <Findings
          {...props}
          focusClaimId={claimFocus}
          onEvidence={openEvidence}
        />
      ) : (
        <ResearchTrail
          onClaim={openClaim}
          sessionId={props.sessionId}
          onEvidence={(id) => {
            setFocus(id);
            setTab("evidence");
          }}
          onLibrary={props.onLibrary}
          onError={props.onError}
        />
      )}
    </div>
  );
}
