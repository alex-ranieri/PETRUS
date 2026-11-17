import { test, expect } from "@playwright/test";
import { spawn, spawnSync } from "node:child_process";
import { createInterface } from "node:readline";
import { mkdtempSync, cpSync, readFileSync, mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import ts from "typescript";

async function harness(page) {
  const root = process.cwd(),
    dir = mkdtempSync(resolve(tmpdir(), "petrus-02-")),
    data = resolve(dir, "data"),
    library = resolve(dir, "Library");
  cpSync(resolve(root, "engine/tests/fixtures"), library, { recursive: true });
  let child,
    sequence = 0;
  const pending = new Map();
  const actions = [];
  const locales = [];
  const start = () => {
    child = spawn(
      resolve(root, ".venv/bin/python"),
      ["-m", "petrus_engine", "--data-dir", data],
      { cwd: root },
    );
    createInterface({ input: child.stdout }).on("line", (line) => {
      const r = JSON.parse(line),
        item = pending.get(r.id);
      pending.delete(r.id);
      if (r.error) item.reject(new Error(r.error));
      else item.resolve(r.result);
    });
  };
  const rpc = (method, params = {}) =>
    new Promise((resolve, reject) => {
      const id = ++sequence;
      pending.set(id, { resolve, reject });
      child.stdin.write(JSON.stringify({ id, method, params }) + "\n");
    });
  const stop = () =>
    new Promise((resolve) => {
      child.once("exit", resolve);
      child.stdin.end();
    });
  start();
  await page.exposeFunction("petrus02IPC", async (command, args) => {
    if (command === "engine_call") return rpc(args.method, args.params);
    if (command === "set_menu_language") {
      locales.push(args.locale);
      return null;
    }
    if (command === "plugin:dialog|open") return library;
    if (command === "paper_action") {
      actions.push(args);
      return null;
    }
    if (command.startsWith("plugin:event|")) return 1;
    throw new Error(command);
  });
  await page.addInitScript(() => {
    window.isTauri = true;
    window.__TAURI_INTERNALS__ = {
      invoke: (cmd, args) => window.petrus02IPC(cmd, args),
      transformCallback: () => 1,
      unregisterCallback: () => undefined,
    };
    window.__TAURI_EVENT_PLUGIN_INTERNALS__ = {
      unregisterListener: () => undefined,
    };
  });
  return {
    rpc,
    stop,
    start,
    actions,
    locales,
    seed: () => {
      const result = spawnSync(
        resolve(root, ".venv/bin/python"),
        [resolve(root, "engine/tests/seed_structured.py"), data],
        { cwd: root, encoding: "utf8" },
      );
      expect(result.status, result.stderr).toBe(0);
    },
  };
}

test("PT-BR onboarding, immediate language changes, persistence, scientific content, references and citations", async ({
  browser,
}) => {
  const context = await browser.newContext({
    locale: "pt-BR",
    viewport: { width: 1380, height: 900 },
    colorScheme: "dark",
    reducedMotion: "reduce",
  });
  const page = await context.newPage();
  const h = await harness(page);
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  mkdirSync("docs/screenshots", { recursive: true });
  try {
    await page.goto("/");
    await expect(page.locator(".splash")).toHaveCount(0);
    await expect(
      page.getByRole("heading", { name: "Escolha sua biblioteca de pesquisa" }),
    ).toBeVisible();
    const logo = page.locator(".onboarding-logo");
    await expect(logo).toBeVisible();
    const box = await logo.boundingBox();
    expect(box.width).toBeGreaterThan(120);
    expect(
      await logo.evaluate((img) => img.naturalWidth / img.naturalHeight),
    ).toBeCloseTo(box.width / box.height, 2);
    await page.screenshot({
      path: "docs/screenshots/onboarding-pt-BR-dark.png",
    });
    await page.getByRole("button", { name: /^Configurações/ }).click();
    await expect(page.getByLabel("Idioma", { exact: true })).toHaveValue(
      "system",
    );
    await page.getByLabel("Idioma", { exact: true }).selectOption("en");
    await expect(
      page.getByRole("heading", { name: "Settings", exact: true }),
    ).toBeVisible();
    await expect
      .poll(async () => (await h.rpc("snapshot")).settings.language)
      .toBe("en");
    await h.stop();
    h.start();
    await page.reload();
    await page.getByRole("button", { name: /^Settings/ }).click();
    await expect(page.getByLabel("Language", { exact: true })).toHaveValue(
      "en",
    );
    await page.getByLabel("Language", { exact: true }).selectOption("pt-BR");
    await expect(
      page.getByRole("heading", { name: "Configurações", exact: true }),
    ).toBeVisible();
    await page
      .getByRole("navigation", { name: "Navegação principal" })
      .getByRole("button", { name: "Início", exact: true })
      .click();
    await page
      .getByRole("button", { name: "Escolher pasta", exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name: /Biblioteca/ }),
    ).toBeVisible();
    await expect
      .poll(async () => (await h.rpc("snapshot")).stats.indexed)
      .toBe(2);
    h.seed();
    await page.reload();
    await page
      .getByRole("button", { name: /Synthetic viral evolution/ })
      .click();
    await expect(
      page.getByRole("heading", {
        name: "Synthetic viral evolution",
        exact: true,
      }),
    ).toBeVisible();
    await page.getByRole("tab", { name: "Conteúdo", exact: true }).click();
    await expect(
      page.getByRole("heading", { name: "Materials and Methods", exact: true }),
    ).toBeVisible();
    await expect(page.getByText("Métodos", { exact: true })).toBeVisible();
    await expect(
      page
        .getByText("Mapeamento de páginas indisponível", { exact: true })
        .first(),
    ).toBeVisible();
    await page
      .getByRole("button", { name: "Páginas 1–1", exact: true })
      .first()
      .click();
    await expect.poll(() => h.actions.some((a) => a.page === 1)).toBe(true);
    await page.getByRole("button", { name: "Páginas", exact: true }).click();
    await expect(page.locator(".extracted-text")).toContainText(
      "Evidence for viral evolution",
    );
    await page.getByRole("tab", { name: "Referências", exact: true }).click();
    await expect(page.locator(".reference-item")).toHaveCount(2);
    await expect(page.locator(".reference-item").first()).toContainText(
      "Synthetic surveillance study",
    );
    await expect(page.locator(".reference-item").first()).toContainText(
      "Na biblioteca",
    );
    await expect(page.locator(".reference-item").last()).toContainText(
      "Fora da biblioteca",
    );
    await page.getByRole("button", { name: "Ausentes", exact: true }).click();
    await expect(page.locator(".reference-item")).toHaveCount(1);
    await page.getByRole("button", { name: "Todas", exact: true }).click();
    await page.screenshot({
      path: "docs/screenshots/references-pt-BR-dark.png",
    });
    await page
      .getByRole("button", { name: "Abrir artigo", exact: true })
      .click();
    await expect(
      page.getByRole("heading", {
        name: "Synthetic surveillance study",
        exact: true,
      }),
    ).toBeVisible();
    await page
      .getByRole("button", { name: "Fechar detalhes do artigo", exact: true })
      .click();
    await page.getByRole("button", { name: "Explorar", exact: true }).click();
    await expect(page.locator(".graph-caption")).toContainText(
      "2 artigos · 1 conexão",
    );
    await expect(
      page.getByRole("checkbox", { name: "Citações", exact: true }),
    ).toBeChecked();
    await expect(
      page.getByRole("checkbox", { name: "Autores em comum", exact: true }),
    ).not.toBeChecked();
    await page.getByText("Inspecionar citações", { exact: true }).click();
    await page
      .locator(".graph-accessible button")
      .filter({ hasText: "Synthetic viral evolution" })
      .first()
      .click();
    await expect(
      page.getByRole("complementary", { name: "Metadados da citação" }),
    ).toContainText("Artigo de origem");
    await page.screenshot({
      path: "docs/screenshots/citations-pt-BR-dark.png",
    });
    await page
      .getByRole("button", { name: "Abrir artigo de origem", exact: true })
      .click();
    await expect(
      page.getByRole("heading", {
        name: "Synthetic viral evolution",
        exact: true,
      }),
    ).toBeVisible();
    await page
      .getByRole("button", { name: "Fechar detalhes do artigo", exact: true })
      .click();
    await page.getByRole("button", { name: /^Configurações/ }).click();
    await page.getByRole("button", { name: "Aparência", exact: true }).click();
    await page.getByRole("button", { name: "Claro", exact: true }).click();
    await expect(page.locator("body")).toHaveCSS(
      "background-color",
      "rgb(246, 247, 244)",
    );
    await page.getByRole("button", { name: "Sobre", exact: true }).click();
    await expect(page.locator(".about .petrus-logo")).toBeVisible();
    await expect(page.locator(".about")).toContainText(
      "Publication Evidence Tracking",
    );
    await page.screenshot({ path: "docs/screenshots/about-pt-BR-light.png" });
    const helpers = await page.evaluate(async () => {
      const m = await import("/src/i18n/index.ts");
      return {
        pt: m.detectLocale("pt-PT"),
        unknown: m.detectLocale("de-DE"),
        manual: m.preferredLocale("en", "pt-BR"),
        number: m.numberLabel(12345.67),
        missing: m.default.t("test.intentionallyMissingKey"),
      };
    });
    expect(helpers).toEqual({
      pt: "pt-BR",
      unknown: "en",
      manual: "en",
      number: "12.345,67",
      missing: "Texto indisponível",
    });
    expect(h.locales).toContain("en");
    expect(h.locales).toContain("pt-BR");
    expect(errors).toEqual([]);
  } finally {
    await h.stop();
    await context.close();
  }
});

test("translation catalogs cover UI copy and safe fallback", async () => {
  const en = JSON.parse(readFileSync("app/src/i18n/locales/en.json", "utf8")),
    pt = JSON.parse(readFileSync("app/src/i18n/locales/pt-BR.json", "utf8"));
  expect(Object.keys(pt).sort()).toEqual(Object.keys(en).sort());
  const files = [
    "app/src/App.tsx",
    "app/src/components/Settings.tsx",
    "app/src/components/PaperPanel.tsx",
    "app/src/components/Graph.tsx",
    "app/src/components/PetrusLogo.tsx",
  ];
  for (const file of files) {
    const source = ts.createSourceFile(
      file,
      readFileSync(file, "utf8"),
      ts.ScriptTarget.Latest,
      true,
      ts.ScriptKind.TSX,
    );
    const raw = [];
    const visit = (node) => {
      if (ts.isJsxText(node) && /[a-zA-ZÀ-ÿ]/.test(node.text.trim()))
        raw.push(node.text.trim());
      if (
        ts.isJsxAttribute(node) &&
        ["title", "aria-label", "placeholder", "alt"].includes(
          node.name.getText(source),
        ) &&
        node.initializer &&
        ts.isStringLiteral(node.initializer)
      )
        raw.push(node.initializer.text);
      ts.forEachChild(node, visit);
    };
    visit(source);
    expect(raw, file).toEqual([]);
  }
});
