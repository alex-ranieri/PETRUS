import { test, expect } from "@playwright/test";

async function setup(browser, locale) {
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

for (const locale of ["en", "pt-BR"]) {
  test(`save, human review, exact note, filters and reopen ${locale}`, async ({
    browser,
  }) => {
    const { page, context, state, en, ask, research } = await setup(
      browser,
      locale,
    );
    await ask();
    expect(state.items).toHaveLength(0);
    await page.getByRole("button", { name: "[E6]", exact: true }).click();
    const first = page.locator("#evidence-E6");
    await expect(first).toHaveClass(/highlighted/);
    await first
      .getByRole("button", {
        name: en ? "Save evidence" : "Salvar evidência",
        exact: true,
      })
      .click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await expect(dialog.getByRole("combobox")).toHaveValue("");
    expect(state.items).toHaveLength(0);
    await dialog.getByRole("combobox").selectOption("1");
    await dialog
      .getByRole("button", { name: en ? "Save" : "Salvar", exact: true })
      .click();
    await expect(
      first.getByRole("button", { name: en ? "Saved" : "Salva", exact: true }),
    ).toBeDisabled();
    expect(state.items).toHaveLength(1);
    expect(state.items[0].decision).toBe("uncertain");
    await page
      .locator("#evidence-E2")
      .getByRole("button", {
        name: en ? "Save evidence" : "Salvar evidência",
        exact: true,
      })
      .click();
    await expect.poll(() => state.items.length).toBe(2);
    await research();
    const cards = page.locator(".saved-evidence-card");
    await expect(cards).toHaveCount(2);
    const item = cards.filter({
      has: page.getByRole("heading", {
        name: "Coordinate source",
        exact: true,
      }),
    });
    await expect(item.locator("blockquote")).toHaveText(
      "Exact source ç\n  second line",
    );
    await item.getByRole("combobox").selectOption("included");
    const note = "  Human note ç 漢字\n  exact spaces  ";
    await item
      .getByLabel(en ? "Research note" : "Nota do pesquisador", { exact: true })
      .fill(note);
    expect(state.items[0].user_note).toBe("");
    await item
      .getByRole("button", {
        name: en ? "Save note" : "Salvar nota",
        exact: true,
      })
      .click();
    await expect.poll(() => state.items[0].user_note).toBe(note);
    const filters = page.getByRole("group", {
      name: en ? "Filter evidence" : "Filtrar evidências",
    });
    await filters
      .getByRole("button", { name: en ? /^Included/ : /^Incluídas/ })
      .click();
    await expect(cards).toHaveCount(1);
    await item.getByRole("combobox").selectOption("excluded");
    await expect(cards).toHaveCount(0);
    await filters
      .getByRole("button", { name: en ? /^Excluded/ : /^Excluídas/ })
      .click();
    await expect(cards).toHaveCount(1);
    await item.getByRole("combobox").selectOption("uncertain");
    await filters
      .getByRole("button", { name: en ? /^Uncertain/ : /^Incertas/ })
      .click();
    await expect(cards).toHaveCount(2);
    await item.getByRole("combobox").selectOption("included");
    await page.reload();
    await research();
    await expect(cards).toHaveCount(2);
    await expect(
      item.getByLabel(en ? "Research note" : "Nota do pesquisador", {
        exact: true,
      }),
    ).toHaveValue(note);
    await expect(item.getByRole("combobox")).toHaveValue("included");
    await item.scrollIntoViewIfNeeded();
    await page.screenshot({
      path: test.info().outputPath("workspace.png"),
      fullPage: true,
    });
    await item
      .getByRole("button", { name: en ? "Open PDF" : "Abrir PDF", exact: true })
      .click();
    expect(state.actions.at(-1)).toMatchObject({
      id: 2,
      action: "open",
      page: 2,
    });
    await item
      .getByRole("button", {
        name: en ? "View in library" : "Ver na biblioteca",
        exact: true,
      })
      .click();
    await expect(
      page.getByRole("heading", { name: "Coordinate source", exact: true }),
    ).toBeVisible();
    await page
      .getByRole("button", {
        name: en ? "Close paper details" : "Fechar detalhes do artigo",
        exact: true,
      })
      .click();
    await research();
    state.unavailable = true;
    // Remount to project current source availability while retaining snapshots.
    await page
      .getByRole("button", { name: en ? "Home" : "Início", exact: true })
      .click();
    await research();
    await expect(item.getByRole("status")).toHaveText(
      en ? "Source currently unavailable" : "Fonte indisponível no momento",
    );
    await expect(item.locator("blockquote")).toHaveText(
      "Exact source ç\n  second line",
    );
    await expect(
      item.getByRole("button", {
        name: en ? "Open PDF" : "Abrir PDF",
        exact: true,
      }),
    ).toHaveCount(0);
    await item
      .getByRole("button", {
        name: en ? "Remove evidence" : "Remover evidência",
        exact: true,
      })
      .click();
    await expect(cards).toHaveCount(1);
    await expect(cards.first()).toContainText(
      en ? "Page unavailable" : "Página não determinada",
    );
    expect(state.calls.filter((c) => c.method === "ask")).toHaveLength(1);
    await context.close();
  });

  test(`retrieved source and create session in picker ${locale}`, async ({
    browser,
  }) => {
    const { page, context, state, en, ask, research } = await setup(
      browser,
      locale,
    );
    state.failed = true;
    await ask();
    await expect(
      page.getByRole("button", {
        name: en
          ? "Save accepted answer to session"
          : "Salvar resposta aceita na sessão",
        exact: true,
      }),
    ).toHaveCount(0);
    await page
      .getByRole("button", {
        name: en
          ? "Retrieved sources · Save evidence (2)"
          : "Fontes recuperadas · Salvar evidência (2)",
        exact: true,
      })
      .click();
    await expect(page.locator("#ask-evidence-heading")).toBeInViewport();
    await page
      .locator("#evidence-E2")
      .getByRole("button", {
        name: en ? "Save evidence" : "Salvar evidência",
        exact: true,
      })
      .click();
    const dialog = page.getByRole("dialog");
    await dialog
      .getByLabel(en ? "New session title" : "Título da nova sessão", {
        exact: true,
      })
      .fill("New workspace");
    await dialog
      .getByRole("button", {
        name: en ? "Create Research Session" : "Criar sessão de pesquisa",
        exact: true,
      })
      .click();
    await expect(dialog.getByRole("combobox")).toHaveValue("2");
    expect(state.items).toHaveLength(0);
    await dialog
      .getByRole("button", { name: en ? "Save" : "Salvar", exact: true })
      .click();
    await expect.poll(() => state.items.length).toBe(1);
    expect(state.items[0]).toMatchObject({
      session_id: 2,
      decision: "uncertain",
      user_note: "",
      origin_type: "retrieved_source",
      page_start: null,
    });
    await research("New workspace");
    await expect(page.locator(".saved-evidence-card")).toContainText(
      en
        ? "Retrieved source — not an accepted answer"
        : "Fonte recuperada — sem resposta aceita",
    );
    // Asking again with this explicitly selected session shows the same card as saved.
    await ask();
    await expect(
      page
        .locator("#evidence-E2")
        .getByRole("button", { name: en ? "Saved" : "Salva", exact: true }),
    ).toBeDisabled();
    expect(state.items).toHaveLength(1);
    await context.close();
  });
  test(`target selection does not save cards or answer ${locale}`, async ({
    browser,
  }) => {
    const { page, context, state, en, ask } = await setup(browser, locale);
    await ask();
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
    await expect(dialog).toHaveCount(0);
    expect(state.items).toHaveLength(0);
    expect(
      state.calls.filter((call) =>
        ["research_evidence_save", "save_ask_event"].includes(call.method),
      ),
    ).toHaveLength(0);
    await page
      .getByRole("button", {
        name: en
          ? "Save accepted answer to session"
          : "Salvar resposta aceita na sessão",
        exact: true,
      })
      .click();
    await expect
      .poll(
        () =>
          state.calls.filter((call) => call.method === "save_ask_event").length,
      )
      .toBe(1);
    expect(state.items).toHaveLength(0);
    await page
      .locator("#evidence-E6")
      .getByRole("button", {
        name: en ? "Save evidence" : "Salvar evidência",
        exact: true,
      })
      .click();
    await expect.poll(() => state.items.length).toBe(1);
    expect(
      state.calls.find((call) => call.method === "research_evidence_save")
        .params.research_event_id,
    ).toBe(1);
    await context.close();
  });
}
