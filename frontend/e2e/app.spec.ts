import { expect, test } from "@playwright/test";

async function login(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(process.env.PLAYWRIGHT_ADMIN_EMAIL ?? "aleksandr.drugalev@h-xgroup.com");
  await page.getByLabel("Пароль").fill(process.env.PLAYWRIGHT_ADMIN_PASSWORD ?? "ChangeMe123!");
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(page.getByRole("heading", { name: "Обзор" })).toBeVisible();
}

test("employee can open only the report form for their own employee record", async ({ page }) => {
  const email = process.env.PLAYWRIGHT_EMPLOYEE_EMAIL;
  const password = process.env.PLAYWRIGHT_EMPLOYEE_PASSWORD;
  test.skip(!email || !password, "Employee credentials are required for this deployment smoke");

  await page.goto("/login");
  await page.getByLabel("Email").fill(email!);
  await page.getByLabel("Пароль").fill(password!);
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(page.getByRole("heading", { name: "Новый отчёт" })).toBeVisible();
  const menuButton = page.getByRole("button", { name: "Открыть меню" });
  if (await menuButton.isVisible()) await menuButton.click();
  await expect(page.getByRole("link", { name: "Новый отчёт" })).toBeVisible();
  await expect(page.getByRole("link", { name: "История" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Обзор" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Выберите сотрудника" })).toHaveCount(0);

  await page.goto("/reports/history");
  await expect(page).toHaveURL(/\/reports\/new$/);
  await expect(page.getByRole("heading", { name: "Новый отчёт" })).toBeVisible();
});

test("user can sign in and navigate the workspace", async ({ page }) => {
  await login(page);
  const menuButton = page.getByRole("button", { name: "Открыть меню" });
  if (await menuButton.isVisible()) await menuButton.click();
  await page.getByRole("link", { name: "История", exact: true }).click();
  await expect(page.getByRole("heading", { name: "История", exact: true })).toBeVisible();
});

test("admin account is linked to Drugalev and protected from employee password changes", async ({ page }) => {
  await login(page);
  const menuButton = page.getByRole("button", { name: "Открыть меню" });
  if (await menuButton.isVisible()) await menuButton.click();
  await page.getByRole("link", { name: "Настройки", exact: true }).click();
  const main = page.getByRole("main");
  await expect(main.getByText("Другалев Александр Александрович", { exact: true })).toBeVisible();
  await expect(main.getByText(/aleksandr\.drugalev@h-xgroup\.com.*администратор/)).toBeVisible();
  const ownPasswordButton = main.getByRole("button", { name: "Изменить свой пароль", exact: true });
  await expect(ownPasswordButton).toBeEnabled();
  await ownPasswordButton.click();
  await expect(page.getByRole("dialog").getByRole("heading", { name: "Изменить свой пароль" })).toBeVisible();
  await expect(page.getByLabel("Текущий пароль")).toBeVisible();
  await expect(page.getByLabel("Новый пароль", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Повторите новый пароль")).toBeVisible();
});

test("representative suggestions rotate counterparties and their participants", async ({ page }) => {
  await login(page);
  await page.getByRole("link", { name: "Новый отчёт" }).first().click();
  await page.getByRole("button", { name: /Представительские расходы/ }).click();

  const counterparty = page.getByLabel("Контрагент / организация");
  const participants = page.getByLabel("Участники со стороны контрагента");
  const suggest = page.getByRole("button", { name: "Дополнить пустые поля" });

  await suggest.click();
  await expect(counterparty).not.toHaveValue("");
  await expect(participants).not.toHaveValue("");
  const firstCounterparty = await counterparty.inputValue();
  const firstParticipants = await participants.inputValue();

  await suggest.click();
  await expect(counterparty).not.toHaveValue(firstCounterparty);
  await expect(participants).not.toHaveValue(firstParticipants);
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
