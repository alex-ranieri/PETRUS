import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  engine,
  errorMessage,
  type TrailItem,
  type TrailActor,
  type TrailPage,
} from "../services/api";

function utc(value: string) {
  return /Z$|[+-]\d\d:\d\d$/.test(value)
    ? value
    : value.replace(" ", "T") + "Z";
}
function scalar(value: unknown) {
  return typeof value === "string" || typeof value === "number"
    ? String(value)
    : "";
}
type Identity = {
  evidence_id?: string;
  unit_id: string;
  paper_id: number;
  text_sha256?: string;
  evidence_fingerprint?: string;
  lexical_rank?: number;
  semantic_rank?: number;
  section_boost?: number;
};

function Detail({ item }: { item: TrailItem }) {
  const { t } = useTranslation();
  const data = item.metadata;
  const selected = Array.isArray(data.selected)
    ? (data.selected as Identity[])
    : [];
  const source =
    data.source_snapshot && typeof data.source_snapshot === "object"
      ? (data.source_snapshot as Record<string, unknown>)
      : null;
  return (
    <div className="trail-details">
      {[
        "statement_snapshot",
        "new_statement_snapshot",
        "researcher_note_snapshot",
      ].map((key) =>
        typeof data[key] === "string" ? (
          <section key={key}>
            <h4>
              {t(
                key === "researcher_note_snapshot"
                  ? "claims.note"
                  : "claims.statement",
              )}
            </h4>
            <pre className="claim-statement">{String(data[key])}</pre>
          </section>
        ) : null,
      )}
      {typeof data.question === "string" && (
        <blockquote className="trail-question">{data.question}</blockquote>
      )}
      {typeof data.question_snapshot === "string" && (
        <p>
          {t("ask.question")}: {data.question_snapshot}
        </p>
      )}
      {typeof data.answer === "string" && (
        <section aria-label={t("trail.answerSnapshot")}>
          <h4>{t("trail.answerSnapshot")}</h4>
          <div className="reading">{data.answer}</div>
        </section>
      )}
      {Array.isArray(data.citations) && (
        <p>
          {t("trail.citations")}:{" "}
          {data.citations.map(scalar).join(", ") || t("trail.none")}
        </p>
      )}
      {typeof data.new_note_snapshot === "string" && (
        <section
          className="research-human-note"
          aria-label={t("trail.noteVersion")}
        >
          <h4>{t("trail.noteVersion")}</h4>
          <pre>{data.new_note_snapshot}</pre>
        </section>
      )}
      {item.event_type === "evidence_note_updated" &&
        typeof data.new_note_snapshot !== "string" && (
          <p className="hint">{t("trail.legacyNote")}</p>
        )}
      {source && (
        <section>
          <h4>{t("trail.sourceSnapshot")}</h4>
          <p>
            {scalar(source.paper_title_snapshot)} ·{" "}
            {scalar(source.section_heading_snapshot)}
          </p>
          {typeof source.text_snapshot === "string" && (
            <blockquote>{source.text_snapshot}</blockquote>
          )}
        </section>
      )}
      {Array.isArray(data.validation_codes) &&
        data.validation_codes.length > 0 && (
          <p>
            {t("trail.validation")}:{" "}
            {data.validation_codes
              .map((code) =>
                t(`ask.warning.${scalar(code)}`, {
                  defaultValue: t("trail.technicalFailure"),
                }),
              )
              .join(" · ")}
          </p>
        )}
      {typeof data.generation_error_code === "string" && (
        <p>
          {t("trail.technicalFailure")}:{" "}
          <code>{data.generation_error_code}</code>
        </p>
      )}
      {selected.length > 0 && (
        <section>
          <h4>{t("trail.selectedIdentities")}</h4>
          <div className="trail-table-scroll">
            <table>
              <thead>
                <tr>
                  <th>{t("trail.localLabel")}</th>
                  <th>{t("trail.unit")}</th>
                  <th>{t("trail.ranks")}</th>
                  <th>{t("trail.hash")}</th>
                </tr>
              </thead>
              <tbody>
                {selected.map((identity, index) => (
                  <tr key={`${identity.unit_id}-${index}`}>
                    <td>{identity.evidence_id}</td>
                    <td>{identity.unit_id}</td>
                    <td>
                      {identity.lexical_rank ?? "—"} /{" "}
                      {identity.semantic_rank ?? "—"} ·{" "}
                      {identity.section_boost ?? "—"}
                    </td>
                    <td>
                      <code>
                        {identity.evidence_fingerprint ??
                          identity.text_sha256 ??
                          "—"}
                      </code>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <small>{t("trail.localLabelNotice")}</small>
        </section>
      )}
      <dl className="trail-metadata">
        {[
          "language",
          "returned_candidate_count",
          "selected_count",
          "final_status",
          "generation_attempts",
          "repair_attempted",
          "provider_id",
          "model_id",
          "question_sha256",
          "answer_sha256",
          "old_note_sha256",
          "new_note_sha256",
          "retrieval_context_sha256",
          "evidence_fingerprint",
        ].map((key) =>
          data[key] !== undefined && data[key] !== null ? (
            <div key={key}>
              <dt>{t(`trail.meta.${key}`)}</dt>
              <dd>
                {typeof data[key] === "boolean"
                  ? t(data[key] ? "trail.yes" : "trail.no")
                  : scalar(data[key])}
              </dd>
            </div>
          ) : null,
        )}
      </dl>
      {data.query_plan && typeof data.query_plan === "object" ? (
        <section>
          <h4>{t("trail.queryPlan")}</h4>
          <dl className="trail-metadata">
            {Object.entries(data.query_plan as Record<string, unknown>).map(
              ([key, value]) => (
                <div key={key}>
                  <dt>{t(`trail.plan.${key}`)}</dt>
                  <dd>
                    {Array.isArray(value)
                      ? value.map(scalar).join(" · ")
                      : scalar(value)}
                  </dd>
                </div>
              ),
            )}
          </dl>
        </section>
      ) : null}
      {data.configuration && typeof data.configuration === "object" ? (
        <section>
          <h4>{t("trail.configuration")}</h4>
          <pre className="trail-config">
            {JSON.stringify(data.configuration, null, 2)}
          </pre>
        </section>
      ) : null}
      <small>
        {t("trail.payloadVersion", { version: item.payload_version })} ·{" "}
        {t("trail.hash")}: <code>{item.payload_sha256}</code>
      </small>
    </div>
  );
}

function Entry({
  item,
  onEvidence,
  onLibrary,
  onError,
  onReference,
  onClaim,
}: {
  onClaim?: (id: number) => void;
  item: TrailItem;
  onEvidence: (id: number) => void;
  onLibrary: (id: number) => void;
  onError: (message: string) => void;
  onReference: (reference: { event_id: number; session_id: number }) => void;
}) {
  const { t, i18n } = useTranslation();
  const [detail, setDetail] = useState<TrailItem | null>(null);
  const [loading, setLoading] = useState(false);
  const oldDecision = scalar(
    item.metadata.old_decision ?? item.metadata.previous,
  );
  const newDecision = scalar(item.metadata.new_decision ?? item.metadata.new);
  return (
    <li
      className="research-trail-entry"
      id={`trail-event-${item.id}`}
      data-event-id={item.id}
      data-actor={item.actor_type}
    >
      <div className="trail-entry-heading">
        <time dateTime={utc(item.created_at)}>
          {new Intl.DateTimeFormat(i18n.resolvedLanguage, {
            dateStyle: "short",
            timeStyle: "medium",
          }).format(new Date(utc(item.created_at)))}
        </time>
        <span className={`trail-actor ${item.actor_type}`}>
          {t(`trail.actor.${item.actor_type}`)}
        </span>
      </div>
      <details
        onToggle={async (event) => {
          if (!event.currentTarget.open || detail || loading) return;
          setLoading(true);
          try {
            setDetail(
              await engine<TrailItem>("research_trail_get", {
                session_id: item.session_id,
                event_id: item.id,
              }),
            );
          } catch (error) {
            onError(errorMessage(error));
          } finally {
            setLoading(false);
          }
        }}
      >
        <summary>
          {t(`trail.event.${item.event_type}`, {
            defaultValue: t("trail.legacyActivity"),
          })}
        </summary>
        {loading && <p role="status">{t("trail.loading")}</p>}
        {detail && <Detail item={detail} />}
      </details>
      {typeof item.metadata.paper_title_snapshot === "string" && (
        <p>
          {item.metadata.paper_title_snapshot}
          {item.metadata.evidence_label_snapshot
            ? ` · ${scalar(item.metadata.evidence_label_snapshot)}`
            : ""}
        </p>
      )}
      {item.event_type === "retrieval_completed" && (
        <p>
          {t("trail.retrievalSummary", {
            count: item.metadata.selected_count,
            papers: Array.isArray(item.metadata.paper_ids)
              ? item.metadata.paper_ids.length
              : 0,
          })}
        </p>
      )}
      {item.event_type === "ask_accepted" &&
        typeof item.metadata.citation_count === "number" && (
          <p>
            {t("trail.acceptedSummary", {
              count: item.metadata.citation_count,
            })}
          </p>
        )}
      {oldDecision && newDecision && (
        <p className="trail-decision-change">
          {t(`research.${oldDecision}`)} → {t(`research.${newDecision}`)}
        </p>
      )}
      {typeof item.metadata.old_relation === "string" && (
        <p>
          {t(`claims.${item.metadata.old_relation}`)} →{" "}
          {t(`claims.${String(item.metadata.new_relation)}`)}
        </p>
      )}
      {typeof item.metadata.old_review_status === "string" && (
        <p>
          {t(`claims.${item.metadata.old_review_status}`)} →{" "}
          {t(`claims.${String(item.metadata.new_review_status)}`)}
        </p>
      )}
      {typeof item.metadata.relation === "string" &&
        item.event_type === "claim_evidence_linked" && (
          <p>{t(`claims.${item.metadata.relation}`)}</p>
        )}
      <div className="trail-links">
        {item.claim_id && onClaim && (
          <button onClick={() => onClaim(item.claim_id!)}>
            {t("claims.open")}
          </button>
        )}
        {item.evidence_available && item.object_id && (
          <button onClick={() => onEvidence(Number(item.object_id))}>
            {t("trail.viewEvidence")}
          </button>
        )}
        {item.object_type === "research_evidence" &&
          !item.evidence_available && (
            <small>{t("trail.evidenceRemoved")}</small>
          )}
        {item.paper_links.map((link) =>
          link.available ? (
            <button
              key={link.paper_id}
              onClick={() => onLibrary(link.paper_id)}
            >
              {t("ask.viewLibrary")} · {link.paper_id}
            </button>
          ) : (
            <small key={link.paper_id}>{t("research.sourceUnavailable")}</small>
          ),
        )}
        {item.event_links.map((link) => (
          <button
            key={`${link.field}-${link.event_id}`}
            onClick={() => onReference(link)}
          >
            {t(`trail.link.${link.field}`)}
          </button>
        ))}
      </div>
    </li>
  );
}

export default function ResearchTrail({
  sessionId,
  onEvidence,
  onLibrary,
  onError,
  onClaim,
}: {
  onClaim?: (id: number) => void;
  sessionId: number;
  onEvidence: (id: number) => void;
  onLibrary: (id: number) => void;
  onError: (message: string) => void;
}) {
  const { t } = useTranslation();
  const [actor, setActor] = useState<TrailActor | "all">("all");
  const [page, setPage] = useState<TrailPage | null>(null);
  const [loading, setLoading] = useState(false);
  const [related, setRelated] = useState<TrailItem | null>(null);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setPage(null);
    void engine<TrailPage>("research_trail_list", {
      session_id: sessionId,
      actor_type: actor,
    })
      .then((result) => {
        if (active) setPage(result);
      })
      .catch((error) => {
        if (active) onError(errorMessage(error));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [sessionId, actor, onError]);
  async function more() {
    if (!page?.next_after_event_id) return;
    setLoading(true);
    try {
      const next = await engine<TrailPage>("research_trail_list", {
        session_id: sessionId,
        actor_type: actor,
        after_event_id: page.next_after_event_id,
      });
      setPage({ ...next, items: [...page.items, ...next.items] });
    } catch (error) {
      onError(errorMessage(error));
    } finally {
      setLoading(false);
    }
  }
  return (
    <section className="research-trail" aria-label={t("trail.title")}>
      <h3>{t("trail.title")}</h3>
      <p className="hint">{t("trail.description")}</p>
      {page?.has_legacy_activity && (
        <p className="notice" role="status">
          {t("trail.legacyWarning")}
        </p>
      )}
      <div
        className="research-evidence-filters"
        role="group"
        aria-label={t("trail.filter")}
      >
        {(["all", "user", "ai", "system"] as const).map((value) => (
          <button
            key={value}
            disabled={loading}
            aria-pressed={actor === value}
            onClick={() => setActor(value)}
          >
            {t(value === "all" ? "research.all" : `trail.actor.${value}`)}
          </button>
        ))}
      </div>
      {loading && <p role="status">{t("trail.loading")}</p>}
      {page?.items.length === 0 && <p>{t("trail.empty")}</p>}
      <ol>
        {page?.items.map((item) => (
          <Entry
            key={item.id}
            item={item}
            onClaim={onClaim}
            onEvidence={onEvidence}
            onLibrary={onLibrary}
            onError={onError}
            onReference={async (reference) => {
              try {
                setRelated(
                  await engine<TrailItem>("research_trail_get", {
                    session_id: reference.session_id,
                    event_id: reference.event_id,
                  }),
                );
              } catch (error) {
                onError(errorMessage(error));
              }
            }}
          />
        ))}
      </ol>
      {page?.next_after_event_id && (
        <button disabled={loading} onClick={() => void more()}>
          {t("trail.more")}
        </button>
      )}
      {related && (
        <section className="trail-related" aria-label={t("trail.related")}>
          <h4>
            {t("trail.related")}: {t(`trail.event.${related.event_type}`)}
          </h4>
          <button onClick={() => setRelated(null)}>{t("trail.close")}</button>
          <Detail item={related} />
        </section>
      )}
    </section>
  );
}
