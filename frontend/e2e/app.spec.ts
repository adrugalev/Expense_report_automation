import { expect, test } from "@playwright/test";

async function login(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await page.getByLabel("Email").fill("admin@example.com");
  await page.getByLabel("Пароль").fill("ChangeMe123!");
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(page.getByRole("heading", { name: "Обзор" })).toBeVisible();
}

test("user can sign in and navigate the workspace", async ({ page }) => {
  await login(page);
  const menuButton = page.getByRole("button", { name: "Открыть меню" });
  if (await menuButton.isVisible()) await menuButton.click();
  await page.getByRole("link", { name: "История", exact: true }).click();
  await expect(page.getByRole("heading", { name: "История", exact: true })).toBeVisible();
});

test("workspace layouts have no horizontal viewport overflow", async ({ page }, testInfo) => {
  await login(page);
  await page.screenshot({ path: testInfo.outputPath("dashboard.png"), fullPage: true });
  await page.goto("/reports/new");
  await expect(page.getByRole("heading", { name: "Новый отчёт" })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(1);
  await page.screenshot({ path: testInfo.outputPath("new-report.png"), fullPage: true });
});

test("user can generate a gift report from a manual receipt", async ({ page }) => {
  await login(page);
  await page.getByRole("link", { name: "Новый отчёт" }).first().click();
  await page.getByRole("button", { name: /Подарки/ }).click();
  await page.getByRole("button", { name: "Выберите сотрудника" }).click();
  await page.getByRole("button", { name: /Баранова Гиляна/ }).click();
  await page.getByRole("button", { name: "Добавить строку" }).click();
  await page.locator("tbody input").nth(4).fill("2500.00");
  await page.getByRole("button", { name: "Сформировать документы" }).click();
  await expect(page.getByRole("heading", { name: "Подарки" })).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText("Документы успешно сформированы")).toBeVisible();
  await expect(page.getByRole("link", { name: /Скачать/ })).toBeVisible();
});
