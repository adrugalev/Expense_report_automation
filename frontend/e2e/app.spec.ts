import { expect, test } from "@playwright/test";

async function login(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(process.env.PLAYWRIGHT_ADMIN_EMAIL ?? "aleksandr.drugalev@h-xgroup.com");
  await page.getByLabel("Пароль").fill(process.env.PLAYWRIGHT_ADMIN_PASSWORD ?? "ChangeMe123!");
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(page.getByRole("heading", { name: "Новый отчёт" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Обзор" })).toHaveCount(0);
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
  await page.goto("/");
  await expect(page).toHaveURL(/\/reports\/new$/);
  const receiptTable = page.getByTestId("receipt-table");
  expect(await receiptTable.evaluate((element) => element.scrollWidth <= element.clientWidth + 1)).toBe(true);
  await page.getByRole("button", { name: "Добавить строку" }).click();
  expect(await receiptTable.evaluate((element) => element.scrollWidth <= element.clientWidth + 1)).toBe(true);
  const menuButton = page.getByRole("button", { name: "Открыть меню" });
  if (await menuButton.isVisible()) await menuButton.click();
  const brand = page.locator("aside:visible").getByText("Автоматизация", { exact: true });
  await expect(brand).toBeVisible();
  expect(await brand.evaluate((element) => element.scrollWidth <= element.clientWidth + 1)).toBe(true);
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
  await expect(page.getByRole("link", { name: "Настройки", exact: true })).toHaveCount(0);
  await page.getByRole("link", { name: "Сотрудники", exact: true }).click();
  const main = page.getByRole("main");
  await expect(main.getByRole("heading", { name: "Сотрудники", exact: true })).toBeVisible();
  const adminRow = main.locator("tbody tr").filter({ hasText: "Другалев Александр Александрович" });
  await expect(adminRow.getByText("Другалев Александр Александрович", { exact: true })).toBeVisible();
  await expect(adminRow.getByText("aleksandr.drugalev@h-xgroup.com", { exact: true })).toBeVisible();
  const ownPasswordButton = adminRow.getByRole("button", { name: "Изменить свой пароль", exact: true });
  await expect(ownPasswordButton).toBeEnabled();
  await ownPasswordButton.click();
  await expect(page.getByRole("dialog").getByRole("heading", { name: "Изменить свой пароль" })).toBeVisible();
  await expect(page.getByLabel("Текущий пароль")).toBeVisible();
  await expect(page.getByLabel("Новый пароль", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Повторите новый пароль")).toBeVisible();
});

test("representative suggestions rotate counterparties and their participants", async ({ page }) => {
  const email = process.env.PLAYWRIGHT_EMPLOYEE_EMAIL;
  const password = process.env.PLAYWRIGHT_EMPLOYEE_PASSWORD;
  test.skip(!email || !password, "Employee credentials are required for this deployment smoke");

  await page.goto("/login");
  await page.getByLabel("Email").fill(email!);
  await page.getByLabel("Пароль").fill(password!);
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(page.getByRole("heading", { name: "Новый отчёт" })).toBeVisible();
  await expect(page.getByRole("img", { name: "Huaxun" })).toBeVisible();
  await page.getByRole("button", { name: /Представительские расходы/ }).click();

  const selfParticipant = page.getByLabel(/Баранова Гиляна Басанговна/);
  await expect(selfParticipant).toBeChecked();
  await selfParticipant.uncheck();
  await expect(selfParticipant).not.toBeChecked();

  const counterparty = page.getByLabel("Контрагент / организация");
  const participants = page.getByLabel("Участники со стороны контрагента");
  const purpose = page.getByLabel("Цель встречи");
  const result = page.getByLabel("Результат встречи");
  const suggest = page.getByRole("button", { name: "Я — Джон Сноу" });

  await expect(purpose).toHaveValue("");
  await expect(result).toHaveValue("");
  await suggest.hover();
  await expect(page.getByRole("tooltip")).toHaveText(
    "Автоматически подставляет контрагента, участников с его стороны, цель и результат встречи, когда вы не знаете, что указать. You know nothing, John Snow.",
  );
  await suggest.click();
  await expect(counterparty).not.toHaveValue("");
  await expect(participants).not.toHaveValue("");
  await expect(purpose).not.toHaveValue("");
  await expect(result).not.toHaveValue("");
  const firstCounterparty = await counterparty.inputValue();
  const firstParticipants = await participants.inputValue();
  const firstPurpose = await purpose.inputValue();
  const firstResult = await result.inputValue();
  expect(await purpose.evaluate((element) => element.scrollHeight <= element.clientHeight + 1)).toBe(true);
  expect(await result.evaluate((element) => element.scrollHeight <= element.clientHeight + 1)).toBe(true);

  await suggest.click();
  await expect(counterparty).not.toHaveValue(firstCounterparty);
  await expect(participants).not.toHaveValue(firstParticipants);
  await expect(purpose).not.toHaveValue(firstPurpose);
  await expect(result).not.toHaveValue(firstResult);
  expect(await purpose.evaluate((element) => element.scrollHeight <= element.clientHeight + 1)).toBe(true);
  expect(await result.evaluate((element) => element.scrollHeight <= element.clientHeight + 1)).toBe(true);
});

test("selected employee is added to company participants and can be unchecked", async ({ page }) => {
  await login(page);
  await page.getByRole("button", { name: /Представительские расходы/ }).click();
  await expect(page.getByRole("button", { name: /Другалев Александр Александрович/ })).toBeVisible();
  await page.getByRole("button", { name: /Другалев Александр Александрович/ }).click();
  await page.getByRole("button", { name: /Баранова Гиляна Басанговна/ }).click();

  const participant = page.getByLabel(/Баранова Гиляна Басанговна/);
  await expect(participant).toBeChecked();
  await participant.uncheck();
  await expect(participant).not.toBeChecked();
});

test("workspace layouts have no horizontal viewport overflow", async ({ page }, testInfo) => {
  await login(page);
  await page.screenshot({ path: testInfo.outputPath("new-report-home.png"), fullPage: true });
  await expect(page.getByRole("heading", { name: "Новый отчёт" })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(1);
  await page.screenshot({ path: testInfo.outputPath("new-report.png"), fullPage: true });
});

test("user can generate a gift report from a manual receipt", async ({ page }) => {
  await login(page);
  await page.getByRole("link", { name: "Новый отчёт" }).first().click();
  await page.getByRole("button", { name: /Подарки/ }).click();
  await page.getByRole("button", { name: /Другалев Александр Александрович/ }).click();
  await page.getByRole("button", { name: /Баранова Гиляна/ }).click();
  await page.getByRole("button", { name: "Добавить строку" }).click();
  await page.locator("tbody input").nth(4).fill("2500.00");
  await page.getByRole("button", { name: "Сформировать документы" }).click();
  await expect(page.getByRole("heading", { name: "Подарки" })).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText("Документы успешно сформированы")).toBeVisible();
  await expect(page.getByRole("link", { name: /Скачать/ })).toBeVisible();
});
