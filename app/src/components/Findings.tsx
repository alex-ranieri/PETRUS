import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  engine,
  errorMessage,
  paperAction,
  type ResearchClaim,
  type ClaimList,
  type ClaimLink,
  type ClaimRelation,
  type ResearchEvidenceList,
  type TrailItem,
} from "../services/api";

const relations: ClaimRelation[] = ["supports", "contradicts", "context"];
function localTime(value: string) {
  return new Date(value).toLocaleString();
}

function ClaimForm({
  initial,
  onSave,
  onCancel,
  busy,
}: {
  initial?: ResearchClaim;
  onSave: (statement: string, note: string) => Promise<void>;
  onCancel: () => void;
  busy: boolean;
}) {
  const { t } = useTranslation();
  const [statement, setStatement] = useState(initial?.statement ?? "");
  const [note, setNote] = useState(initial?.researcher_note ?? "");
  return (
    <form
      className="claim-form"
      onSubmit={(event) => {
        event.preventDefault();
        void onSave(statement, note);
      }}
    >
      <label>
        {t("claims.statement")}
        <textarea
          aria-label={t("claims.statement")}
          required
          maxLength={10000}
          value={statement}
          onChange={(e) => setStatement(e.target.value)}
        />
      </label>
      <label>
        {t("claims.note")}
        <textarea
          aria-label={t("claims.note")}
          maxLength={100000}
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />
      </label>
      <p className="hint">{t("claims.humanOnly")}</p>
      <button className="primary" disabled={busy || !statement.trim()}>
        {t("claims.save")}
      </button>
      <button type="button" disabled={busy} onClick={onCancel}>
        {t("claims.cancel")}
      </button>
    </form>
  );
}

function HistoricalSource({
  link,
  sessionId,
  onError,
}: {
  link: ClaimLink;
  sessionId: number;
  onError: (message: string) => void;
}) {
  const { t } = useTranslation();
  const [snapshot, setSnapshot] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  return link.source_snapshot_event_id ? (
    <details
      className="claim-source-snapshot"
      onToggle={async (event) => {
        if (!event.currentTarget.open || snapshot !== null || loading) return;
        setLoading(true);
        try {
          const result = await engine<TrailItem>("research_trail_get", {
            session_id: sessionId,
            event_id: link.source_snapshot_event_id,
          });
          const source = result.metadata.source_snapshot as
            { text_snapshot?: string } | undefined;
          setSnapshot(source?.text_snapshot ?? "");
        } catch (error) {
          onError(errorMessage(error));
        } finally {
          setLoading(false);
        }
      }}
    >
      <summary>{t("claims.historicalSource")}</summary>
      {loading && <p role="status">{t("trail.loading")}</p>}
      {snapshot !== null &&
        (snapshot ? (
          <blockquote>{snapshot}</blockquote>
        ) : (
          <p>{t("claims.noSnapshot")}</p>
        ))}
    </details>
  ) : (
    <p>{t("claims.noSnapshot")}</p>
  );
}

export default function Findings({
  sessionId,
  focusClaimId,
  onEvidence,
  onPaper,
  onLibrary,
  onError,
}: {
  sessionId: number;
  focusClaimId?: number;
  onEvidence: (id: number) => void;
  onPaper: (id: number) => void;
  onLibrary: (id: number) => void;
  onError: (message: string) => void;
}) {
  const { t } = useTranslation();
  const [filter, setFilter] = useState<
    "all" | "draft" | "reviewed" | "archived"
  >("all");
  const [list, setList] = useState<ClaimList | null>(null);
  const [selected, setSelected] = useState<number | null>(focusClaimId ?? null);
  const [claim, setClaim] = useState<ResearchClaim | null>(null);
  const [form, setForm] = useState<"new" | "edit" | null>(null);
  const [busy, setBusy] = useState(false);
  const [sources, setSources] = useState<ResearchEvidenceList | null>(null);
  const [sourceId, setSourceId] = useState("");
  const [relation, setRelation] = useState<ClaimRelation | "">("");
  const load = useCallback(async () => {
    try {
      setList(
        await engine<ClaimList>("research_claim_list", {
          session_id: sessionId,
          filter,
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
    if (focusClaimId) setSelected(focusClaimId);
  }, [focusClaimId]);
  useEffect(() => {
    let active = true;
    setClaim(null);
    setForm(null);
    setSources(null);
    if (selected)
      void engine<ResearchClaim>("research_claim_get", { id: selected })
        .then((value) => {
          if (active) setClaim(value);
        })
        .catch((error) => {
          if (active) onError(errorMessage(error));
        });
    return () => {
      active = false;
    };
  }, [selected, onError]);
  async function mutate(
    method: string,
    params: Record<string, unknown>,
    nextId = selected,
  ) {
    setBusy(true);
    try {
      const result = await engine<ResearchClaim>(method, params);
      await load();
      const id = method === "research_claim_create" ? result.id : nextId;
      if (id) {
        setClaim(await engine<ResearchClaim>("research_claim_get", { id }));
        setSelected(id);
      }
      setForm(null);
      setSources(null);
    } catch (error) {
      onError(errorMessage(error));
      throw error;
    } finally {
      setBusy(false);
    }
  }
  function run(method: string, params: Record<string, unknown>) {
    void mutate(method, params).catch(() => undefined);
  }
  return (
    <section className="findings-workspace" aria-label={t("claims.title")}>
      <div className="claim-heading">
        <h3>{t("claims.title")}</h3>
        <button
          disabled={busy}
          onClick={() => {
            setForm("new");
            setSources(null);
          }}
        >
          {t("claims.new")}
        </button>
      </div>
      <p className="hint">{t("claims.humanOnly")}</p>
      <p className="hint">{t("claims.reviewMeaning")}</p>
      <div
        role="group"
        aria-label={t("claims.filters")}
        className="research-evidence-filters"
      >
        {(["all", "draft", "reviewed", "archived"] as const).map((value) => (
          <button
            key={value}
            disabled={busy}
            aria-pressed={filter === value}
            onClick={() => setFilter(value)}
          >
            {t(`claims.${value}`)} · {list?.counts[value] ?? 0}
          </button>
        ))}
      </div>
      {form === "new" && (
        <ClaimForm
          busy={busy}
          onCancel={() => setForm(null)}
          onSave={async (statement, researcher_note) => {
            await mutate("research_claim_create", {
              session_id: sessionId,
              statement,
              researcher_note,
            }).catch(() => undefined);
          }}
        />
      )}
      {list?.items.length === 0 && <p>{t("claims.empty")}</p>}
      <div className="claim-list">
        {list?.items.map((item) => (
          <button
            className="claim-card"
            key={item.id}
            aria-pressed={selected === item.id}
            onClick={() => {
              setSelected(item.id);
              setForm(null);
            }}
          >
            <span>
              {t("claims.number", { id: item.id })} ·{" "}
              {t(`claims.${item.review_status}`)}
            </span>
            <p className="claim-statement">{item.statement}</p>
            <small>
              {t("claims.evidenceCount", { count: item.evidence_count })} ·{" "}
              {relations
                .map((kind) => `${t(`claims.${kind}`)}: ${item.counts[kind]}`)
                .join(" · ")}
            </small>
            <time dateTime={item.updated_at}>{localTime(item.updated_at)}</time>
          </button>
        ))}
      </div>
      {list?.next_after_id && (
        <button
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            try {
              const next = await engine<ClaimList>("research_claim_list", {
                session_id: sessionId,
                filter,
                after_id: list.next_after_id,
              });
              setList({ ...next, items: [...list.items, ...next.items] });
            } catch (error) {
              onError(errorMessage(error));
            } finally {
              setBusy(false);
            }
          }}
        >
          {t("trail.more")}
        </button>
      )}
      {claim && form !== "new" && (
        <article
          className="claim-detail"
          id={`research-claim-${claim.id}`}
          aria-label={t("claims.detail")}
        >
          <h3>
            {t("claims.number", { id: claim.id })} ·{" "}
            {t(`claims.${claim.review_status}`)}
          </h3>
          {claim.archived_at && (
            <p role="status">{t("claims.archivedReadOnly")}</p>
          )}
          {claim.review_warning && (
            <p role="status" className="notice">
              {t("claims.reviewWarning")}
            </p>
          )}
          {form === "edit" ? (
            <ClaimForm
              key={claim.id}
              initial={claim}
              busy={busy}
              onCancel={() => setForm(null)}
              onSave={async (statement, researcher_note) => {
                await mutate("research_claim_update", {
                  id: claim.id,
                  statement,
                  researcher_note,
                }).catch(() => undefined);
              }}
            />
          ) : (
            <>
              <div className="claim-statement">{claim.statement}</div>
              <section className="research-human-note">
                <h4>{t("claims.note")}</h4>
                <pre>{claim.researcher_note || t("claims.noNote")}</pre>
              </section>
              {!claim.archived_at ? (
                <div className="claim-actions">
                  <button disabled={busy} onClick={() => setForm("edit")}>
                    {t("claims.edit")}
                  </button>
                  <button
                    disabled={busy}
                    onClick={async () => {
                      try {
                        setSources(
                          await engine<ResearchEvidenceList>(
                            "research_evidence_list",
                            { session_id: sessionId },
                          ),
                        );
                        setSourceId("");
                        setRelation("");
                      } catch (error) {
                        onError(errorMessage(error));
                      }
                    }}
                  >
                    {t("claims.addEvidence")}
                  </button>
                  <button
                    disabled={
                      busy ||
                      (claim.review_status === "draft" &&
                        claim.evidence_count === 0)
                    }
                    onClick={() =>
                      run("research_claim_update", {
                        id: claim.id,
                        review_status:
                          claim.review_status === "draft"
                            ? "reviewed"
                            : "draft",
                      })
                    }
                  >
                    {t(
                      claim.review_status === "draft"
                        ? "claims.markReviewed"
                        : "claims.returnDraft",
                    )}
                  </button>
                  <button
                    disabled={busy}
                    onClick={() =>
                      run("research_claim_archive", { id: claim.id })
                    }
                  >
                    {t("claims.archive")}
                  </button>
                </div>
              ) : (
                <button
                  disabled={busy}
                  onClick={() =>
                    run("research_claim_restore", { id: claim.id })
                  }
                >
                  {t("claims.restore")}
                </button>
              )}
            </>
          )}
          <p className="hint">{t("claims.classificationMeaning")}</p>
          {sources && (
            <form
              className="claim-evidence-picker"
              aria-label={t("claims.addEvidence")}
              onSubmit={(event) => {
                event.preventDefault();
                run("research_claim_evidence_link", {
                  claim_id: claim.id,
                  saved_evidence_id: Number(sourceId),
                  relation,
                });
              }}
            >
              <fieldset>
                <legend>{t("claims.chooseEvidence")}</legend>
                {sources.items
                  .filter(
                    (item) =>
                      !claim.links.some(
                        (link) =>
                          link.evidence_fingerprint ===
                          item.evidence_fingerprint,
                      ),
                  )
                  .map((item) => (
                    <label className="claim-source-option" key={item.id}>
                      <input
                        type="radio"
                        name="claim-source"
                        value={item.id}
                        checked={sourceId === String(item.id)}
                        onChange={(event) => setSourceId(event.target.value)}
                      />
                      <strong>{item.paper_title_snapshot}</strong> ·{" "}
                      {item.section_heading_snapshot} ·{" "}
                      {item.page_start === null
                        ? t("ask.pageUnavailable")
                        : t("ask.pages", {
                            start: item.page_start,
                            end: item.page_end,
                          })}{" "}
                      · {t(`research.${item.decision}`)}
                      <blockquote>{item.text_snapshot}</blockquote>
                    </label>
                  ))}
              </fieldset>
              <label>
                {t("claims.relation")}
                <select
                  required
                  value={relation}
                  onChange={(event) =>
                    setRelation(event.target.value as ClaimRelation)
                  }
                >
                  <option value="">{t("claims.chooseRelation")}</option>
                  {relations.map((kind) => (
                    <option key={kind} value={kind}>
                      {t(`claims.${kind}`)}
                    </option>
                  ))}
                </select>
              </label>
              <button disabled={busy || !sourceId || !relation}>
                {t("claims.link")}
              </button>
              <button type="button" onClick={() => setSources(null)}>
                {t("claims.cancel")}
              </button>
            </form>
          )}
          <div className="claim-links">
            {claim.links.map((link) => (
              <article
                className="claim-link"
                key={link.id}
                data-link-id={link.id}
              >
                <h4>
                  {t(`claims.${link.relation}`)} · {link.paper_title_snapshot}
                </h4>
                <p>
                  {link.section_heading_snapshot} ·{" "}
                  {link.page_start === null
                    ? t("ask.pageUnavailable")
                    : t("ask.pages", {
                        start: link.page_start,
                        end: link.page_end,
                      })}{" "}
                  · {t(`ask.provenance.${link.provenance_level}`)}
                </p>
                <p>
                  {t("research.decision")}:{" "}
                  {t(
                    `research.${link.current_decision ?? link.decision_at_link}`,
                  )}
                  {link.source_removed
                    ? ` · ${t("claims.decisionAtLink")}`
                    : ""}
                </p>
                {!link.source_available && (
                  <p role="status">
                    {t(
                      link.source_removed
                        ? "claims.sourceRemoved"
                        : "research.sourceUnavailable",
                    )}
                  </p>
                )}
                <div className="claim-link-actions">
                  {!claim.archived_at && (
                    <>
                      <label>
                        {t("claims.relation")}
                        <select
                          disabled={busy}
                          value={link.relation}
                          onChange={(event) =>
                            run("research_claim_evidence_update", {
                              id: link.id,
                              relation: event.target.value,
                            })
                          }
                        >
                          {relations.map((kind) => (
                            <option key={kind} value={kind}>
                              {t(`claims.${kind}`)}
                            </option>
                          ))}
                        </select>
                      </label>
                      <button
                        disabled={busy}
                        onClick={() =>
                          run("research_claim_evidence_unlink", { id: link.id })
                        }
                      >
                        {t("claims.unlink")}
                      </button>
                    </>
                  )}
                  {link.saved_evidence_id && (
                    <button onClick={() => onEvidence(link.saved_evidence_id!)}>
                      {t("trail.viewEvidence")}
                    </button>
                  )}
                  {link.source_available && link.current_paper_id && (
                    <>
                      <button onClick={() => onPaper(link.current_paper_id!)}>
                        {t("research.viewPaper")}
                      </button>
                      <button onClick={() => onLibrary(link.current_paper_id!)}>
                        {t("ask.viewLibrary")}
                      </button>
                      <button
                        onClick={async () => {
                          try {
                            await paperAction(
                              link.current_paper_id!,
                              "open",
                              link.page_start ?? undefined,
                            );
                          } catch (error) {
                            onError(errorMessage(error));
                          }
                        }}
                      >
                        {t("research.openPdf")}
                      </button>
                    </>
                  )}
                </div>
                <HistoricalSource
                  link={link}
                  sessionId={sessionId}
                  onError={onError}
                />
                <small className="claim-identity">
                  {t("trail.meta.evidence_fingerprint")}:{" "}
                  {link.evidence_fingerprint}
                </small>
              </article>
            ))}
          </div>
        </article>
      )}
    </section>
  );
}
