import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  engine,
  errorMessage,
  paperAction,
  type EvidenceDecision,
  type SavedEvidence,
  type ResearchEvidenceList,
} from "../services/api";
const decisions: EvidenceDecision[] = ["included", "excluded", "uncertain"];

function EvidenceItem({
  item,
  onUpdate,
  onRemove,
  onPaper,
  onLibrary,
  onError,
  onClaim,
}: {
  onClaim?: (id: number) => void;
  item: SavedEvidence;
  onUpdate: (
    id: number,
    changes: Partial<Pick<SavedEvidence, "decision" | "user_note">>,
  ) => Promise<void>;
  onRemove: (id: number) => Promise<void>;
  onPaper: (id: number) => void;
  onLibrary: (id: number) => void;
  onError: (message: string) => void;
}) {
  const { t } = useTranslation();
  const [note, setNote] = useState(item.user_note);
  const [busy, setBusy] = useState(false);
  async function run(action: () => Promise<void>) {
    setBusy(true);
    try {
      await action();
    } finally {
      setBusy(false);
    }
  }
  return (
    <article
      id={`research-evidence-${item.id}`}
      tabIndex={-1}
      className="evidence-card saved-evidence-card"
      data-evidence-id={item.id}
    >
      <h3>{item.paper_title_snapshot}</h3>
      {item.related_claims?.length ? (
        <div className="evidence-related-claims">
          <small>{t("claims.related")}</small>
          {item.related_claims.map((claim) => (
            <button key={claim.id} onClick={() => onClaim?.(claim.id)}>
              {t("claims.number", { id: claim.id })} ·{" "}
              {t(
                `claims.${claim.archived_at ? "archived" : claim.review_status}`,
              )}
            </button>
          ))}
        </div>
      ) : null}
      <p>
        {item.section_heading_snapshot}
        {item.section_heading_snapshot ? " · " : ""}
        {item.page_start === null
          ? t("ask.pageUnavailable")
          : t("ask.pages", { start: item.page_start, end: item.page_end })}
      </p>
      <small>
        {t(`ask.provenance.${item.provenance_level}`)} ·{" "}
        {t(`research.origin.${item.origin_type}`)}
      </small>
      {item.question_snapshot && (
        <p className="hint">
          {t("ask.question")}: {item.question_snapshot}
          {item.evidence_label_snapshot
            ? ` · ${item.evidence_label_snapshot}`
            : ""}
        </p>
      )}
      <blockquote>{item.text_snapshot}</blockquote>
      <p className="hint">{t("research.snapshotNotice")}</p>
      <label>
        {t("research.decision")}
        <select
          aria-label={t("research.decision")}
          value={item.decision}
          disabled={busy}
          onChange={(e) =>
            void run(() =>
              onUpdate(item.id, {
                decision: e.target.value as EvidenceDecision,
              }),
            )
          }
        >
          {decisions.map((decision) => (
            <option key={decision} value={decision}>
              {t(`research.${decision}`)}
            </option>
          ))}
        </select>
      </label>
      <div className="research-human-note">
        <label>
          {t("research.note")}
          <textarea
            aria-label={t("research.note")}
            maxLength={100000}
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
        </label>
        <small>{t("research.humanNote")}</small>
        <button
          disabled={busy || note === item.user_note}
          onClick={() => void run(() => onUpdate(item.id, { user_note: note }))}
        >
          {t("research.saveNote")}
        </button>
      </div>
      {item.source_available && item.paper_id !== null ? (
        <div className="evidence-source-actions">
          <button onClick={() => onPaper(item.paper_id!)}>
            {t("research.viewPaper")}
          </button>
          <button onClick={() => onLibrary(item.paper_id!)}>
            {t("ask.viewLibrary")}
          </button>
          <button
            onClick={async () => {
              try {
                await paperAction(
                  item.paper_id!,
                  "open",
                  item.page_start ?? undefined,
                );
              } catch (error) {
                onError(errorMessage(error));
              }
            }}
          >
            {t("research.openPdf")}
          </button>
        </div>
      ) : (
        <p role="status">{t("research.sourceUnavailable")}</p>
      )}
      <button disabled={busy} onClick={() => void run(() => onRemove(item.id))}>
        {t("research.remove")}
      </button>
    </article>
  );
}

export default function ResearchEvidenceWorkspace({
  sessionId,
  onPaper,
  onLibrary,
  onError,
  onChanged,
  focusEvidenceId,
  onClaim,
}: {
  sessionId: number;
  onClaim?: (id: number) => void;
  focusEvidenceId?: number;
  onPaper: (id: number) => void;
  onLibrary: (id: number) => void;
  onError: (message: string) => void;
  onChanged: () => Promise<void>;
}) {
  const { t } = useTranslation();
  const [filter, setFilter] = useState<EvidenceDecision | "all">("all");
  const [data, setData] = useState<ResearchEvidenceList | null>(null);
  const load = useCallback(async () => {
    try {
      setData(
        await engine<ResearchEvidenceList>("research_evidence_list", {
          session_id: sessionId,
          decision: filter,
        }),
      );
    } catch (error) {
      onError(errorMessage(error));
    }
  }, [sessionId, filter, onError]);
  useEffect(() => {
    void load();
  }, [load]);
  useEffect(() => {
    if (focusEvidenceId && data) {
      const node = document.getElementById(
        `research-evidence-${focusEvidenceId}`,
      );
      node?.scrollIntoView({ block: "center", behavior: "smooth" });
      node?.focus({ preventScroll: true });
    }
  }, [focusEvidenceId, data]);
  async function mutate(operation: string, params: Record<string, unknown>) {
    try {
      await engine(operation, params);
      await load();
      await onChanged();
    } catch (error) {
      onError(errorMessage(error));
    }
  }
  return (
    <section
      className="research-evidence-workspace"
      aria-label={t("research.evidence")}
    >
      <h3>{t("research.evidence")}</h3>
      <p className="hint">{t("research.humanDecisions")}</p>
      <div
        className="research-evidence-filters"
        role="group"
        aria-label={t("research.filter")}
      >
        {(["all", ...decisions] as const).map((value) => (
          <button
            key={value}
            aria-pressed={filter === value}
            onClick={() => setFilter(value)}
          >
            {t(`research.${value}`)} ·{" "}
            {data?.counts[value === "all" ? "total" : value] ?? 0}
          </button>
        ))}
      </div>
      {data && <p>{t("research.total", { count: data.counts.total })}</p>}
      {data?.items.length === 0 && (
        <p>
          {t(
            data.counts.total
              ? "research.noMatchingEvidence"
              : "research.empty",
          )}
        </p>
      )}
      <div className="saved-evidence-list">
        {data?.items.map((item) => (
          <EvidenceItem
            key={item.id}
            item={item}
            onClaim={onClaim}
            onUpdate={(id, changes) =>
              mutate("research_evidence_update", { id, ...changes })
            }
            onRemove={(id) => mutate("research_evidence_remove", { id })}
            onPaper={onPaper}
            onLibrary={onLibrary}
            onError={onError}
          />
        ))}
      </div>
    </section>
  );
}
