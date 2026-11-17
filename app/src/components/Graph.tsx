import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import cytoscape from "cytoscape";
import { Maximize, Minus, Plus, Network, X, ArrowUpRight } from "lucide-react";
import {
  engine,
  errorMessage,
  type GraphData,
  type Relationship,
} from "../services/api";
import { numberLabel } from "../i18n";
const relationships: Relationship[] = [
  "CITES",
  "SHARED_AUTHOR",
  "SAME_COLLECTION",
  "TITLE_SIMILARITY",
  "SHARED_KEYWORDS",
  "SHARED_REFERENCES",
  "SEMANTIC_SIMILARITY",
];
export default function Graph({
  onPaper,
  revision,
  theme,
  onError,
}: {
  onPaper: (id: number) => void;
  revision: string;
  theme: string;
  onError: (message: string) => void;
}) {
  const { t, i18n } = useTranslation();
  const container = useRef<HTMLDivElement>(null);
  const cy = useRef<cytoscape.Core | null>(null);
  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState<Record<Relationship, boolean> | null>(
    null,
  );
  const [selected, setSelected] = useState<GraphData["edges"][number] | null>(
    null,
  );
  useEffect(() => {
    let active = true;
    engine<GraphData>("graph")
      .then((value) => {
        if (active) {
          setData(value);
          setFilters(
            (prior) =>
              prior || {
                CITES: true,
                SHARED_AUTHOR: false,
                SAME_COLLECTION: false,
                TITLE_SIMILARITY: false,
                SHARED_KEYWORDS: false,
                SHARED_REFERENCES: false,
                SEMANTIC_SIMILARITY: false,
              },
          );
        }
      })
      .catch((e) => onError(errorMessage(e)))
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [revision, onError]);
  useEffect(() => {
    if (!container.current || !data?.nodes.length || !filters) return;
    const colors = getComputedStyle(container.current);
    const color = (name: string) => colors.getPropertyValue(name).trim();
    const graph = cytoscape({
      container: container.current,
      minZoom: 0.12,
      maxZoom: 2.3,
      elements: [
        ...data.nodes.map((n) => ({
          data: {
            ...n,
            shortLabel:
              n.label.length > 45 ? n.label.slice(0, 42) + "…" : n.label,
          },
        })),
        ...data.edges.filter((e) => filters[e.type]).map((e) => ({ data: e })),
      ],
      style: [
        {
          selector: "node",
          style: {
            "background-color": color("--teal"),
            "border-width": 5,
            "border-color": color("--surface"),
            width: 21,
            height: 21,
            label: "data(shortLabel)",
            color: color("--muted"),
            "font-family": "system-ui",
            "font-size": 10,
            "text-valign": "bottom",
            "text-margin-y": 12,
            "text-wrap": "wrap",
            "text-max-width": "170px",
          },
        },
        {
          selector: "node:selected",
          style: {
            "background-color": color("--gold"),
            "border-color": color("--gold-soft"),
            width: 29,
            height: 29,
          },
        },
        {
          selector: "edge",
          style: {
            width: 0.8,
            "line-color": color("--graph-edge"),
            "curve-style": "bezier",
            opacity: 0.7,
          },
        },
        {
          selector: 'edge[type="CITES"]',
          style: {
            width: 1.6,
            "line-color": color("--gold"),
            "target-arrow-color": color("--gold"),
            "target-arrow-shape": "triangle",
            "arrow-scale": 0.9,
          },
        },
        {
          selector: 'edge[type="SAME_COLLECTION"]',
          style: { "line-style": "dotted" },
        },
        {
          selector:
            'edge[type="TITLE_SIMILARITY"], edge[type="SHARED_KEYWORDS"], edge[type="SHARED_REFERENCES"]',
          style: {
            "line-style": "dashed",
            "line-color": color("--teal"),
            "target-arrow-shape": "none",
          },
        },
        { selector: "edge:selected", style: { width: 3, opacity: 1 } },
      ],
      layout: {
        name: "cose",
        animate: false,
        nodeRepulsion: () => 14000,
        idealEdgeLength: () => 120,
        padding: 80,
        randomize: false,
      },
    });
    graph.on("tap", "node", (event) => onPaper(Number(event.target.id())));
    graph.on("tap", "edge", (event) => {
      const edge = data.edges.find((e) => e.id === event.target.id());
      if (edge && (edge.type === "CITES" || edge.metadata)) setSelected(edge);
    });
    cy.current = graph;
    const observer = new ResizeObserver(() => graph.resize());
    observer.observe(container.current);
    return () => {
      observer.disconnect();
      graph.destroy();
      cy.current = null;
    };
  }, [data, filters, theme, onPaper]);
  const edges = data?.edges.filter((e) => filters?.[e.type]) || [];
  return (
    <>
      <div className="graph-filters">
        <strong>{t("graph.relationships")}</strong>
        {relationships.map((type) => (
          <label key={type}>
            <input
              type="checkbox"
              checked={filters?.[type] ?? type === "CITES"}
              onChange={(e) =>
                setFilters((p) => ({ ...p!, [type]: e.target.checked }))
              }
            />
            <span className={`relation-key ${type}`} aria-hidden="true" />
            {t("graph." + type)}
          </label>
        ))}
      </div>
      <div className="graph-shell">
        <div className="graph-legend">
          <span className="dot teal" />
          {t("copy.paper_22d50")}
          <span className="line-key" />
          {t("graph.CITES")}
        </div>
        <div
          className="graph-canvas"
          ref={container}
          aria-label={t("copy.interactive_paper_connections_graph_d881a")}
        />
        {(!data?.nodes.length || loading) && (
          <div className="graph-empty">
            <Network size={44} strokeWidth={1} />
            <h3>
              {t(
                loading
                  ? "copy.mapping_your_library_a7591"
                  : "copy.connections_start_with_your_papers_40142",
              )}
            </h3>
            <p>
              {t("copy.add_a_library_then_assign_papers_to_fdb4e")}
              <br />
              {t(
                "copy.shared_authors_and_collections_create_connections_09847",
              )}
            </p>
          </div>
        )}
        <div className="graph-controls">
          <button
            title={t("copy.zoom_in_4fc05")}
            onClick={() => cy.current?.zoom(cy.current.zoom() * 1.2)}
          >
            <Plus size={17} />
          </button>
          <button
            title={t("copy.zoom_out_a4ae4")}
            onClick={() => cy.current?.zoom(cy.current.zoom() / 1.2)}
          >
            <Minus size={17} />
          </button>
          <button
            title={t("copy.fit_graph_b8398")}
            onClick={() => cy.current?.fit(undefined, 65)}
          >
            <Maximize size={17} />
          </button>
        </div>
        <div className="graph-caption">
          <span>
            {t("graph.paperCount", { count: data?.nodes.length || 0 }) +
              " · " +
              t("graph.edgeCount", { count: edges.length })}
            {data && data.nodes.length >= data.limit
              ? " · " + t("graph.limit", { limit: numberLabel(data.limit) })
              : ""}
          </span>
          <span>{t("copy.scroll_to_zoom_drag_to_explore_click_69255")}</span>
        </div>
        {selected?.reference && filters?.[selected.type] && (
          <aside
            className="citation-inspector"
            aria-label={t("graph.citationMetadata")}
          >
            <button
              className="modal-close"
              aria-label={t("copy.close_dialog_7b290")}
              onClick={() => setSelected(null)}
            >
              <X size={17} />
            </button>
            <h3>{t("graph.citationMetadata")}</h3>
            <h4>{t("graph.source")}</h4>
            <p>{selected.reference.source_title}</p>
            <h4>{t("graph.target")}</h4>
            <p>{selected.reference.target_title}</p>
            {selected.reference.authors_text && (
              <p>{selected.reference.authors_text}</p>
            )}
            <p>
              {[selected.reference.journal, selected.reference.year]
                .filter(Boolean)
                .join(" · ")}
            </p>
            {selected.reference.doi && (
              <p className="mono">{selected.reference.doi}</p>
            )}
            <h4>{t("graph.referenceNumber")}</h4>
            <p>[{selected.reference.citation_order}]</p>
            <h4>{t("graph.rawCitation")}</h4>
            <p>{selected.reference.raw_citation}</p>
            <button
              className="primary"
              onClick={() => onPaper(Number(selected.source))}
            >
              {t("graph.openSource")}
              <ArrowUpRight size={15} />
            </button>
          </aside>
        )}
        {selected?.metadata && filters?.[selected.type] && (
          <aside
            className="citation-inspector"
            aria-label={t("graph.relatednessDetails")}
          >
            <button
              className="modal-close"
              aria-label={t("copy.close_dialog_7b290")}
              onClick={() => setSelected(null)}
            >
              <X size={17} />
            </button>
            <h3>{t("graph." + selected.type)}</h3>
            <p>{data?.nodes.find((n) => n.id === selected.source)?.label}</p>
            <p>{data?.nodes.find((n) => n.id === selected.target)?.label}</p>
            <p>
              {t("graph.similarity", {
                value: new Intl.NumberFormat(i18n.resolvedLanguage, {
                  style: "percent",
                  maximumFractionDigits: 0,
                }).format(selected.score || 0),
              })}
            </p>
            {selected.type === "SEMANTIC_SIMILARITY" && (
              <p>{t("graph.semanticExplanation")}</p>
            )}
            {selected.metadata.shared_terms && (
              <>
                <h4>
                  {t("graph.sharedTerms", { count: selected.metadata.count })}
                </h4>
                <p>{selected.metadata.shared_terms.join(" · ")}</p>
                <p className="hint">{t("graph.derivedTerms")}</p>
              </>
            )}
            {selected.metadata.shared_reference_count !== undefined && (
              <>
                <h4>
                  {t("graph.sharedReferencesCount", {
                    count: selected.metadata.shared_reference_count,
                  })}
                </h4>
                <ul>
                  {selected.metadata.examples?.map((example, index) => (
                    <li key={index}>{example.title || example.doi}</li>
                  ))}
                </ul>
              </>
            )}
            <p className="hint">{t("graph.relatednessDisclaimer")}</p>
            <button
              className="primary"
              onClick={() => onPaper(Number(selected.source))}
            >
              {t("graph.openSource")}
              <ArrowUpRight size={15} />
            </button>
          </aside>
        )}
      </div>
      <p className="hint">{t("graph.relatednessDisclaimer")}</p>
      <details className="graph-accessible">
        <summary>{t("graph.relatednessDetails")}</summary>
        {edges
          .filter((e) => e.metadata)
          .map((edge) => (
            <button key={edge.id} onClick={() => setSelected(edge)}>
              {t("graph." + edge.type)}:{" "}
              {data?.nodes.find((n) => n.id === edge.source)?.label} ↔{" "}
              {data?.nodes.find((n) => n.id === edge.target)?.label}
            </button>
          ))}
      </details>
      <details className="graph-accessible">
        <summary>{t("graph.citationsList")}</summary>
        {edges
          .filter((e) => e.type === "CITES")
          .map((edge) => (
            <button key={edge.id} onClick={() => setSelected(edge)}>
              {edge.reference?.source_title} → {edge.reference?.target_title}
            </button>
          ))}
      </details>
      <details className="graph-accessible">
        <summary>{t("graph.browse")}</summary>
        {data?.nodes.map((n) => (
          <button key={n.id} onClick={() => onPaper(Number(n.id))}>
            {n.label}
          </button>
        ))}
      </details>
      <span className="sr-only" lang={i18n.resolvedLanguage} />
    </>
  );
}
