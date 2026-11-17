import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  X,
  ExternalLink,
  FolderSearch,
  FileText,
  ArrowUpRight,
  Save,
  ChevronLeft,
  ChevronRight,
  RotateCw,
} from "lucide-react";
import {
  engine,
  paperAction,
  errorMessage,
  dateLabel,
  type PaperDetail,
  type Collection,
} from "../services/api";
import { label, localizeMessage, numberLabel } from "../i18n";
export default function PaperPanel({
  id,
  onClose,
  onPaper,
  collections,
  onChanged,
  onError,
  revision,
}: {
  id: number;
  onClose: () => void;
  onPaper: (id: number) => void;
  collections: Collection[];
  onChanged: () => void;
  onError: (message: string) => void;
  revision: string;
}) {
  const { t } = useTranslation();
  const [paper, setPaper] = useState<PaperDetail | null>(null);
  const [tab, setTab] = useState("Overview");
  const [mode, setMode] = useState<"structured" | "pages">("structured");
  const [refFilter, setRefFilter] = useState("all");
  const [notes, setNotes] = useState("");
  const [saved, setSaved] = useState(false);
  const [pageNotice, setPageNotice] = useState<number | null>(null);
  const [page, setPage] = useState(1);
  const [content, setContent] = useState<{
    page: { page: number; text: string } | null;
    extracted_pages: number;
  } | null>(null);
  const [failed, setFailed] = useState(false);
  const [savingMembership, setSavingMembership] = useState(false);
  const loaded = useRef(false);
  useEffect(() => {
    let active = true;
    engine<PaperDetail>("paper", { id })
      .then((data) => {
        if (active) {
          setPaper(data);
          if (!loaded.current) {
            setNotes(data.notes);
            loaded.current = true;
          }
        }
      })
      .catch((e) => {
        if (active) setFailed(true);
        onError(errorMessage(e));
      });
    return () => {
      active = false;
    };
  }, [id, revision, onError]);
  useEffect(() => {
    if (tab !== "Content" || mode !== "pages") return;
    let active = true;
    setContent(null);
    engine<{
      page: { page: number; text: string } | null;
      extracted_pages: number;
    }>("content", { id, page })
      .then((data) => {
        if (active) setContent(data);
      })
      .catch((e) => onError(errorMessage(e)));
    return () => {
      active = false;
    };
  }, [id, page, tab, mode, onError]);
  useEffect(() => {
    const close = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [onClose]);
  async function action(kind: "open" | "reveal", atPage?: number) {
    try {
      const outcome = await paperAction(id, kind, atPage);
      if (atPage && !outcome?.page_open_supported) setPageNotice(atPage);
    } catch (e) {
      onError(errorMessage(e));
    }
  }
  async function membership(collectionId: number, selected: boolean) {
    const prior = paper?.memberships || [];
    setSavingMembership(true);
    setPaper((p) =>
      p
        ? {
            ...p,
            memberships: selected
              ? [...p.memberships, collectionId]
              : p.memberships.filter((i) => i !== collectionId),
          }
        : p,
    );
    try {
      await engine("set_collection", {
        paper_id: id,
        collection_id: collectionId,
        selected,
      });
      setPaper(await engine<PaperDetail>("paper", { id }));
      onChanged();
    } catch (e) {
      setPaper((p) => (p ? { ...p, memberships: prior } : p));
      onError(errorMessage(e));
    } finally {
      setSavingMembership(false);
    }
  }
  const c = (key: string) => t("copy." + key);
  const references =
    paper?.references.filter(
      (r) =>
        refFilter === "all" ||
        (refFilter === "in"
          ? r.resolution_status === "resolved"
          : r.resolution_status !== "resolved"),
    ) || [];
  return (
    <aside className="paper-panel" aria-label={c("paper_details_f7f3d")}>
      <div className="panel-top">
        <span>
          <FileText size={15} />
          {c("paper_details_5aea2")}
        </span>
        <button aria-label={c("close_paper_details_ccb0f")} onClick={onClose}>
          <X size={19} />
        </button>
      </div>
      {!paper ? (
        <div className="empty-state">
          <p>
            {c(
              failed
                ? "could_not_load_this_paper_close_this_f527f"
                : "loading_paper_80a6e",
            )}
          </p>
        </div>
      ) : (
        <>
          <div className="paper-heading">
            <div className="parsing-status">
              <span className={`status ${paper.status}`}>
                {label(paper.status)}
              </span>
              <span
                className={`status ${paper.scientific_status}`}
                title={t("scientific.status")}
              >
                {label(paper.scientific_status)}
              </span>
            </div>
            <h2>{paper.title}</h2>
            <p>{paper.authors || c("author_metadata_unavailable_09ea3")}</p>
            <div className="paper-citation">
              {paper.journal || c("journal_unknown_a7169")}
              <span>·</span>
              {paper.publication_year || c("year_unknown_69334")}
            </div>
            <div className="button-row">
              <button
                className="primary"
                disabled={!paper.files.some((f) => f.available)}
                onClick={() => void action("open")}
              >
                <ExternalLink size={15} />
                {c("open_pdf_40fdb")}
              </button>
              <button
                className="secondary"
                onClick={() => void action("reveal")}
              >
                <FolderSearch size={15} />
                {c("reveal_file_f7b39")}
              </button>
            </div>
            <button
              className="text-button reprocess-paper"
              onClick={() => {
                void engine("reprocess_scientific", { paper_id: id })
                  .then(onChanged)
                  .catch((e) => onError(errorMessage(e)));
              }}
            >
              <RotateCw size={13} />
              {t("scientific.reprocess")}
            </button>
          </div>
          <div className="tabs" role="tablist">
            {["Overview", "Content", "References", "Connections", "Notes"].map(
              (value) => (
                <button
                  key={value}
                  role="tab"
                  aria-selected={tab === value}
                  className={tab === value ? "active" : ""}
                  onClick={() => setTab(value)}
                >
                  {label(value)}
                </button>
              ),
            )}
          </div>
          <div className="panel-body">
            {tab === "Overview" && (
              <>
                {paper.warning && (
                  <div className="notice warning">{t("warnings.basic")}</div>
                )}
                {paper.scientific_warning && (
                  <div className="notice warning">
                    {localizeMessage(paper.scientific_warning)}
                  </div>
                )}
                <section>
                  <h4>{c("abstract_e29c6")}</h4>
                  <p className="reading">
                    {paper.abstract ||
                      c("no_abstract_was_reliably_identified_by_the_30077")}
                  </p>
                </section>
                <section>
                  <h4>{c("metadata_9075e")}</h4>
                  <dl>
                    <dt>{c("doi_5d31a")}</dt>
                    <dd className="mono">
                      {paper.doi || c("not_identified_8dd12")}
                    </dd>
                    <dt>{c("pages_60058")}</dt>
                    <dd>{paper.page_count ?? "—"}</dd>
                    <dt>{c("indexed_ec8be")}</dt>
                    <dd>{label(paper.index_status)}</dd>
                    <dt>{t("scientific.status")}</dt>
                    <dd>{label(paper.scientific_status)}</dd>
                    <dt>{c("added_b6873")}</dt>
                    <dd>{dateLabel(paper.created_at)}</dd>
                  </dl>
                </section>
                <section>
                  <h4>{c("collections_d938f")}</h4>
                  {collections.length ? (
                    <div className="collection-choices">
                      {collections.map((col) => (
                        <label key={col.id}>
                          <input
                            type="checkbox"
                            disabled={savingMembership}
                            checked={paper.memberships.includes(col.id)}
                            onChange={(e) =>
                              void membership(col.id, e.target.checked)
                            }
                          />
                          {col.name}
                        </label>
                      ))}
                    </div>
                  ) : (
                    <p className="hint">
                      {c("create_a_collection_using_the_in_the_80cb3")}
                    </p>
                  )}
                </section>
                <section>
                  <h4>{c("file_locations_c4da5")}</h4>
                  {paper.files.map((f) => (
                    <div className="file-info" key={f.id}>
                      <FileText size={16} />
                      <div>
                        <p>{f.file_path}</p>
                        <small>
                          {f.available
                            ? t("files.original", {
                                size: numberLabel(
                                  Number(
                                    (f.file_size / 1024 / 1024).toFixed(2),
                                  ),
                                ),
                              })
                            : localizeMessage(f.error) ||
                              c("unavailable_2c9c1")}
                        </small>
                      </div>
                    </div>
                  ))}
                  <h4>{c("sha_256_45792")}</h4>
                  <p className="hash mono">{paper.file_hash}</p>
                </section>
              </>
            )}
            {tab === "Content" && (
              <>
                {pageNotice !== null && (
                  <div className="notice">
                    <span>
                      {t("content.pageOpenNote", { page: pageNotice })}
                    </span>
                    <button
                      aria-label={t("copy.dismiss_notification_dc83c")}
                      onClick={() => setPageNotice(null)}
                    >
                      <X size={14} />
                    </button>
                  </div>
                )}
                <div className="segmented">
                  <button
                    className={mode === "structured" ? "active" : ""}
                    onClick={() => setMode("structured")}
                  >
                    {t("content.structured")}
                  </button>
                  <button
                    className={mode === "pages" ? "active" : ""}
                    onClick={() => setMode("pages")}
                  >
                    {t("content.pages")}
                  </button>
                </div>
                {mode === "structured" ? (
                  paper.sections.length ? (
                    paper.sections.map((section) => {
                      let depth = 0,
                        parent = section.parent_section_id;
                      while (parent && depth < 20) {
                        depth++;
                        parent =
                          paper.sections.find((s) => s.id === parent)
                            ?.parent_section_id ?? null;
                      }
                      const spans = paper.source_spans.filter(
                        (s) => s.section_id === section.id,
                      );
                      return (
                        <section
                          className="scientific-section"
                          key={section.id}
                          style={{ marginLeft: depth * 12 }}
                        >
                          <span className="small-label">
                            {label(section.section_type)}
                          </span>
                          <h3>
                            {section.heading || label(section.section_type)}
                          </h3>
                          <div className="section-pages">
                            {section.page_start !== null ? (
                              <button
                                className="text-button"
                                onClick={() =>
                                  void action("open", section.page_start!)
                                }
                                title={t("content.openAtPage", {
                                  page: section.page_start,
                                })}
                              >
                                {t("content.pageRange", {
                                  start: section.page_start,
                                  end: section.page_end,
                                })}
                                <ArrowUpRight size={13} />
                              </button>
                            ) : (
                              <span className="hint">
                                {t("content.unmapped")}
                              </span>
                            )}
                          </div>
                          <p className="reading">{section.text}</p>
                          {!!spans.length && (
                            <details className="provenance">
                              <summary>
                                {t("scientific.provenance")} · {spans.length}
                              </summary>
                              {spans.map((span) => (
                                <blockquote key={span.id}>
                                  <small>
                                    {c("page_fb062")} {span.page}
                                  </small>
                                  <p>{span.text}</p>
                                </blockquote>
                              ))}
                            </details>
                          )}
                        </section>
                      );
                    })
                  ) : (
                    <div className="feature-note">
                      <FileText size={28} />
                      <p>{t("content.noStructure")}</p>
                    </div>
                  )
                ) : (
                  <>
                    <div className="content-pagination">
                      <button
                        disabled={page <= 1}
                        aria-label={c("previous_page_81f54")}
                        onClick={() => setPage((p) => p - 1)}
                      >
                        <ChevronLeft size={17} />
                      </button>
                      <span>
                        {c("page_fb062")} {page} /{" "}
                        {content?.extracted_pages || "…"}
                      </span>
                      <button
                        disabled={!content || page >= content.extracted_pages}
                        aria-label={c("next_page_4bfc1")}
                        onClick={() => setPage((p) => p + 1)}
                      >
                        <ChevronRight size={17} />
                      </button>
                    </div>
                    <p className="hint">
                      {c(
                        "basic_text_extraction_original_page_numbers_preserved_61a77",
                      )}
                    </p>
                    <pre className="extracted-text">
                      {content
                        ? content.page?.text ||
                          c("no_extractable_text_on_this_page_open_8d1e1")
                        : c("loading_page_05322")}
                    </pre>
                  </>
                )}
              </>
            )}
            {tab === "References" && (
              <>
                <div className="segmented reference-filters">
                  {["all", "in", "missing"].map((filter) => (
                    <button
                      key={filter}
                      aria-pressed={refFilter === filter}
                      className={refFilter === filter ? "active" : ""}
                      onClick={() => setRefFilter(filter)}
                    >
                      {t(
                        filter === "in"
                          ? "references.inLibrary"
                          : "references." + filter,
                      )}
                    </button>
                  ))}
                </div>
                {references.length ? (
                  references.map((ref) => (
                    <article className="reference-item" key={ref.id}>
                      <div className="reference-title">
                        <span>[{ref.citation_order}]</span>
                        <h3>{ref.title || t("references.untitled")}</h3>
                      </div>
                      <p>{ref.authors_text}</p>
                      <small>
                        {[ref.journal, ref.year].filter(Boolean).join(" · ")}
                      </small>
                      {ref.doi && <p className="mono">{ref.doi}</p>}
                      <span
                        className={`status ${ref.resolution_status === "resolved" ? "ready" : "warning"}`}
                      >
                        {t(
                          ref.resolution_status === "resolved"
                            ? "references.inLibrary"
                            : ref.resolution_status === "candidate"
                              ? "references.candidate"
                              : "references.notInLibrary",
                        )}
                      </span>
                      {ref.resolution_status === "resolved" &&
                        ref.target_paper_id !== null && (
                          <button
                            className="text-button"
                            onClick={() => onPaper(ref.target_paper_id!)}
                          >
                            {t("references.openPaper")}
                            <ArrowUpRight size={14} />
                          </button>
                        )}
                      <details>
                        <summary>{t("graph.rawCitation")}</summary>
                        <p className="reading">{ref.raw_citation}</p>
                      </details>
                    </article>
                  ))
                ) : (
                  <p className="reading">{t("references.empty")}</p>
                )}
              </>
            )}
            {tab === "Connections" && (
              <>
                <h4>{c("connected_papers_2ac61")}</h4>
                <p className="hint">
                  {c("based_on_exact_author_metadata_or_shared_1a49c")}
                </p>
                {paper.connections.length ? (
                  paper.connections.map((p) => (
                    <button
                      className="connection-item"
                      key={p.id}
                      onClick={() => onPaper(p.id)}
                    >
                      <FileText size={17} />
                      <span>{p.title}</span>
                      <ArrowUpRight size={15} />
                    </button>
                  ))
                ) : (
                  <p className="reading">
                    {c("no_connections_yet_add_papers_to_a_6941e")}
                  </p>
                )}
              </>
            )}
            {tab === "Notes" && (
              <>
                <h4>{c("your_notes_6e963")}</h4>
                <textarea
                  className="notes-editor"
                  aria-label={c("paper_notes_21f93")}
                  placeholder={c(
                    "capture_a_question_observation_or_idea_5bb53",
                  )}
                  value={notes}
                  onChange={(e) => {
                    setNotes(e.target.value);
                    setSaved(false);
                  }}
                />
                <button
                  className="primary"
                  onClick={() => {
                    void engine("save_notes", { id, notes })
                      .then(() => setSaved(true))
                      .catch((e) => onError(errorMessage(e)));
                  }}
                >
                  <Save size={15} />
                  {c(saved ? "saved_locally_f7fe2" : "save_notes_ea7d8")}
                </button>
              </>
            )}
          </div>
        </>
      )}
    </aside>
  );
}
