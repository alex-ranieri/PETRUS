import { test, expect } from "@playwright/test";

for (const locale of ["en", "pt-BR"]) {
  test(`Ask evidence navigation and labels ${locale}`, async ({ browser }) => {
    const context = await browser.newContext({ locale });
    const page = await context.newPage();
    const settings = {
      theme: "light",
      auto_scan: false,
      watch_folders: false,
      ai_provider: "None",
      ai_endpoint: "",
      ai_model: "",
      language: locale,
      scientific_parser: "simple",
      grobid_endpoint: "http://127.0.0.1:8070",
      grobid_fallback: true,
      embedding_provider: "none",
      embedding_endpoint: "",
      embedding_model: "",
      embedding_max_chars: 6000,
      llm_provider: "none",
      llm_endpoint: "",
      llm_model: "qwen/qwen3.5-9b",
      llm_temperature: 0.1,
      llm_query_expansion: false,
    };
    const snapshot = {
      libraries: [
        { id: 1, name: "Synthetic", root_path: "/synthetic", file_count: 1 },
      ],
      stats: { papers: 1, indexed: 1, attention: 0, collections: 0 },
      collections: [],
      jobs: [],
      sessions: [],
      issues: [],
      issues_total: 0,
      settings,
      data_dir: "/synthetic",
      database_path: "/synthetic/test.sqlite3",
      grobid: { state: "unavailable", endpoint: "" },
      facets: { years: [], journals: [], authors: [] },
    };
    let savedSettings;
    await page.exposeFunction("askIPC", async (command, args) => {
      if (
        command === "set_menu_language" ||
        command.startsWith("plugin:event|")
      )
        return 1;
      if (command === "engine_call") {
        if (args.method === "snapshot") return snapshot;
        if (args.method === "llm_models") return { models: [] };
        if (args.method === "save_settings") {
          savedSettings = args.params;
          Object.assign(settings, args.params);
          return settings;
        }
        if (args.method === "papers") return { papers: [], total: 0 };
        if (args.method === "ask") {
          const failed = args.params.question === "FAIL";
          const abstained = args.params.question === "ABSTAIN";
          if (failed) await new Promise((resolve) => setTimeout(resolve, 500));
          return {
            question: args.params.question,
            answer: failed
              ? "INVALID OUTPUT [E99]"
              : abstained
                ? locale === "en"
                  ? "I could not find sufficient evidence in the indexed library to answer this confidently."
                  : "Não encontrei evidência suficiente na biblioteca indexada para responder com confiança."
                : locale === "en"
                  ? "Synthetic method [E1].\n\nUnmapped context [E2]."
                  : "Método sintético [E1].\n\nContexto sem página [E2].",
            insufficient_evidence: abstained,
            citations: failed || abstained ? [] : ["E1", "E2"],
            limitations: failed ? ["llm_response_rejected"] : [],
            execution_metadata: {
              generation_attempts: failed ? 2 : 1,
              repair_attempted: failed,
              repair_reason: failed ? ["invalid_json"] : [],
              first_validation_errors: [],
              final_validation_errors: [],
              final_status: failed ? "rejected" : "accepted",
            },
            papers: [{ paper_id: 1, title: "Controlled paper" }],
            retrieval_metadata: {},
            evidence: [
              {
                evidence_id: "E1",
                unit_id: "span:1",
                paper_id: 1,
                paper_title: "Controlled paper",
                section: "Original Methods",
                page_start: 2,
                page_end: 2,
                text: "Original synthetic source text.",
                provenance: "coordinate",
                evidence_role: "methods",
                supports_paginated_evidence: true,
              },
              {
                evidence_id: "E2",
                unit_id: "section:2",
                paper_id: 1,
                paper_title: "Controlled paper",
                section: "Original Discussion",
                page_start: null,
                page_end: null,
                text: "Original unmapped source text.",
                provenance: "section_only",
                evidence_role: "discussion",
                supports_paginated_evidence: false,
              },
            ],
          };
        }
        if (args.method === "graph")
          return {
            nodes: [
              { id: "1", label: "Controlled paper" },
              { id: "2", label: "Another paper" },
            ],
            edges: [
              {
                id: "semantic-1-2",
                source: "1",
                target: "2",
                type: "SEMANTIC_SIMILARITY",
                relation: "SEMANTIC_SIMILARITY",
                score: 0.9,
                metadata: { score: 0.9 },
              },
            ],
            limit: 300,
          };
      }
      throw new Error(`Unexpected IPC ${command} ${args?.method}`);
    });
    await page.addInitScript(() => {
      window.isTauri = true;
      window.__TAURI_INTERNALS__ = {
        invoke: (cmd, args) => window.askIPC(cmd, args),
        transformCallback: () => 1,
        unregisterCallback: () => undefined,
      };
    });
    await page.goto("/");
    await expect(page.locator(".splash")).toHaveCount(0);
    await page.locator(".ask-placeholder").click();
    await expect(
      page.getByRole("heading", {
        name: locale === "en" ? "Ask PETRUS" : "Pergunte ao PETRUS",
        exact: true,
      }),
    ).toBeVisible();
    await page
      .getByLabel(locale === "en" ? "Question" : "Pergunta", { exact: true })
      .fill(
        locale === "en" ? "What synthetic method?" : "Qual método sintético?",
      );
    await page
      .getByRole("button", {
        name: locale === "en" ? "Ask" : "Perguntar",
        exact: true,
      })
      .click();
    await expect(page.locator(".evidence-card")).toHaveCount(2);
    await expect(
      page.getByText(
        locale === "en" ? "Page unavailable" : "Página não determinada",
        { exact: false },
      ),
    ).toBeVisible();
    await page.getByRole("button", { name: "[E2]", exact: true }).click();
    await expect(page.locator("#evidence-E2")).toHaveClass(/highlighted/);
    await expect(page.locator("#evidence-E1")).toContainText(
      "Original synthetic source text.",
    );
    const questionField = page.getByLabel(
      locale === "en" ? "Question" : "Pergunta",
      { exact: true },
    );
    await questionField.fill("FAIL");
    await page.locator(".ask-form button").click();
    await expect(page.locator(".ask-form button")).toBeDisabled();
    await expect(page.getByRole("alert")).toContainText(
      locale === "en"
        ? "PETRUS could not produce a valid grounded response."
        : "O PETRUS não conseguiu produzir uma resposta fundamentada válida.",
    );
    await expect(
      page.getByRole("heading", {
        name: locale === "en" ? "Retrieved sources" : "Fontes recuperadas",
        exact: true,
      }),
    ).toBeVisible();
    await expect(page.locator(".ask-answer")).not.toContainText(
      "INVALID OUTPUT",
    );
    await expect(page.locator(".ask-answer")).not.toContainText(
      locale === "en" ? "Insufficient evidence" : "Evidência insuficiente",
    );
    await expect(page.locator(".evidence-citation")).toHaveCount(0);
    await expect(page.locator(".evidence-card")).toHaveCount(2);
    await questionField.fill("ABSTAIN");
    await page.locator(".ask-form button").click();
    await expect(
      page.getByRole("heading", {
        name:
          locale === "en" ? "Insufficient evidence" : "Evidência insuficiente",
        exact: true,
      }),
    ).toBeVisible();
    await expect(page.locator(".ask-answer[role=alert]")).toHaveCount(0);
    await page
      .getByRole("button", {
        name: locale === "en" ? "Explore" : "Explorar",
        exact: true,
      })
      .click();
    const semantic = page.getByRole("checkbox", {
      name: locale === "en" ? "Semantic similarity" : "Similaridade semântica",
      exact: true,
    });
    await expect(semantic).not.toBeChecked();
    await semantic.check();
    await page
      .getByText(
        locale === "en" ? "Relatedness details" : "Detalhes da relação",
        { exact: true },
      )
      .click();
    await page
      .locator(".graph-accessible button")
      .filter({
        hasText:
          locale === "en" ? "Semantic similarity" : "Similaridade semântica",
      })
      .click();
    await expect(page.locator(".citation-inspector")).toContainText(
      locale === "en"
        ? "does not imply scientific agreement"
        : "não implica concordância",
    );
    await page.getByRole("button", { name: locale === "en" ? /^Settings/ : /^Configurações/ }).click();
    await page.locator(".settings-nav").getByRole("button", { name: locale === "en" ? "AI" : "IA", exact: true }).click();
    const llmSettings = page.getByRole("group", { name: "LLM", exact: true });
    await llmSettings.getByRole("combobox").selectOption("lmstudio");
    const outputLimit = page.getByLabel(locale === "en" ? "Output token limit" : "Limite de saída (tokens)", { exact: true });
    const timeout = page.getByLabel(locale === "en" ? "Timeout per generation (seconds)" : "Tempo limite por geração (segundos)", { exact: true });
    await expect(outputLimit).toHaveValue("1600");
    await expect(timeout).toHaveValue("90");
    await outputLimit.fill("2400");
    await timeout.fill("180");
    await page.getByRole("button", { name: locale === "en" ? "Save settings" : "Salvar configurações", exact: true }).click();
    await expect.poll(() => savedSettings).toMatchObject({ llm_max_output_tokens: 2400, llm_timeout_seconds: 180, llm_model: "qwen/qwen3.5-9b" });
    await context.close();
  });
}
