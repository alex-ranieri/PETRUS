import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  engine,
  errorMessage,
  paperAction,
  type AskResponse,
  type Session,
  type ResearchEvidenceList,
} from "../services/api";

import SaveEvidenceDialog from "./SaveEvidenceDialog";

export default function Ask({
  onPaper,
  onLibrary,
  onError,
  sessionId,
  sessions,
  onSessionsChanged,
}: {
  onPaper: (id: number) => void;
  onLibrary: (id: number) => void;
  onError: (message: string) => void;
  sessionId?: number;
  sessions: Session[];
  onSessionsChanged: () => Promise<void>;
}) {
  const { t } = useTranslation();
  const [question, setQuestion] = useState("");
  const [response, setResponse] = useState<AskResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [highlight, setHighlight] = useState("");
  const [notice, setNotice] = useState("");
  const [saved, setSaved] = useState(false);
  const [targetSession, setTargetSession] = useState<number | "">(
    sessionId ?? "",
  );
  const [picker, setPicker] = useState(false);
  const [pending, setPending] = useState<
    AskResponse["evidence"][number] | null
  >(null);
  const [savedUnits, setSavedUnits] = useState<string[]>([]);
  const [savingEvidence, setSavingEvidence] = useState(false);
  const [researchEventId, setResearchEventId] = useState<number | undefined>();
  useEffect(() => {
    let active = true;
    setSavedUnits([]);
    if (targetSession && response) {
      void engine<ResearchEvidenceList>("research_evidence_list", {
        session_id: targetSession,
      })
        .then((result) => {
          if (active)
            setSavedUnits(
              response.evidence
                .filter((unit) =>
                  result.items.some(
                    (item) =>
                      item.evidence_unit_id === unit.unit_id &&
                      item.paper_id === unit.paper_id &&
                      item.text_snapshot === unit.text,
                  ),
                )
                .map((unit) => unit.unit_id),
            );
        })
        .catch((error) => {
          if (active) onError(errorMessage(error));
        });
    }
    return () => {
      active = false;
    };
  }, [targetSession, response, onError]);
  async function saveEvidence(
    item: AskResponse["evidence"][number],
    session: number,
  ) {
    if (!response) return;
    setSavingEvidence(true);
    try {
      await engine("research_evidence_save", {
        session_id: session,
        response_id: response.response_id,
        evidence: item,
        evidence_label: item.evidence_id,
        research_event_id: researchEventId,
      });
      setSavedUnits((prior) => [...new Set([...prior, item.unit_id])]);
      setPicker(false);
      setPending(null);
    } catch (error) {
      onError(errorMessage(error));
    } finally {
      setSavingEvidence(false);
    }
  }

  const failed = response?.execution_metadata
    ? !["accepted", "no_evidence"].includes(
        response.execution_metadata.final_status,
      )
    : false;
  const answerTitle = failed
    ? t("ask.generationFailed")
    : response?.insufficient_evidence
      ? t("ask.insufficientTitle")
      : t("ask.answer");
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!question.trim() || busy) return;
    setBusy(true);
    setResponse(null);
    setNotice("");
    setSaved(false);
    setResearchEventId(undefined);
    try {
      setResponse(
        await engine<AskResponse>("ask", {
          question,
          ...(targetSession ? { session_id: targetSession } : {}),
        }),
      );
    } catch (error) {
      onError(errorMessage(error));
    } finally {
      setBusy(false);
    }
  }
  function focusEvidence(id: string) {
    setHighlight(id);
    document
      .getElementById(`evidence-${id}`)
      ?.scrollIntoView({ behavior: "smooth", block: "center" });
  }
  async function openEvidence(id: number, page: number | null) {
    try {
      const result = await paperAction(id, "open", page ?? undefined);
      if (page && !result.page_open_supported)
        setNotice(t("ask.pageOpeningNotice"));
    } catch (error) {
      onError(errorMessage(error));
    }
  }
  return (
    <div className="page ask-page">
      <span className="eyebrow">{t("ask.localEvidence")}</span>
      <h1>{t("ask.title")}</h1>
      <p className="subtext">{t("ask.description")}</p>
      <div className="research-target-session">
        <button
          disabled={busy}
          onClick={() => {
            setPending(null);
            setPicker(true);
          }}
        >
          {t("research.chooseTarget")}
        </button>
        {targetSession && (
          <span>
            {sessions.find((session) => session.id === targetSession)?.title}
          </span>
        )}
      </div>
      <form onSubmit={submit} className="ask-form">
        <label htmlFor="ask-question">{t("ask.question")}</label>
        <textarea
          id="ask-question"
          value={question}
          maxLength={2000}
          onChange={(e) => setQuestion(e.target.value)}
          required
        />
        <button className="primary" disabled={busy || !question.trim()}>
          {t(busy ? "ask.working" : "ask.submit")}
        </button>
      </form>
      {response && (
        <>
          {response.trail ? (
            <p
              role={response.trail.state === "failed" ? "alert" : "status"}
              className="hint"
            >
              {t(
                response.trail.state === "failed"
                  ? "trail.persistenceFailed"
                  : "trail.recorded",
              )}
              {response.trail.state === "recorded" &&
                response.trail.session_id &&
                ` · ${sessions.find((session) => session.id === response.trail?.session_id)?.title ?? response.trail.session_id}`}
            </p>
          ) : (
            <p className="hint">{t("trail.exploratory")}</p>
          )}
          <section
            className="ask-answer"
            aria-label={answerTitle}
            role={failed ? "alert" : undefined}
          >
            <h2>{answerTitle}</h2>
            <div className="reading">
              {(failed ? t("ask.failed") : response.answer)
                .split(/(\[E\d+\])/g)
                .map((part, index) =>
                  /^\[E\d+\]$/.test(part) ? (
                    <button
                      className="evidence-citation"
                      key={index}
                      onClick={() => focusEvidence(part.slice(1, -1))}
                    >
                      {part}
                    </button>
                  ) : (
                    <span key={index}>{part}</span>
                  ),
                )}
            </div>
            {failed && response.evidence.length > 0 && (
              <button
                className="secondary"
                onClick={() =>
                  document
                    .getElementById("ask-evidence-heading")
                    ?.scrollIntoView({
                      behavior: "smooth",
                      block: "start",
                    })
                }
              >
                {t("ask.retrievedSources")} · {t("research.saveEvidence")} (
                {response.evidence.length})
              </button>
            )}
            {!!response.limitations.length && (
              <p className="hint">
                {t("ask.limitations")}:{" "}
                {response.limitations
                  .map((code) =>
                    t(`ask.warning.${code}`, {
                      defaultValue: t("ask.checkSources"),
                    }),
                  )
                  .join(" · ")}
              </p>
            )}
            <p className="hint">{t("ask.checkSources")}</p>
            {targetSession &&
              response.execution_metadata?.final_status === "accepted" && (
                <button
                  className="secondary"
                  disabled={saved}
                  onClick={async () => {
                    try {
                      const event = await engine<{ event_id: number }>(
                        "save_ask_event",
                        {
                          session_id: targetSession,
                          response,
                        },
                      );
                      setResearchEventId(event.event_id);
                      setSaved(true);
                    } catch (error) {
                      onError(errorMessage(error));
                    }
                  }}
                >
                  {t(saved ? "ask.saved" : "research.saveAcceptedAnswer")}
                </button>
              )}
          </section>
          <p className="hint">{t("research.cardSaveHint")}</p>
          <h2 id="ask-evidence-heading">
            {t(failed ? "ask.retrievedSources" : "ask.evidence")}
          </h2>
          {failed && <p className="hint">{t("ask.sourcesNotAnswer")}</p>}
          <div className="ask-evidence-grid">
            {response.evidence.map((item) => (
              <article
                id={`evidence-${item.evidence_id}`}
                key={item.evidence_id}
                className={`evidence-card ${highlight === item.evidence_id ? "highlighted" : ""}`}
                tabIndex={-1}
              >
                <h3>
                  {item.evidence_id} · {item.paper_title}
                </h3>
                <p>
                  {item.section} ·{" "}
                  {item.page_start === null
                    ? t("ask.pageUnavailable")
                    : t("ask.pages", {
                        start: item.page_start,
                        end: item.page_end,
                      })}
                </p>
                <small>{t(`ask.provenance.${item.provenance}`)}</small>
                <blockquote>{item.text}</blockquote>
                <button
                  onClick={() =>
                    void openEvidence(item.paper_id, item.page_start)
                  }
                >
                  {t("ask.openPaper")}
                </button>
                <button onClick={() => onLibrary(item.paper_id)}>
                  {t("ask.viewLibrary")}
                </button>
                <button onClick={() => onPaper(item.paper_id)}>
                  {t("ask.paperDetails")}
                </button>
                <button
                  disabled={savingEvidence || savedUnits.includes(item.unit_id)}
                  onClick={() => {
                    if (targetSession) void saveEvidence(item, targetSession);
                    else {
                      setPending(item);
                      setPicker(true);
                    }
                  }}
                >
                  {t(
                    savedUnits.includes(item.unit_id)
                      ? "research.saved"
                      : "research.saveEvidence",
                  )}
                </button>
              </article>
            ))}
          </div>
        </>
      )}
      {notice && <p role="status">{notice}</p>}
      {picker && (
        <SaveEvidenceDialog
          sessions={sessions}
          initialSession={targetSession}
          selectOnly={pending === null}
          onConfirm={async (id) => {
            if (id !== targetSession) {
              setSaved(false);
              setResearchEventId(undefined);
            }
            setTargetSession(id);
            if (pending) await saveEvidence(pending, id);
            else setPicker(false);
          }}
          onCancel={() => {
            setPicker(false);
            setPending(null);
          }}
          onCreated={onSessionsChanged}
          onError={onError}
        />
      )}
    </div>
  );
}
