import { test, expect } from "@playwright/test";
import { writeFile } from "node:fs/promises";

test("founder and participant workflow, evidence output, theme and mobile navigation", async ({ page, context }, testInfo) => {
  const email = `founder-${Date.now()}@example.test`;
  const password = "independent-test-password";
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Sign in", exact: true })).toBeVisible();
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Invalid credentials" })).toBeVisible();
  await page.getByRole("button", { name: "New here? Create an account" }).click();
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("heading", { name: "Research overview" })).toBeVisible();
  await page.getByLabel("Theme").selectOption("dark");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.getByLabel("Theme").selectOption("system");
  await page.emulateMedia({ colorScheme: "light" });
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.getByLabel("Theme").selectOption("light");

  await page.getByRole("link", { name: "Projects", exact: true }).click();
  await page.getByLabel("Project name").fill("Mumbai snacks");
  await page.getByRole("button", { name: "Create project" }).click();
  await expect(page.getByRole("strong").filter({ hasText: /^Mumbai snacks$/ })).toBeVisible();

  await page.getByRole("link", { name: "Product studio" }).click();
  await page.getByLabel("Product name", { exact: true }).fill("Millet crisps");
  await page.getByLabel("Price (INR)", { exact: true }).fill("30");
  await page.getByLabel("Pack size (g)", { exact: true }).fill("50");
  await page.getByLabel("Include a competitor").check();
  const competitor = page.getByRole("group", { name: "Competitor" });
  await competitor.getByLabel("Product name").fill("Masala crackers");
  await competitor.getByLabel("Price (INR)").fill("35");
  await competitor.getByLabel("Pack size (g)").fill("50");
  await page.getByRole("button", { name: "Create product" }).click();
  await expect(page.getByText("Millet crisps", { exact: true })).toBeVisible();

  await page.getByRole("link", { name: "Consumer lab", exact: true }).click();
  await page.getByLabel("Study name").fill("Price study");
  await page.getByRole("button", { name: "Create study" }).click();
  await page.getByRole("button", { name: "Launch study" }).click();
  const invite = await page.getByRole("link", { name: "Open participant lab" }).getAttribute("href");
  const guest = await context.newPage();
  await guest.goto(invite!);
  await expect(guest.getByText("Sandbox session", { exact: false })).toBeVisible();
  await guest.getByLabel("I am 18 years or older").check();
  await guest.getByLabel("I understand the study").check();
  await guest.getByRole("button", { name: "Start tasks" }).click();
  for (let i = 1; i <= 6; i++) {
    await expect(guest.getByRole("heading", { name: "Choice task " + i })).toBeVisible();
    await guest.getByRole("button", { name: "I would buy neither" }).click();
  }
  await expect(guest.getByRole("heading", { name: "Study complete" })).toBeVisible();
  guest.once("dialog", (dialog) => dialog.accept());
  await guest.getByRole("button", { name: "Withdraw and delete my responses" }).click();
  await expect(guest.getByRole("heading", { name: "Your responses were deleted" })).toBeVisible();
  await guest.close();

  await page.getByRole("button", { name: "Generate synthetic panel" }).click();
  await expect(page.getByText("540 choices")).toBeVisible();
  await page.getByRole("button", { name: "Train choice model" }).click();
  await expect(page.getByText("Latest model", { exact: false })).toContainText("ready", { timeout: 20000 });
  await page.getByRole("button", { name: "Rank candidates" }).click();
  await expect(page.getByText("Recommended task", { exact: false })).toBeVisible();
  await page.getByRole("link", { name: "Market twin", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Preference coefficients" })).toBeVisible();
  await page.getByRole("link", { name: "Simulator", exact: true }).click();
  await page.getByLabel("Compare prices").fill("20, 30, 40");
  await page.getByRole("button", { name: "Run simulation" }).click();
  await expect(page.getByRole("heading", { name: "Price comparison" })).toBeVisible();
  await expect(page.getByText("Synthetic choice evidence.", { exact: false })).toBeVisible();
  await page.getByRole("link", { name: "Reports", exact: true }).click();
  await page.getByRole("button", { name: "Generate report" }).click();
  const href = await page.getByRole("link", { name: "PDF", exact: true }).getAttribute("href");
  const pdf = await page.request.get(href!);
  expect(pdf.headers()["content-type"]).toBe("application/pdf");
  const pdfBytes = await pdf.body();
  expect(pdfBytes.subarray(0, 4).toString()).toBe("%PDF");
  await writeFile(testInfo.outputPath("scenario-report.pdf"), pdfBytes);

  await page.screenshot({ path: testInfo.outputPath("report-library.png"), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Open navigation" }).click();
  await page.getByRole("link", { name: "Overview", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Research overview" })).toBeVisible();
  await expect(page.getByText("90 sandbox sessions separately")).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("mobile-overview.png"), fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390);
});

test("demo, packaging upload, collaborators and adaptive participant assignment", async ({ page, browser }) => {
  const email = `ready-${Date.now()}@example.test`;
  await page.goto("/");
  await page.getByRole("button", { name: "New here? Create an account" }).click();
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("test-password-for-ready-workspace");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("heading", { name: "Research overview" })).toBeVisible();
  await page.getByRole("button", { name: "Prepare demo workspace" }).click();
  await expect(page.getByText("90 sandbox sessions separately")).toBeVisible({ timeout: 60000 });
  await page.getByRole("button", { name: "Prepare demo workspace" }).click();
  await expect(page.getByText("90 sandbox sessions separately")).toBeVisible();

  const teammate = await browser.newContext();
  const registration = await teammate.request.post("http://127.0.0.1:3009/api/v1/auth/register", {
    data: { email: "editor-" + email, password: "test-password-for-ready-workspace" },
  });
  expect(registration.status()).toBe(201);
  await page.getByRole("link", { name: "Projects", exact: true }).click();
  await page.getByLabel("Collaborator email").fill("editor-" + email);
  await page.getByRole("button", { name: "Add editor" }).click();
  await expect(page.getByText("editor-" + email, { exact: true })).toBeVisible();
  const shared = await teammate.request.get("http://127.0.0.1:3009/api/v1/projects");
  expect((await shared.json())[0].is_owner).toBe(false);
  await teammate.close();

  await page.getByRole("link", { name: "Product studio" }).click();
  await page.getByText("Packaging image", { exact: true }).click();
  const imageData = await page.evaluate(() => {
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = 32;
    const painter = canvas.getContext("2d")!;
    painter.fillStyle = "#238060"; painter.fillRect(0, 0, 32, 32);
    return canvas.toDataURL("image/png").split(",")[1];
  });
  await page.getByLabel("Upload packaging for Millet crisps").setInputFiles({
    name: "packaging.png", mimeType: "image/png",
    buffer: Buffer.from(imageData, "base64"),
  });
  await expect(page.getByAltText("Millet crisps packaging")).toBeVisible();
  await page.getByRole("link", { name: "Consumer lab", exact: true }).click();
  await page.getByLabel("Study name").fill("Adaptive task budget");
  await page.getByLabel("Assignment policy").selectOption("adaptive");
  await page.getByLabel("Maximum tasks per participant").fill("3");
  await page.getByRole("button", { name: "Create study" }).click();
  await expect(page.getByText("adaptive · up to 3 tasks per session")).toBeVisible();
  await page.getByRole("button", { name: "Launch study" }).click();
  const invite = await page.getByRole("link", { name: "Open participant lab" }).getAttribute("href");
  const guest = await browser.newContext();
  const participant = await guest.newPage();
  await participant.goto("http://127.0.0.1:3009" + invite);
  await participant.getByLabel("I am 18 years or older").check();
  await participant.getByLabel("I understand the study").check();
  await participant.getByRole("button", { name: "Start tasks" }).click();
  for (let task = 1; task <= 3; task++) {
    await expect(participant.getByRole("heading", { name: "Choice task " + task })).toBeVisible();
    await participant.getByRole("button", { name: "I would buy neither" }).click();
  }
  await expect(participant.getByRole("heading", { name: "Study complete" })).toBeVisible();
  await guest.close();
  await page.getByRole("button", { name: /^Notifications/ }).click();
  await expect(page.getByRole("region", { name: "Notification list" })).toBeVisible();
});
