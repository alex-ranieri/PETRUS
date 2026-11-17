import { test, expect } from "@playwright/test";
import { setup } from "./claims-fixture.mjs";
for (const locale of ["en", "pt-BR"]) {
  test(`human findings lifecycle, navigation, source removal and Trail ${locale}`, async ({
    browser,
  }) => {
    const { page, context, state, en, ask, research } = await setup(
      browser,
      locale,
    );
    await ask();
    await page
      .locator("#evidence-E6")
      .getByRole("button", {
        name: en ? "Save evidence" : "Salvar evidência",
        exact: true,
      })
      .click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("combobox").selectOption("1");
    await dialog
      .getByRole("button", { name: en ? "Save" : "Salvar", exact: true })
      .click();
    await page
      .locator("#evidence-E2")
      .getByRole("button", {
        name: en ? "Save evidence" : "Salvar evidência",
        exact: true,
      })
      .click();
    await expect.poll(() => state.items.length).toBe(2);
    await research();
    const findings = () =>
      page.getByRole("tab", { name: en ? "Findings" : "Achados", exact: true });
    await findings().click();
    await expect(page.locator(".findings-workspace")).toContainText(
      en ? "No claims yet" : "Nenhuma afirmação criada",
    );
    await page
      .getByRole("button", {
        name: en ? "New claim" : "Nova afirmação",
        exact: true,
      })
      .click();
    const initial = "  Preliminary TEST hypothesis ç\n  exact  ";
    const revised = "  Revised TEST hypothesis ç\n  exact  ";
    const note = "  Researcher note ç\n  exact  ";
    await page
      .getByLabel(en ? "Scientific statement" : "Afirmação científica", {
        exact: true,
      })
      .fill(initial);
    await page
      .getByRole("button", {
        name: en ? "Save claim" : "Salvar afirmação",
        exact: true,
      })
      .click();
    const detail = page.locator(".claim-detail");
    await expect(detail).toContainText(initial);
    const review = () =>
      detail.getByRole("button", {
        name: en ? "Mark reviewed" : "Marcar como revisada",
        exact: true,
      });
    await expect(review()).toBeDisabled();
    const add = async (index, relation) => {
      await detail
        .getByRole("button", {
          name: en ? "Add evidence" : "Adicionar evidência",
          exact: true,
        })
        .click();
      const picker = page.locator(".claim-evidence-picker");
      await picker.locator("input[type=radio]").nth(index).check();
      await picker.getByRole("combobox").selectOption(relation);
      await picker
        .getByRole("button", {
          name: en ? "Link evidence" : "Vincular evidência",
          exact: true,
        })
        .click();
    };
    await add(0, "supports");
    await expect(detail.locator(".claim-link")).toHaveCount(1);
    await expect(detail.locator(".claim-link")).toContainText(
      en ? "Uncertain" : "Incertas",
    );
    await detail.locator(".claim-link select").selectOption("contradicts");
    await expect(detail.locator(".claim-link h4")).toContainText(
      en ? "Contradicts" : "Contradiz",
    );
    await add(0, "context");
    await expect(detail.locator(".claim-link")).toHaveCount(2);
    await review().click();
    await expect(detail.locator("h3")).toContainText(
      en ? "Reviewed by researcher" : "Revisada pelo pesquisador",
    );
    await detail
      .getByRole("button", {
        name: en ? "Edit claim" : "Editar afirmação",
        exact: true,
      })
      .click();
    await page
      .getByLabel(en ? "Scientific statement" : "Afirmação científica", {
        exact: true,
      })
      .fill(revised);
    await page
      .getByLabel(en ? "Researcher note" : "Nota do pesquisador", {
        exact: true,
      })
      .fill(note);
    await page
      .getByRole("button", {
        name: en ? "Save claim" : "Salvar afirmação",
        exact: true,
      })
      .click();
    await expect(detail.locator(".claim-statement")).toHaveText(revised);
    await expect(detail.locator(".research-human-note pre")).toHaveText(note);
    await detail
      .getByRole("button", {
        name: en ? "Return to draft" : "Voltar a rascunho",
        exact: true,
      })
      .click();
    await review().click();
    await detail
      .locator(".claim-link")
      .first()
      .getByRole("button", { name: en ? "Open PDF" : "Abrir PDF", exact: true })
      .click();
    expect(state.actions.at(-1)).toMatchObject({
      id: 2,
      action: "open",
      page: 2,
    });
    await detail
      .locator(".claim-link")
      .first()
      .getByRole("button", {
        name: en ? "View paper" : "Ver artigo",
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
    await detail
      .locator(".claim-link")
      .first()
      .getByRole("button", {
        name: en ? "View evidence" : "Ver evidência",
        exact: true,
      })
      .click();
    await expect(page.locator("#research-evidence-1")).toBeFocused();
    await page
      .locator("#research-evidence-1 .evidence-related-claims button")
      .click();
    await expect(detail.locator(".claim-statement")).toHaveText(revised);
    await detail
      .getByRole("button", {
        name: en ? "Archive claim" : "Arquivar afirmação",
        exact: true,
      })
      .click();
    await expect(page.locator(".claim-card")).toHaveCount(0);
    await page
      .getByRole("group", { name: en ? "Filter claims" : "Filtrar afirmações" })
      .getByRole("button", { name: en ? /^Archived/ : /^Arquivadas/ })
      .click();
    await expect(page.locator(".claim-card")).toHaveCount(1);
    await detail
      .getByRole("button", {
        name: en ? "Restore claim" : "Restaurar afirmação",
        exact: true,
      })
      .click();
    await page
      .getByRole("group", { name: en ? "Filter claims" : "Filtrar afirmações" })
      .getByRole("button", { name: en ? /^All/ : /^Todas/ })
      .click();
    await expect(page.locator(".claim-card")).toHaveCount(1);
    await detail
      .locator(".claim-link")
      .last()
      .getByRole("button", {
        name: en ? "Unlink evidence" : "Desvincular evidência",
        exact: true,
      })
      .click();
    await expect(detail.locator(".claim-link")).toHaveCount(1);
    state.unavailable = true;
    await page.reload();
    await research();
    await findings().click();
    await page.locator(".claim-card").click();
    await expect(detail).toContainText(
      en ? "Source currently unavailable" : "Fonte indisponível no momento",
    );
    await expect(detail.locator(".claim-statement")).toHaveText(revised);
    await expect(detail.locator(".research-human-note pre")).toHaveText(note);
    await detail
      .locator(".claim-link")
      .getByRole("button", {
        name: en ? "View evidence" : "Ver evidência",
        exact: true,
      })
      .click();
    await page
      .locator("#research-evidence-1")
      .getByRole("button", {
        name: en ? "Remove evidence" : "Remover evidência",
        exact: true,
      })
      .click();
    await findings().click();
    await page.locator(".claim-card").click();
    await expect(detail).toContainText(
      en ? "Source removed" : "Fonte removida",
    );
    await detail.locator(".claim-source-snapshot summary").click();
    await expect(
      detail.locator(".claim-source-snapshot blockquote"),
    ).toHaveText("Exact source ç\n  second line");
    await page.screenshot({
      path: test.info().outputPath("claim-removed.png"),
      fullPage: true,
    });
    await page
      .getByRole("tab", {
        name: en ? "Research Trail" : "Trilha de pesquisa",
        exact: true,
      })
      .click();
    await expect(page.locator(".research-trail-entry")).toHaveCount(
      state.events.length,
    );
    expect(
      state.events
        .filter((e) => e.event_type.startsWith("claim_"))
        .every((e) => e.actor_type === "user"),
    ).toBeTruthy();
    await page
      .locator(".research-trail-entry")
      .filter({ hasText: en ? "Statement revised" : "Afirmação revisada" })
      .locator("summary")
      .click();
    await expect(page.locator(".trail-details .claim-statement")).toHaveText(
      revised,
    );
    const statusFilter = page.getByRole("tab", {
      name: en ? "Findings" : "Achados",
      exact: true,
    });
    await statusFilter.click();
    await page
      .getByRole("group", { name: en ? "Filter claims" : "Filtrar afirmações" })
      .getByRole("button", { name: en ? /^Draft/ : /^Rascunho/ })
      .click();
    await expect(page.locator(".claim-card")).toHaveCount(0);
    await page
      .getByRole("group", { name: en ? "Filter claims" : "Filtrar afirmações" })
      .getByRole("button", {
        name: en ? /^Reviewed by researcher/ : /^Revisada pelo pesquisador/,
      })
      .click();
    await expect(page.locator(".claim-card")).toHaveCount(1);
    expect(state.calls.filter((c) => c.method === "ask")).toHaveLength(1);
    await context.close();
  });
}
