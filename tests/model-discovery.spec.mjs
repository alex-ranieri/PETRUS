import { test, expect } from "@playwright/test";

const model = (id, category, extra = {}) => ({
  id,
  category,
  type: category,
  display_name: null,
  architecture: null,
  format: null,
  parameters: null,
  quantization: null,
  size_bytes: null,
  loaded: null,
  reasoning: { configurable: null, can_disable: null },
  ...extra,
});
const initialModels = [
  model("qwen/qwen3.5-9b", "llm", {
    display_name: "Qwen 9B",
    parameters: "9B",
    format: "mlx",
    quantization: "4bit",
    loaded: true,
    reasoning: { configurable: true, can_disable: true },
  }),
  model("模型/ação:9b", "llm"),
  model("nomic", "embedding"),
  model("future/runtime", "unknown"),
];

async function setup(browser, locale, overrides = {}) {
  const context = await browser.newContext({ locale });
  const page = await context.newPage();
  const settings = {
    theme: "light",
    language: locale,
    auto_scan: false,
    watch_folders: false,
    ai_provider: "None",
    ai_endpoint: "",
    ai_model: "",
    scientific_parser: "simple",
    grobid_endpoint: "http://127.0.0.1:8070",
    grobid_fallback: true,
    embedding_provider: "lmstudio",
    embedding_endpoint: "http://127.0.0.1:1234/v1",
    embedding_model: "nomic",
    embedding_max_chars: 6000,
    llm_provider: "lmstudio",
    llm_endpoint: "http://127.0.0.1:1234",
    llm_model: "qwen/qwen3.5-9b",
    llm_temperature: 0.1,
    llm_max_output_tokens: 1600,
    llm_timeout_seconds: 90,
    llm_query_expansion: false,
    ...overrides,
  };
  const state = {
    settings,
    models: structuredClone(initialModels),
    calls: [],
    offline: false,
    delay: 0,
    saves: [],
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
  await page.exposeFunction("catalogIPC", async (command, args) => {
    if (command === "set_menu_language" || command.startsWith("plugin:event|"))
      return 1;
    if (command !== "engine_call") throw new Error(`Unexpected IPC ${command}`);
    state.calls.push(args);
    if (args.method === "snapshot") return snapshot;
    if (args.method === "papers") return { papers: [], total: 0 };
    if (args.method === "llm_models") {
      const result = structuredClone(state.models);
      if (state.delay)
        await new Promise((resolve) => setTimeout(resolve, state.delay));
      if (state.offline) throw new Error("synthetic offline PRIVATE");
      return { models: result };
    }
    if (args.method === "save_settings") {
      state.saves.push(args.params);
      Object.assign(settings, args.params);
      return settings;
    }
    if (args.method === "llm_status") return { state: "available" };
    throw new Error(`Unexpected method ${args.method}`);
  });
  await page.addInitScript(() => {
    window.isTauri = true;
    window.__TAURI_INTERNALS__ = {
      invoke: (cmd, args) => window.catalogIPC(cmd, args),
      transformCallback: () => 1,
      unregisterCallback: () => undefined,
    };
  });
  await page.goto("/");
  await expect(page.locator(".splash")).toHaveCount(0);
  const english = locale === "en";
  await page
    .getByRole("button", { name: english ? /^Settings/ : /^Configurações/ })
    .click();
  const ai = page
    .locator(".settings-nav")
    .getByRole("button", { name: english ? "AI" : "IA", exact: true });
  await ai.click();
  const llm = page.getByRole("group", { name: "LLM", exact: true });
  const embedding = page.getByRole("group", { name: "Embedding", exact: true });
  const chat = llm.getByLabel(english ? "Chat model" : "Modelo de chat", {
    exact: true,
  });
  const embed = embedding.getByLabel(
    english ? "Embedding model" : "Modelo de embedding",
    { exact: true },
  );
  const refreshName = english ? "Refresh models" : "Atualizar modelos";
  const save = page.getByRole("button", {
    name: english ? "Save settings" : "Salvar configurações",
    exact: true,
  });
  return {
    context,
    page,
    state,
    llm,
    embedding,
    chat,
    embed,
    ai,
    save,
    refreshName,
    english,
  };
}

for (const locale of ["en", "pt-BR"]) {
  test(`model discovery explicit selection, refresh and persistence ${locale}`, async ({
    browser,
  }) => {
    const {
      context,
      page,
      state,
      llm,
      embedding,
      chat,
      embed,
      ai,
      save,
      refreshName,
      english,
    } = await setup(browser, locale);
    await expect(
      chat.locator("option[value='model:模型/ação:9b']"),
    ).toHaveCount(1);
    await expect(embed.locator("option[value='model:nomic']")).toHaveCount(1);
    await expect(chat.locator("option[value='model:nomic']")).toHaveCount(0);
    await expect(
      embed.locator("option[value='model:qwen/qwen3.5-9b']"),
    ).toHaveCount(0);
    await expect(chat.locator("optgroup option")).toHaveText([
      "future/runtime",
    ]);
    await expect(
      chat.locator("option[value='model:qwen/qwen3.5-9b']"),
    ).toContainText(
      english ? "Reasoning off supported" : "Suporta reasoning desligado",
    );
    await expect(chat.locator("option[value='model:模型/ação:9b']")).toHaveText(
      "模型/ação:9b",
    );
    expect(state.saves).toHaveLength(0);
    await chat.selectOption("model:模型/ação:9b");
    expect(state.settings.llm_model).toBe("qwen/qwen3.5-9b");
    state.delay = 400;
    state.models.push(model("new-chat", "llm"));
    await llm.getByRole("button", { name: refreshName, exact: true }).click();
    await expect(
      llm.getByRole("button", {
        name: english ? "Loading models…" : "Carregando modelos…",
      }),
    ).toBeDisabled();
    await expect(chat.locator("option[value='model:new-chat']")).toHaveCount(1);
    await expect(chat).toHaveValue("model:模型/ação:9b");
    expect(state.saves).toHaveLength(0);
    expect(
      state.calls.filter((c) => c.method.endsWith("_status")),
    ).toHaveLength(0);
    await save.click();
    await expect.poll(() => state.settings.llm_model).toBe("模型/ação:9b");
    expect(state.settings.embedding_model).toBe("nomic");
    expect(state.settings.llm_max_output_tokens).toBe(1600);
    expect(state.settings.llm_timeout_seconds).toBe(90);
    // Reopen AI: selection comes from the persisted snapshot, not a catalog default.
    await page.locator(".settings-nav button").first().click();
    await ai.click();
    await expect(chat).toHaveValue("model:模型/ação:9b");
    state.models.push(model("nomic/new-ü", "embedding"));
    await embedding
      .getByRole("button", { name: refreshName, exact: true })
      .click();
    await expect(
      embed.locator("option[value='model:nomic/new-ü']"),
    ).toHaveCount(1);
    await embed.selectOption("model:nomic/new-ü");
    await save.click();
    await expect.poll(() => state.settings.embedding_model).toBe("nomic/new-ü");
    await llm
      .getByRole("button", {
        name: english ? "Save and check connection" : "Salvar e testar conexão",
      })
      .click();
    await expect
      .poll(() => state.calls.filter((c) => c.method === "llm_status").length)
      .toBe(1);
    await context.close();
  });

  test(`missing, offline and custom IDs preserved ${locale}`, async ({
    browser,
  }) => {
    const {
      context,
      page,
      state,
      llm,
      chat,
      embed,
      save,
      refreshName,
      english,
    } = await setup(browser, locale, {
      llm_model: "saved/missing",
      embedding_model: "saved/embedding",
    });
    await expect(chat.locator("option:checked")).toContainText(
      english
        ? "Configured — currently unavailable"
        : "Configurado — indisponível no momento",
    );
    await expect(embed).toHaveValue("model:saved/embedding");
    state.offline = true;
    await llm.getByRole("button", { name: refreshName, exact: true }).click();
    await expect(llm.getByRole("status")).toContainText(
      english
        ? "Unable to read LM Studio models."
        : "Não foi possível ler os modelos do LM Studio.",
    );
    await expect(chat).toHaveValue("model:saved/missing");
    expect(state.settings.llm_model).toBe("saved/missing");
    expect(state.settings.embedding_model).toBe("saved/embedding");
    expect(state.saves).toHaveLength(0);
    await expect(page.locator("body")).not.toContainText("PRIVATE");
    await chat.selectOption("custom");
    const manual = llm.getByLabel(
      english ? "Custom model ID…" : "ID de modelo personalizado…",
      { exact: true },
    );
    await expect(manual).toHaveValue("saved/missing");
    await manual.fill(" custom/模型:β ");
    await save.click();
    await expect.poll(() => state.settings.llm_model).toBe(" custom/模型:β ");
    expect(state.settings.embedding_model).toBe("saved/embedding");
    state.offline = false;
    state.models = [];
    await llm.getByRole("button", { name: refreshName, exact: true }).click();
    await expect(llm.getByRole("status")).toHaveText(
      english ? "No models available" : "Nenhum modelo disponível",
    );
    await expect(manual).toHaveValue(" custom/模型:β ");
    await context.close();
  });

  test(`empty selection and OpenAI manual provider ${locale}`, async ({
    browser,
  }) => {
    const { context, state, llm, chat, embed, save, refreshName, english } =
      await setup(browser, locale, {
        llm_model: "",
        embedding_model: "",
        embedding_provider: "none",
      });
    await expect(
      chat.locator("option[value='model:qwen/qwen3.5-9b']"),
    ).toHaveCount(1);
    await expect(chat).toHaveValue("");
    await expect(chat.locator("option:checked")).toHaveText(
      english ? "Select a model" : "Selecionar um modelo",
    );
    await expect(embed).toHaveCount(0);
    expect(state.settings.embedding_model).toBe("");
    const calls = state.calls.filter((c) => c.method === "llm_models").length;
    await llm
      .getByRole("combobox", { name: "Provider", exact: true })
      .selectOption("openai_compatible");
    await expect(chat).toHaveCount(0);
    await expect(
      llm.getByRole("button", { name: refreshName, exact: true }),
    ).toHaveCount(0);
    await llm
      .getByLabel(english ? "Exact model ID" : "ID exato do modelo", {
        exact: true,
      })
      .fill("custom/openai");
    await save.click();
    await expect.poll(() => state.settings.llm_model).toBe("custom/openai");
    expect(state.calls.filter((c) => c.method === "llm_models")).toHaveLength(
      calls,
    );
    expect(state.settings.llm_provider).toBe("openai_compatible");
    await context.close();
  });
}
