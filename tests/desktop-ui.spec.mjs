// Real Python engine + synthetic fixture PDFs. Only the native IPC/dialog/OS boundary is substituted.
import { test, expect } from "@playwright/test";
import { spawn } from "node:child_process";
import { createInterface } from "node:readline";
import { mkdtempSync, cpSync, mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { resolve } from "node:path";

test("onboarding, ingestion, search, paper details, collections, graph, sessions and persistence", async ({
  page,
}) => {
  const root = process.cwd();
  const temp = mkdtempSync(resolve(tmpdir(), "petrus-ui-"));
  const library = resolve(temp, "Fixture library ü");
  cpSync(resolve(root, "engine/tests/fixtures"), library, { recursive: true });
  let child;
  let sequence = 0;
  const pending = new Map();
  const start = () => {
    child = spawn(
      resolve(root, ".venv/bin/python"),
      ["-m", "petrus_engine", "--data-dir", resolve(temp, "data")],
      { cwd: root },
    );
    createInterface({ input: child.stdout }).on("line", (line) => {
      const message = JSON.parse(line);
      const item = pending.get(message.id);
      pending.delete(message.id);
      if (message.error) item.reject(new Error(message.error));
      else item.resolve(message.result);
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
  const actions = [];
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  start();
  await page.exposeFunction("petrusTestIPC", async (command, args) => {
    if (command === "engine_call") return await rpc(args.method, args.params);
    if (command === "set_menu_language") return null;
    if (command === "plugin:dialog|open") return library;
    if (command === "paper_action") {
      actions.push(args);
      return null;
    }
    if (command.startsWith("plugin:event|")) return 1;
    throw new Error(`Unexpected native command: ${command}`);
  });
  await page.addInitScript(() => {
    window.isTauri = true;
    window.__TAURI_INTERNALS__ = {
      invoke: (cmd, args) => window.petrusTestIPC(cmd, args),
      transformCallback: () => 1,
      unregisterCallback: () => undefined,
    };
    window.__TAURI_EVENT_PLUGIN_INTERNALS__ = {
      unregisterListener: () => undefined,
    };
  });
  mkdirSync(resolve(root, "docs/screenshots"), { recursive: true });
  try {
    await page.emulateMedia({ colorScheme: "dark", reducedMotion: "reduce" });
    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: "Choose your research library" }),
    ).toBeVisible();
    await rpc("save_settings", { theme: "dark" });
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark", {
      timeout: 5000,
    });
    await page.screenshot({ path: "docs/screenshots/onboarding-dark.png" });
    await page.getByRole("button", { name: "Choose folder" }).click();
    await expect(
      page.getByRole("button", { name: /Synthetic viral evolution/ }),
    ).toBeVisible({ timeout: 15000 });
    await expect(
      page.getByRole("button", { name: /Synthetic surveillance study/ }),
    ).toBeVisible();
    await expect
      .poll(async () => (await rpc("snapshot")).stats.indexed)
      .toBe(2);
    await page.getByLabel("Search your library").fill("surveillance");
    await expect(
      page.getByRole("button", { name: /Synthetic viral evolution/ }),
    ).toHaveCount(0);
    await expect(
      page.getByRole("button", { name: /Synthetic surveillance study/ }),
    ).toBeVisible();
    await page.getByLabel("Clear search").click();
    await page
      .getByRole("button", { name: /Synthetic viral evolution/ })
      .click();
    await expect(
      page.getByRole("heading", { name: "Synthetic viral evolution" }),
    ).toBeVisible();
    await expect(
      page.getByRole("definition").filter({ hasText: "10.1234/petrus.test" }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Open PDF", exact: true }).click();
    await page
      .getByRole("button", { name: "Reveal file", exact: true })
      .click();
    expect(actions.map((a) => a.action)).toEqual(["open", "reveal"]);
    await page.getByRole("tab", { name: "Content", exact: true }).click();
    await page.getByRole("button", { name: "Pages", exact: true }).click();
    await expect(page.locator(".extracted-text")).toContainText(
      "Evidence for viral evolution",
    );
    await page.getByRole("tab", { name: "Notes", exact: true }).click();
    await page
      .getByLabel("Paper notes")
      .fill("A test observation with a local provenance trail.");
    await page.getByRole("button", { name: "Save notes" }).click();
    await expect(
      page.getByRole("button", { name: "Saved locally" }),
    ).toBeVisible();
    await page.getByLabel("Close paper details").click();
    await page
      .getByRole("button", { name: "New collection", exact: true })
      .click();
    await page.getByLabel("Collection name").fill("Viral evolution");
    await page
      .getByRole("button", { name: "Create collection", exact: true })
      .click();
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await page
      .getByRole("button", { name: /Synthetic viral evolution/ })
      .click();
    await page
      .getByRole("checkbox", { name: "Viral evolution", exact: true })
      .check();
    await page.getByLabel("Close paper details").click();
    await expect(page.locator(".collection-chip")).toContainText(
      "Viral evolution",
    );
    await page.screenshot({ path: "docs/screenshots/library-dark.png" });
    await page
      .getByRole("navigation", { name: "Main navigation" })
      .getByRole("button", { name: "Explore", exact: true })
      .click();
    await expect(page.locator(".graph-caption")).toContainText(
      "2 papers · 0 connections",
    );
    await page
      .getByRole("checkbox", { name: "Shared authors", exact: true })
      .check();
    await expect(page.locator(".graph-caption")).toContainText(
      "2 papers · 1 connection",
    );
    await expect(page.locator(".graph-canvas canvas").first()).toBeVisible();
    await page.screenshot({ path: "docs/screenshots/explore-dark.png" });
    await page.getByRole("button", { name: "Research", exact: true }).click();
    await page.getByRole("button", { name: "New Research Session" }).click();
    await page.getByLabel("Title", { exact: true }).fill("Surveillance review");
    await page
      .getByLabel("Research question")
      .fill("What does the local evidence say?");
    await page
      .getByLabel("Description")
      .fill("A synthetic UI validation session.");
    await page
      .getByRole("button", { name: "Create session", exact: true })
      .click();
    const evidenceSessionId = (await rpc("snapshot")).sessions[0].id;
    const fixtureEvidence = (
      await rpc("research_evidence_save", {
        session_id: evidenceSessionId,
        unit_id: "chunk:1",
      })
    ).item;
    await rpc("research_evidence_update", {
      id: fixtureEvidence.id,
      decision: "included",
      user_note: "Synthetic fixture note — persistence only.",
    });
    await page.getByRole("button", { name: /Surveillance review/ }).click();
    await expect(
      page.getByText("What does the local evidence say?", { exact: true }),
    ).toBeVisible();
    await page.getByRole("button", { name: /^Settings/ }).click();
    await page.getByRole("button", { name: "Appearance", exact: true }).click();
    await page.getByRole("button", { name: "Light", exact: true }).click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
    await expect(page.locator("body")).toHaveCSS(
      "background-color",
      "rgb(246, 247, 244)",
    );
    await page.getByRole("button", { name: "Home", exact: true }).click();
    await expect(
      page
        .getByRole("navigation", { name: "Main navigation" })
        .getByRole("button", { name: "Home", exact: true }),
    ).toHaveClass(/active/);
    await page.screenshot({ path: "docs/screenshots/home-light.png" });
    await stop();
    start();
    await page.reload();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
    await page
      .getByRole("button", { name: /^Library/ })
      .first()
      .click();
    await expect(
      page.getByRole("button", { name: /Synthetic viral evolution/ }),
    ).toBeVisible();
    await page
      .getByRole("button", { name: /Synthetic viral evolution/ })
      .click();
    await page.getByRole("tab", { name: "Notes", exact: true }).click();
    await expect(page.getByLabel("Paper notes")).toHaveValue(
      "A test observation with a local provenance trail.",
    );
    const reopenedEvidence = await rpc("research_evidence_get", {
      id: fixtureEvidence.id,
    });
    expect(reopenedEvidence).toMatchObject({
      text_snapshot: fixtureEvidence.text_snapshot,
      text_sha256: fixtureEvidence.text_sha256,
      evidence_fingerprint: fixtureEvidence.evidence_fingerprint,
      decision: "included",
      user_note: "Synthetic fixture note — persistence only.",
    });
    await page.getByRole("button", { name: "Research", exact: true }).click();
    await page.getByRole("button", { name: /Surveillance review/ }).click();
    await expect(page.locator(".saved-evidence-card")).toHaveCount(1);
    await expect(
      page.getByRole("textbox", { name: "Research note", exact: true }),
    ).toHaveValue("Synthetic fixture note — persistence only.");
    await page.getByRole("tab", { name: "Findings", exact: true }).click();
    await page.getByRole("button", { name: "New claim", exact: true }).click();
    await page
      .getByLabel("Scientific statement", { exact: true })
      .fill("  Preliminary SYNTHETIC TEST hypothesis.  ");
    await page
      .getByLabel("Researcher note", { exact: true })
      .fill("  Synthetic fixture note\n  preserved  ");
    await page.getByRole("button", { name: "Save claim", exact: true }).click();
    const claimPanel = page.locator(".claim-detail");
    await expect(claimPanel.locator(".claim-statement")).toHaveText(
      "  Preliminary SYNTHETIC TEST hypothesis.  ",
    );
    await claimPanel
      .getByRole("button", { name: "Add evidence", exact: true })
      .click();
    const picker = page.locator(".claim-evidence-picker");
    await picker.locator("input[type=radio]").check();
    await picker.getByRole("combobox").selectOption("supports");
    await picker
      .getByRole("button", { name: "Link evidence", exact: true })
      .click();
    await expect(claimPanel.locator(".claim-link")).toHaveCount(1);
    await claimPanel
      .getByRole("button", { name: "Mark reviewed", exact: true })
      .click();
    await expect(claimPanel.locator("h3")).toContainText(
      "Reviewed by researcher",
    );
    const claimId = (
      await rpc("research_claim_list", { session_id: evidenceSessionId })
    ).items[0].id;
    const claimBefore = await rpc("research_claim_get", { id: claimId });
    const trailBefore = await rpc("research_trail_list", {
      session_id: evidenceSessionId,
    });
    await stop();
    start();
    await page.reload();
    await page.getByRole("button", { name: "Research", exact: true }).click();
    await page.getByRole("button", { name: /Surveillance review/ }).click();
    await page.getByRole("tab", { name: "Findings", exact: true }).click();
    await page.locator(".claim-card").click();
    await expect(claimPanel.locator(".research-human-note pre")).toHaveText(
      "  Synthetic fixture note\n  preserved  ",
    );
    expect(await rpc("research_claim_get", { id: claimId })).toEqual(
      claimBefore,
    );
    expect(
      await rpc("research_trail_list", { session_id: evidenceSessionId }),
    ).toEqual(trailBefore);
    await page
      .getByRole("tab", { name: "Research Trail", exact: true })
      .click();
    await expect(
      page
        .locator(".research-trail-entry")
        .filter({ hasText: "Claim created" }),
    ).toHaveCount(1);
    expect((await rpc("snapshot")).sessions).toHaveLength(1);
    expect(errors).toEqual([]);
  } finally {
    await stop();
  }
});
