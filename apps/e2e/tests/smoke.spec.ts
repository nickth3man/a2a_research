import { test, expect } from "../fixtures/observability";

test("home page renders query form and how-it-works", async ({ page, obs }) => {
  await page.goto("/");

  await expect(page.getByLabel("Research query")).toBeVisible();
  await expect(page.getByRole("button", { name: /run pipeline/i })).toBeVisible();
  await expect(page.getByText(/how it works/i)).toBeVisible();

  expect(obs.pageErrors, "no uncaught page errors on initial render").toEqual([]);
});

test("api health endpoint responds", async ({ request }) => {
  const apiUrl = process.env.E2E_API_URL ?? "http://localhost:8000";
  const res = await request.get(`${apiUrl}/api/health`);
  expect(res.ok()).toBeTruthy();
  expect(await res.json()).toMatchObject({ status: "ok" });
});
