import { invoke, isTauri } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
import i18n, { localizeMessage } from "../i18n";

export { isTauri };
export function engine<T>(
  method: string,
  params: Record<string, unknown> = {},
): Promise<T> {
  if (!isTauri())
    return Promise.reject(new Error(i18n.t("errors.desktopRequired")));
  return invoke<T>("engine_call", { method, params });
}
export async function pickLibrary(): Promise<string | null> {
  if (!isTauri()) throw new Error(i18n.t("errors.desktopRequired"));
  return await open({
    directory: true,
    multiple: false,
    title: i18n.t("copy.choose_your_research_library_1551a"),
  });
}
export function paperAction(
  id: number,
  action: "open" | "reveal",
  page?: number,
) {
  return invoke<{
    page_requested?: number | null;
    page_open_supported?: boolean;
    revealed?: boolean;
  }>("paper_action", { id, action, page: page ?? null });
}
export type Paper = {
  id: number;
  title: string;
  authors: string | null;
  journal: string | null;
  publication_year: number | null;
  doi: string | null;
  abstract: string | null;
  status: string;
  metadata_status: string;
  index_status: string;
  file_name: string;
  file_hash: string;
  page_count: number | null;
  warning: string | null;
  collections: string | null;
  notes: string;
  created_at: string;
  scientific_status: string;
  scientific_warning: string | null;
};
export type PaperFile = {
  id: number;
  file_path: string;
  file_size: number;
  available: number;
  error: string | null;
  file_modified_at: number;
};
export type PaperDetail = Paper & {
  files: PaperFile[];
  memberships: number[];
  references: Reference[];
  sections: ScientificSection[];
  source_spans: SourceSpan[];
  connections: { id: number; title: string }[];
};
export type Collection = { id: number; name: string; paper_count: number };
export type Library = {
  id: number;
  name: string;
  root_path: string;
  file_count: number;
  last_scan_at: string | null;
};
export type Job = {
  id: number;
  library_id: number;
  library_name: string;
  status: string;
  stage: string;
  total: number;
  completed: number;
  errors: number;
  message: string | null;
  message_key: string | null;
  message_params: string | null;
  created_at: string;
};
export type Session = {
  id: number;
  title: string;
  research_question: string;
  description: string;
  created_at: string;
};
export type ModelCapabilityInfo = {
  configurable: boolean | null;
  can_disable: boolean | null;
};
export type LocalModelInfo = {
  id: string;
  display_name: string | null;
  type: string | null;
  category: "llm" | "embedding" | "unknown";
  architecture: string | null;
  format: string | null;
  parameters: string | null;
  quantization: string | null;
  size_bytes: number | null;
  loaded: boolean | null;
  reasoning: ModelCapabilityInfo;
};
export type ModelCatalogResponse = { models: LocalModelInfo[] };
export type Settings = {
  theme: "system" | "light" | "dark";
  auto_scan: boolean;
  watch_folders: boolean;
  embedding_provider: "none" | "lmstudio";
  embedding_endpoint: string;
  embedding_model: string;
  embedding_max_chars: number;
  llm_provider: "none" | "lmstudio" | "openai_compatible";
  llm_endpoint: string;
  llm_model: string;
  llm_temperature: number;
  llm_max_output_tokens?: number;
  llm_timeout_seconds?: number;
  llm_query_expansion: boolean;
  ai_provider: string;
  ai_endpoint: string;
  ai_model: string;
  language: "system" | "en" | "pt-BR";
  scientific_parser: "simple" | "grobid";
  grobid_endpoint: string;
  grobid_fallback: boolean;
};
export type Snapshot = {
  libraries: Library[];
  stats: {
    papers: number;
    indexed: number;
    attention: number;
    collections: number;
  };
  collections: Collection[];
  jobs: Job[];
  sessions: Session[];
  issues_total: number;
  issues: {
    id: number;
    paper_id: number | null;
    file_name: string;
    error: string;
    library_name: string;
  }[];
  settings: Settings;
  data_dir: string;
  database_path: string;
  system_locale?: string;
  grobid: { state: string; endpoint: string };
  facets: { years: number[]; journals: string[]; authors: string[] };
};
export const emptySnapshot: Snapshot = {
  libraries: [],
  stats: { papers: 0, indexed: 0, attention: 0, collections: 0 },
  collections: [],
  jobs: [],
  sessions: [],
  issues: [],
  issues_total: 0,
  settings: {
    theme: "system",
    auto_scan: false,
    watch_folders: false,
    embedding_provider: "none",
    embedding_endpoint: "",
    embedding_model: "",
    embedding_max_chars: 6000,
    llm_provider: "none",
    llm_endpoint: "",
    llm_model: "",
    llm_temperature: 0.1,
    llm_max_output_tokens: 1600,
    llm_timeout_seconds: 90,
    llm_query_expansion: false,
    ai_provider: "None",
    ai_endpoint: "",
    ai_model: "",
    language: "system",
    scientific_parser: "simple",
    grobid_endpoint: "http://127.0.0.1:8070",
    grobid_fallback: true,
  },
  data_dir: "",
  database_path: "",
  grobid: { state: "unavailable", endpoint: "http://127.0.0.1:8070" },
  facets: { years: [], journals: [], authors: [] },
};
export type GraphData = {
  nodes: { id: string; label: string }[];
  edges: {
    id: string;
    source: string;
    target: string;
    relation: string;
    type: Relationship;
    score?: number;
    metadata?: {
      score: number;
      shared_terms?: string[];
      count?: number;
      term_source?: "derived_term" | "source_keyword";
      shared_reference_count?: number;
      examples?: { doi: string | null; title: string | null }[];
    };
    reference?: Reference & {
      source_title: string;
      target_title: string;
      source_id: number;
      target_id: number;
    };
  }[];
  limit: number;
};
export function errorMessage(error: unknown) {
  return localizeMessage(
    error instanceof Error ? error.message : String(error),
  );
}
export function dateLabel(value: string | null) {
  return value
    ? new Date(
        value.includes("T") ? value : value.replace(" ", "T") + "Z",
      ).toLocaleDateString(i18n.resolvedLanguage || "en", {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : i18n.t("labels.pending");
}
export type Relationship =
  | "CITES"
  | "SHARED_AUTHOR"
  | "SAME_COLLECTION"
  | "TITLE_SIMILARITY"
  | "SHARED_KEYWORDS"
  | "SHARED_REFERENCES"
  | "SEMANTIC_SIMILARITY";
export type Reference = {
  id: number;
  source_paper_id: number;
  target_paper_id: number | null;
  citation_order: number;
  title: string | null;
  authors_text: string | null;
  journal: string | null;
  year: number | null;
  doi: string | null;
  raw_citation: string;
  resolution_status: "unresolved" | "candidate" | "resolved";
  resolution_confidence: number | null;
};
export type ScientificSection = {
  id: number;
  parent_section_id: number | null;
  section_type: string;
  heading: string;
  text: string;
  page_start: number | null;
  page_end: number | null;
  section_order: number;
};
export type SourceSpan = {
  id: number;
  section_id: number | null;
  reference_id: number | null;
  page: number;
  char_start: number | null;
  char_end: number | null;
  text: string;
  source_type: string;
  coordinates_json: string | null;
};
export function jobLabel(job: Job) {
  if (job.message_key) return i18n.t(job.message_key);
  const result = job.message?.match(
    /^(\d+) PDFs checked(?: · (\d+) warnings)?$/,
  );
  if (result)
    return i18n.t("jobs.checked", {
      count: Number(result[1]),
      errors: Number(result[2] || 0),
    });
  if (!job.message || job.message === "Discovering PDFs…")
    return i18n.t("labels.discovered");
  if (/\.pdf$/i.test(job.message)) return job.message;
  return localizeMessage(job.message);
}

export type AskResponse = {
  response_id?: string;
  trail?: {
    state: "recorded" | "failed";
    session_id?: number;
    question_event_id?: number;
    retrieval_event_id?: number;
    result_event_id?: number;
    warning?: string;
  };
  question: string;
  answer: string;
  insufficient_evidence: boolean;
  citations: string[];
  limitations: string[];
  papers: { paper_id: number; title: string }[];
  retrieval_metadata: Record<string, unknown>;
  execution_metadata?: {
    generation_attempts: number;
    repair_attempted: boolean;
    repair_reason: string[];
    first_validation_errors: { category: string; code: string }[];
    final_validation_errors: { category: string; code: string }[];
    final_status:
      | "accepted"
      | "rejected"
      | "generation_failed"
      | "no_evidence"
      | "not_configured";
  };
  evidence: {
    evidence_id: string;
    unit_id: string;
    paper_id: number;
    paper_title: string;
    section: string | null;
    page_start: number | null;
    page_end: number | null;
    text: string;
    provenance: string;
    evidence_role: string;
    supports_paginated_evidence: boolean;
  }[];
};

export type EvidenceDecision = "included" | "excluded" | "uncertain";
export type SavedEvidence = {
  related_claims?: {
    id: number;
    review_status: "draft" | "reviewed";
    archived_at: string | null;
  }[];
  id: number;
  session_id: number;
  paper_id: number | null;
  evidence_fingerprint: string;
  paper_sha256: string;
  paper_title_snapshot: string;
  paper_doi_snapshot: string | null;
  evidence_unit_id: string;
  source_span_id: number | null;
  section_id: number | null;
  section_heading_snapshot: string | null;
  evidence_role: string;
  provenance_level: string;
  page_start: number | null;
  page_end: number | null;
  supports_paginated_evidence: boolean;
  text_snapshot: string;
  text_sha256: string;
  decision: EvidenceDecision;
  user_note: string;
  origin_type: "ask_answer" | "retrieved_source";
  research_event_id: number | null;
  question_snapshot: string | null;
  evidence_label_snapshot: string | null;
  source_available: boolean;
  created_at: string;
  updated_at: string;
};
export type ResearchEvidenceList = {
  items: SavedEvidence[];
  counts: Record<EvidenceDecision | "total", number>;
};

export type TrailActor = "user" | "ai" | "system";
export type TrailItem = {
  claim_id?: number;
  id: number;
  session_id: number;
  event_type: string;
  actor_type: TrailActor;
  created_at: string;
  object_type: string | null;
  object_id: string | null;
  payload_version: number;
  payload_sha256: string;
  legacy: boolean;
  metadata: Record<string, unknown>;
  evidence_available: boolean;
  event_links: { field: string; event_id: number; session_id: number }[];
  paper_links: { paper_id: number; available: boolean }[];
};
export type TrailPage = {
  items: TrailItem[];
  next_after_event_id: number | null;
  has_legacy_activity: boolean;
};

export type ClaimRelation = "supports" | "contradicts" | "context";
export type ClaimStatus = "draft" | "reviewed";
export type ClaimLink = {
  id: number;
  claim_id: number;
  saved_evidence_id: number | null;
  relation: ClaimRelation;
  evidence_fingerprint: string;
  paper_sha256: string;
  text_sha256: string;
  paper_title_snapshot: string;
  section_heading_snapshot: string | null;
  page_start: number | null;
  page_end: number | null;
  provenance_level: string;
  decision_at_link: EvidenceDecision;
  current_decision: EvidenceDecision | null;
  current_paper_id: number | null;
  source_removed: boolean;
  source_available: boolean;
  source_snapshot_event_id: number | null;
  source_snapshot_available: boolean;
};
export type ResearchClaim = {
  id: number;
  session_id: number;
  statement: string;
  researcher_note: string;
  review_status: ClaimStatus;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
  counts: Record<ClaimRelation, number>;
  evidence_count: number;
  review_warning: boolean;
  links: ClaimLink[];
};
export type ClaimList = {
  items: ResearchClaim[];
  counts: Record<"all" | ClaimStatus | "archived", number>;
  next_after_id: number | null;
};
