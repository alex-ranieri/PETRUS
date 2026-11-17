import { test, expect } from "@playwright/test";

async function setup(browser, locale) {
  const context = await browser.newContext({
    locale,
    timezoneId: "America/Sao_Paulo",
  });
  const page = await context.newPage();
  const en = locale === "en";
  const sessions = [
    { id: 1, title: "New trail" },
    { id: 2, title: "Old workspace" },
  ];
  const calls = [];
  let persistFailed = false;
  const kinds = [
    "session_created",
    "question_asked",
    "retrieval_completed",
    "ask_accepted",
    "evidence_saved",
    "evidence_decision_changed",
    "evidence_note_updated",
    "evidence_removed",
    "ask_abstained",
    "ask_rejected",
    "ask_generation_failed",
  ];
  const actors = [
    "user",
    "user",
    "system",
    "ai",
    "user",
    "user",
    "user",
    "user",
    "ai",
    "system",
    "system",
  ];
  const metadata = [
    { title: "New trail" },
    { question: "Exact question ç", question_sha256: "a".repeat(64) },
    {
      selected_count: 1,
      paper_ids: [2],
      returned_candidate_count: 3,
      selected: [
        {
          evidence_id: "E6",
          unit_id: "span:2",
          paper_id: 2,
          lexical_rank: 1,
          semantic_rank: 2,
          text_sha256: "b".repeat(64),
        },
      ],
      query_plan: { detected_language: "en", expanded_terms: ["test"] },
      configuration: { rrf_k: 60, ranking_observed: true },
    },
    { answer: "Validated answer [E6].", citations: ["E6"], citation_count: 1 },
    {
      paper_title_snapshot: "Saved source",
      evidence_label_snapshot: "E6",
      source_snapshot: {
        paper_title_snapshot: "Saved source",
        section_heading_snapshot: "Methods",
        text_snapshot: "Durable source text",
      },
    },
    { old_decision: "uncertain", new_decision: "included" },
    {
      new_note_snapshot: "  Human note ç\n  exact  ",
      old_note_sha256: "c".repeat(64),
      new_note_sha256: "d".repeat(64),
    },
    { paper_title_snapshot: "Removed source", decision: "uncertain" },
    { answer: "Insufficient evidence", insufficient_evidence: true },
    { validation_codes: ["missing_citations"] },
    { generation_error_code: "llm_timeout" },
  ];
  const details = kinds.map((event_type, i) => ({
    id: i + 1,
    session_id: 1,
    event_type,
    actor_type: actors[i],
    created_at: `2026-10-16 12:00:${String(i).padStart(2, "0")}`,
    payload_version: 1,
    payload_sha256: "f".repeat(64),
    legacy: false,
    object_type: i >= 4 && i <= 7 ? "research_evidence" : "question",
    object_id: i === 7 ? "9" : i >= 4 && i <= 6 ? "1" : null,
    metadata: metadata[i],
    evidence_available: i >= 4 && i <= 6,
    paper_links: i === 4 ? [{ paper_id: 2, available: true }] : [],
    event_links:
      i === 3
        ? [{ field: "question_event_id", event_id: 2, session_id: 1 }]
        : [],
  }));
  const compact = (item) => ({
    ...item,
    metadata: Object.fromEntries(
      Object.entries(item.metadata).filter(
        ([key]) =>
          ![
            "question",
            "answer",
            "new_note_snapshot",
            "source_snapshot",
            "selected",
            "query_plan",
            "configuration",
          ].includes(key),
      ),
    ),
  });
  const old = [
    { ...details[0], id: 20, session_id: 2, legacy: true },
    { ...details[6], id: 21, session_id: 2, legacy: true, metadata: {} },
    {
      ...details[0],
      id: 22,
      session_id: 2,
      event_type: "trail_tracking_started",
      actor_type: "system",
      legacy: false,
    },
  ];
  const item = {
    id: 1,
    session_id: 1,
    paper_id: 2,
    evidence_unit_id: "span:2",
    paper_title_snapshot: "Saved source",
    section_heading_snapshot: "Methods",
    text_snapshot: "Durable source text",
    decision: "included",
    user_note: "Human note",
    origin_type: "ask_answer",
    source_available: true,
    provenance_level: "coordinate",
    page_start: 2,
    page_end: 2,
  };
  await page.exposeFunction("trailIPC", async (command, args) => {
    if (command === "set_menu_language" || command.startsWith("plugin:event|"))
      return 1;
    if (command !== "engine_call") throw new Error(command);
    const { method, params } = args;
    calls.push(args);
    if (method === "snapshot")
      return {
        libraries: [],
        stats: { papers: 0, indexed: 0, attention: 0, collections: 0 },
        collections: [],
        jobs: [],
        sessions,
        issues: [],
        issues_total: 0,
        settings: { language: locale, theme: "light" },
        grobid: { state: "unavailable" },
        facets: { years: [], journals: [], authors: [] },
      };
    if (method === "papers") return { papers: [], total: 0 };
    if (method === "session")
      return { ...sessions.find((s) => s.id === params.id), events: [] };
    if (method === "research_evidence_list")
      return {
        items: params.session_id === 1 ? [item] : [],
        counts: { included: 1, excluded: 0, uncertain: 0, total: 1 },
      };
    if (method === "research_trail_list") {
      const all = (params.session_id === 2 ? old : details).filter(
        (i) =>
          !params.actor_type ||
          params.actor_type === "all" ||
          i.actor_type === params.actor_type,
      );
      const start = params.after_event_id
        ? all.findIndex((i) => i.id === params.after_event_id) + 1
        : 0;
      const rows = all.slice(start, start + 6);
      return {
        items: rows.map(compact),
        has_legacy_activity: params.session_id === 2,
        next_after_event_id: start + 6 < all.length ? rows.at(-1).id : null,
      };
    }
    if (method === "research_trail_get")
      return [...details, ...old].find(
        (i) => i.id === params.event_id && i.session_id === params.session_id,
      );
    if (method === "ask")
      return {
        response_id: "receipt",
        question: params.question,
        answer: "Validated answer [E6].",
        citations: ["E6"],
        insufficient_evidence: false,
        limitations: [],
        papers: [],
        evidence: [],
        retrieval_metadata: {},
        execution_metadata: { final_status: "accepted" },
        ...(params.session_id
          ? {
              trail: {
                state: persistFailed ? "failed" : "recorded",
                session_id: 1,
                question_event_id: 2,
                result_event_id: 4,
              },
            }
          : {}),
      };
    throw new Error(method);
  });
  await page.addInitScript(() => {
    window.isTauri = true;
    window.__TAURI_INTERNALS__ = {
      invoke: (cmd, args) => window.trailIPC(cmd, args),
      transformCallback: () => 1,
      unregisterCallback: () => undefined,
    };
  });
  await page.goto("/");
  await expect(page.locator(".splash")).toHaveCount(0);
  const research = async (title = "New trail") => {
    await page
      .getByRole("button", { name: en ? "Research" : "Pesquisa", exact: true })
      .click();
    await page.getByRole("button", { name: new RegExp(title) }).click();
    await page
      .getByRole("tab", {
        name: en ? "Research Trail" : "Trilha de pesquisa",
        exact: true,
      })
      .click();
    await expect(page.locator(".research-trail-entry").first()).toBeVisible();
  };
  return {
    context,
    page,
    en,
    calls,
    research,
    fail: () => {
      persistFailed = true;
    },
  };
}

for (const locale of ["en", "pt-BR"]) {
  test(`chronology, actors, lazy expansion, links and reload ${locale}`, async ({
    browser,
  }) => {
    const { context, page, en, calls, research } = await setup(browser, locale);
    await research();
    const rows = page.locator(".research-trail-entry");
    await expect(rows).toHaveCount(6);
    expect(
      await rows.evaluateAll((nodes) => nodes.map((n) => n.dataset.eventId)),
    ).toEqual(["1", "2", "3", "4", "5", "6"]);
    expect(
      await rows.evaluateAll((nodes) => nodes.map((n) => n.dataset.actor)),
    ).toEqual(["user", "user", "system", "ai", "user", "user"]);
    expect(calls.filter((c) => c.method === "research_trail_get")).toHaveLength(
      0,
    );
    await page.locator("#trail-event-2 summary").click();
    await expect(page.locator("#trail-event-2 blockquote")).toHaveText(
      "Exact question ç",
    );
    await page.locator("#trail-event-3 summary").click();
    await expect(page.locator("#trail-event-3 table")).toContainText("span:2");
    await expect(page.locator("#trail-event-3 .trail-config")).toContainText(
      "60",
    );
    await page.locator("#trail-event-4 summary").click();
    await expect(page.locator("#trail-event-4 .reading")).toHaveText(
      "Validated answer [E6].",
    );
    await page.locator("#trail-event-4 .trail-links button").click();
    await expect(page.locator(".trail-related blockquote")).toHaveText(
      "Exact question ç",
    );
    await expect(
      page.locator("#trail-event-6 .trail-decision-change"),
    ).toContainText("→");
    await page
      .getByRole("button", {
        name: en ? "Load more events" : "Carregar mais eventos",
        exact: true,
      })
      .click();
    await expect(rows).toHaveCount(11);
    await page.locator("#trail-event-7 summary").click();
    await expect(
      page.locator("#trail-event-7 .research-human-note pre"),
    ).toHaveText("  Human note ç\n  exact  ");
    await expect(page.locator("#trail-event-8")).toContainText(
      "Removed source",
    );
    await page.screenshot({
      path: test.info().outputPath("trail.png"),
      fullPage: true,
    });
    const filter = page.locator('.research-trail [role="group"]');
    await filter.getByRole("button", { name: "PETRUS", exact: true }).click();
    await expect(rows).toHaveCount(2);
    expect(
      await rows.evaluateAll((nodes) => nodes.map((n) => n.dataset.eventId)),
    ).toEqual(["4", "9"]);
    await filter
      .getByRole("button", { name: en ? "System" : "Sistema", exact: true })
      .click();
    await expect(rows).toHaveCount(3);
    await filter
      .getByRole("button", { name: en ? "All" : "Todas", exact: true })
      .click();
    await page
      .locator("#trail-event-5")
      .getByRole("button", {
        name: en ? "View evidence" : "Ver evidência",
        exact: true,
      })
      .click();
    await expect(page.locator("#research-evidence-1")).toBeFocused();
    await page.reload();
    await research();
    expect(
      await rows.evaluateAll((nodes) => nodes.map((n) => n.dataset.eventId)),
    ).toEqual(["1", "2", "3", "4", "5", "6"]);
    expect(calls.filter((c) => c.method === "ask")).toHaveLength(0);
    await context.close();
  });
  test(`legacy boundary and unknown old notes ${locale}`, async ({
    browser,
  }) => {
    const { context, page, en, research } = await setup(browser, locale);
    await research("Old workspace");
    await expect(page.locator(".research-trail .notice")).toBeVisible();
    await expect(page.locator(".research-trail-entry")).toHaveCount(3);
    await page.locator("#trail-event-21 summary").click();
    await expect(page.locator("#trail-event-21 .hint")).toContainText(
      en ? "did not record" : "não registrou",
    );
    await context.close();
  });
  test(`explicit target before Ask, exploratory and persistence warning ${locale}`, async ({
    browser,
  }) => {
    const { context, page, en, calls, fail } = await setup(browser, locale);
    await page.locator(".ask-placeholder").click();
    const input = page.getByLabel(en ? "Question" : "Pergunta", {
      exact: true,
    });
    await input.fill("Question");
    await page.locator(".ask-form button").click();
    await expect
      .poll(() => calls.filter((c) => c.method === "ask").length)
      .toBe(1);
    expect(calls.find((c) => c.method === "ask").params).not.toHaveProperty(
      "session_id",
    );
    await page
      .getByRole("button", {
        name: en ? "Choose target session" : "Escolher sessão-alvo",
        exact: true,
      })
      .click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("combobox").selectOption("1");
    await dialog
      .getByRole("button", {
        name: en ? "Use session" : "Usar sessão",
        exact: true,
      })
      .click();
    await page.locator(".ask-form button").click();
    await expect(page.locator('.ask-page > [role="status"]')).toContainText(
      en ? "Recorded" : "Registrado",
    );
    expect(
      calls.filter((c) => c.method === "ask").at(-1).params.session_id,
    ).toBe(1);
    fail();
    await page.locator(".ask-form button").click();
    await expect(page.locator('.ask-page [role="alert"]')).toContainText(
      en ? "not fully recorded" : "não foi registrada por completo",
    );
    expect(calls.filter((c) => c.method === "ask")).toHaveLength(3);
    expect(
      calls.filter((c) =>
        ["research_evidence_save", "save_ask_event"].includes(c.method),
      ),
    ).toHaveLength(0);
    await context.close();
  });
}
