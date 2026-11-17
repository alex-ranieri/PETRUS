import { test, expect } from "@playwright/test";

export async function setup(browser, locale) {
  const context = await browser.newContext({ locale });
  const page = await context.newPage();
  const en = locale === "en";
  const settings = {
    language: locale,
    theme: "light",
    auto_scan: false,
    watch_folders: false,
  };
  const session = {
    id: 1,
    title: "Human workspace",
    research_question: "",
    description: "",
    created_at: "2026-10-16",
  };
  const state = {
    sessions: [session],
    items: [],
    calls: [],
    actions: [],
    events: [],
    claims: [],
    links: [],
    failed: false,
    unavailable: false,
  };
  const evidence = [
    {
      evidence_id: "E6",
      unit_id: "span:2",
      paper_id: 2,
      paper_title: "Coordinate source",
      section: "Methods",
      page_start: 2,
      page_end: 2,
      text: "Exact source ç\n  second line",
      provenance: "coordinate",
      evidence_role: "methods",
      supports_paginated_evidence: true,
    },
    {
      evidence_id: "E2",
      unit_id: "section:3",
      paper_id: 3,
      paper_title: "Unmapped source",
      section: "Discussion",
      page_start: null,
      page_end: null,
      text: "Unmapped original source",
      provenance: "section_only",
      evidence_role: "discussion",
      supports_paginated_evidence: false,
    },
  ];
  const snapshot = {
    libraries: [
      { id: 1, name: "Synthetic", root_path: "/synthetic", file_count: 2 },
    ],
    stats: { papers: 2, indexed: 2, attention: 0, collections: 0 },
    collections: [],
    jobs: [],
    sessions: state.sessions,
    issues: [],
    issues_total: 0,
    settings,
    data_dir: "/synthetic",
    database_path: "/synthetic/test.sqlite3",
    grobid: { state: "unavailable", endpoint: "" },
    facets: { years: [], journals: [], authors: [] },
  };
  await page.exposeFunction("workspaceIPC", async (command, args) => {
    if (command === "set_menu_language" || command.startsWith("plugin:event|"))
      return 1;
    if (command === "paper_action") {
      state.actions.push(args);
      return { page_open_supported: true };
    }
    if (command !== "engine_call") throw new Error(command);
    const { method, params } = args;
    state.calls.push(args);
    if (method === "snapshot") return snapshot;
    if (method === "papers") return { papers: [], total: 0 };
    if (method === "ask")
      return {
        response_id: "receipt",
        question: params.question,
        answer: "Answer [E6].",
        insufficient_evidence: false,
        citations: ["E6"],
        limitations: [],
        papers: [],
        retrieval_metadata: {},
        execution_metadata: {
          final_status: state.failed ? "generation_failed" : "accepted",
        },
        evidence,
      };
    if (method === "new_session") {
      const newSession = {
        ...session,
        id: state.sessions.length + 1,
        title: params.title,
      };
      state.sessions.push(newSession);
      return { id: newSession.id };
    }
    if (method === "session")
      return {
        ...state.sessions.find((s) => s.id === params.id),
        events: state.events,
      };
    if (method === "save_ask_event") {
      state.events.push({ id: 1, event_type: "ask", created_at: "2026-10-16" });
      return { event_id: 1 };
    }
    if (method === "research_evidence_save") {
      const source = params.evidence;
      let item = state.items.find(
        (i) =>
          i.session_id === params.session_id &&
          i.evidence_unit_id === source.unit_id,
      );
      if (!item) {
        item = {
          id: state.items.length + 1,
          evidence_fingerprint: "fixture-fingerprint-" + source.unit_id,
          session_id: params.session_id,
          paper_id: source.paper_id,
          evidence_unit_id: source.unit_id,
          paper_title_snapshot: source.paper_title,
          section_heading_snapshot: source.section,
          page_start: source.page_start,
          page_end: source.page_end,
          text_snapshot: source.text,
          provenance_level: source.provenance,
          origin_type: state.failed ? "retrieved_source" : "ask_answer",
          decision: "uncertain",
          user_note: "",
          source_available: true,
          question_snapshot: "Original question",
          evidence_label_snapshot: source.evidence_id,
        };
        state.items.push(item);
      }
      return { item, created: true };
    }
    const now = () => new Date().toISOString();
    const emit = (kind, claim, metadata = {}) =>
      state.events.push({
        id: state.events.length + 1,
        session_id: claim.session_id,
        event_type: kind,
        actor_type: "user",
        object_type: "research_claim",
        object_id: String(claim.id),
        claim_id: claim.id,
        created_at: now(),
        payload_version: 1,
        payload_sha256: "f".repeat(64),
        legacy: false,
        evidence_available: false,
        event_links: [],
        paper_links: [],
        metadata: { claim_id: claim.id, ...metadata },
      });
    const detail = (claim) => {
      const links = state.links
        .filter((l) => l.claim_id === claim.id)
        .map((l) => {
          const source = state.items.find((i) => i.id === l.original_id);
          return {
            ...l,
            saved_evidence_id: source?.id ?? null,
            current_paper_id: source?.paper_id ?? null,
            current_decision: source?.decision ?? null,
            source_removed: !source,
            source_available: !!source && !state.unavailable,
            source_snapshot_event_id: 1,
            source_snapshot_available: true,
          };
        });
      return {
        ...claim,
        links,
        evidence_count: links.length,
        counts: Object.fromEntries(
          ["supports", "contradicts", "context"].map((k) => [
            k,
            links.filter((l) => l.relation === k).length,
          ]),
        ),
        review_warning:
          claim.review_status === "reviewed" &&
          (!links.length || links.some((l) => !l.source_available)),
      };
    };
    const attach = () =>
      state.items.forEach((i) => {
        i.related_claims = state.links
          .filter((l) => l.original_id === i.id)
          .map((l) => {
            const c = state.claims.find((c) => c.id === l.claim_id);
            return {
              id: c.id,
              review_status: c.review_status,
              archived_at: c.archived_at,
            };
          });
      });
    if (method === "research_claim_create") {
      const claim = {
        id: state.claims.length + 1,
        session_id: params.session_id,
        statement: params.statement,
        researcher_note: params.researcher_note ?? "",
        review_status: "draft",
        created_at: now(),
        updated_at: now(),
        archived_at: null,
      };
      state.claims.push(claim);
      emit("claim_created", claim, { statement_snapshot: claim.statement });
      return detail(claim);
    }
    if (method === "research_claim_list") {
      const all = state.claims.filter(
        (c) => c.session_id === params.session_id,
      );
      return {
        items: all
          .filter((c) =>
            params.filter === "archived"
              ? c.archived_at
              : !c.archived_at &&
                (params.filter === "all" ||
                  !params.filter ||
                  c.review_status === params.filter),
          )
          .map(detail)
          .reverse(),
        counts: {
          all: all.filter((c) => !c.archived_at).length,
          draft: all.filter(
            (c) => !c.archived_at && c.review_status === "draft",
          ).length,
          reviewed: all.filter(
            (c) => !c.archived_at && c.review_status === "reviewed",
          ).length,
          archived: all.filter((c) => c.archived_at).length,
        },
        next_after_id: null,
      };
    }
    if (method === "research_claim_get")
      return detail(state.claims.find((c) => c.id === params.id));
    if (method === "research_claim_update") {
      const claim = state.claims.find((c) => c.id === params.id);
      for (const key of ["statement", "researcher_note", "review_status"])
        if (params[key] !== undefined && params[key] !== claim[key]) {
          const kind = {
            statement: "claim_statement_updated",
            researcher_note: "claim_note_updated",
            review_status: "claim_review_status_changed",
          }[key];
          const data =
            key === "statement"
              ? { new_statement_snapshot: params[key] }
              : key === "researcher_note"
                ? { new_note_snapshot: params[key] }
                : {
                    old_review_status: claim[key],
                    new_review_status: params[key],
                  };
          emit(kind, claim, data);
          claim[key] = params[key];
        }
      claim.updated_at = now();
      attach();
      return detail(claim);
    }
    if (
      method === "research_claim_archive" ||
      method === "research_claim_restore"
    ) {
      const claim = state.claims.find((c) => c.id === params.id);
      claim.archived_at = method.endsWith("restore") ? null : now();
      emit(
        method.endsWith("restore") ? "claim_restored" : "claim_archived",
        claim,
      );
      attach();
      return detail(claim);
    }
    if (method === "research_claim_evidence_link") {
      const claim = state.claims.find((c) => c.id === params.claim_id);
      const source = state.items.find((i) => i.id === params.saved_evidence_id);
      const l = {
        id: state.links.length + 1,
        claim_id: claim.id,
        original_id: source.id,
        relation: params.relation,
        decision_at_link: source.decision,
        paper_title_snapshot: source.paper_title_snapshot,
        section_heading_snapshot: source.section_heading_snapshot,
        page_start: source.page_start,
        page_end: source.page_end,
        provenance_level: source.provenance_level,
        evidence_fingerprint: source.evidence_fingerprint,
      };
      state.links.push(l);
      emit("claim_evidence_linked", claim, { relation: l.relation });
      attach();
      return { item: l, created: true };
    }
    if (
      method === "research_claim_evidence_update" ||
      method === "research_claim_evidence_unlink"
    ) {
      const l = state.links.find((l) => l.id === params.id);
      const claim = state.claims.find((c) => c.id === l.claim_id);
      if (method.endsWith("unlink")) {
        state.links = state.links.filter((i) => i !== l);
        emit("claim_evidence_unlinked", claim);
      } else {
        emit("claim_evidence_relation_changed", claim, {
          old_relation: l.relation,
          new_relation: params.relation,
        });
        l.relation = params.relation;
      }
      attach();
      return l;
    }
    if (method === "research_trail_list")
      return {
        items: state.events,
        has_legacy_activity: false,
        next_after_event_id: null,
      };
    if (method === "research_trail_get")
      return {
        ...state.events.find((i) => i.id === params.event_id),
        metadata: {
          ...(state.events.find((i) => i.id === params.event_id)?.metadata ??
            {}),
          source_snapshot: { text_snapshot: "Exact source ç\n  second line" },
        },
      };
    if (method === "research_evidence_list") {
      const items = state.items.filter(
        (i) => i.session_id === params.session_id,
      );
      const counts = {
        included: 0,
        excluded: 0,
        uncertain: 0,
        total: items.length,
      };
      for (const i of items) counts[i.decision]++;
      return {
        items: items
          .filter(
            (i) =>
              !params.decision ||
              params.decision === "all" ||
              i.decision === params.decision,
          )
          .map((i) => ({ ...i, source_available: !state.unavailable })),
        counts,
      };
    }
    if (method === "research_evidence_update") {
      const item = state.items.find((i) => i.id === params.id);
      Object.assign(item, params);
      return item;
    }
    if (method === "research_evidence_remove") {
      state.items = state.items.filter((i) => i.id !== params.id);
      return { removed: params.id };
    }
    if (method === "paper")
      return {
        id: 2,
        title: "Coordinate source",
        authors: "Author",
        notes: "",
        files: [],
        sections: [],
        references: [],
        collections: [],
        chunks: [],
        source_spans: [],
        parser_runs: [],
        scientific_status: "structured",
        scientific_warning_codes: [],
      };
    throw new Error(`Unexpected ${method}`);
  });
  await page.addInitScript(() => {
    window.isTauri = true;
    window.__TAURI_INTERNALS__ = {
      invoke: (cmd, args) => window.workspaceIPC(cmd, args),
      transformCallback: () => 1,
      unregisterCallback: () => undefined,
    };
  });
  await page.goto("/");
  await expect(page.locator(".splash")).toHaveCount(0);
  const ask = async () => {
    await page.locator(".ask-placeholder").click();
    await page
      .getByLabel(en ? "Question" : "Pergunta", { exact: true })
      .fill("Original question");
    await page.locator(".ask-form button").click();
    await expect(page.locator(".ask-evidence-grid .evidence-card")).toHaveCount(
      2,
    );
  };
  const research = async (title = "Human workspace") => {
    await page
      .getByRole("button", { name: en ? "Research" : "Pesquisa", exact: true })
      .click();
    await page.getByRole("button", { name: new RegExp(title) }).click();
    await expect(page.locator(".research-evidence-workspace")).toBeVisible();
  };
  return { page, context, state, en, ask, research };
}
