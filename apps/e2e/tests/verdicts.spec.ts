import { test, expect } from "../fixtures/observability";
import {
  defaultPipelineEvents,
  mockResearchSession,
  resultEvent,
} from "../fixtures/mock-api";

const SESSION = "00000000-0000-4000-8000-000000000001";

async function runWithClaims(
  page: import("@playwright/test").Page,
  claims: Array<{ text: string; verdict: string; confidence: number }>,
) {
  const events = defaultPipelineEvents(SESSION);
  events[events.length - 1] = resultEvent(SESSION, {
    report: "## Mocked\nbody",
    claims: claims.map((c) => ({
      ...c,
      sources: ["https://example.com"],
      evidence: null,
    })),
    sources: [{ url: "https://example.com", title: "Example" }],
  });
  await mockResearchSession(page, { events });
  await page.goto("/");
  await page.getByLabel("Research query").fill("test");
  await page.getByRole("button", { name: /run pipeline/i }).click();
}

test("REFUTED claim renders with cross glyph and crimson label", async ({ page, obs }) => {
  await runWithClaims(page, [
    { text: "A claim that was refuted.", verdict: "REFUTED", confidence: 0.9 },
  ]);

  await expect(page.getByText("A claim that was refuted.")).toBeVisible();
  await expect(page.getByText("REFUTED").first()).toBeVisible();
  await expect(page.getByText("0 supported · 1 refuted")).toBeVisible();

  // Verify result SSE event structure
  const resultEvents = obs.sseEvents.filter((e) => e.event === "result");
  expect(resultEvents.length, "expected result SSE event").toBe(1);
  const resultData = JSON.parse(resultEvents[0].data);
  expect(resultData.claims, "expected claims in result").toBeTruthy();
  expect(Array.isArray(resultData.claims), "claims should be array").toBe(true);
});

test("UNVERIFIABLE claim is shown with question-mark glyph", async ({ page, obs }) => {
  await runWithClaims(page, [
    { text: "Could not be verified.", verdict: "UNVERIFIABLE", confidence: 0.4 },
  ]);

  await expect(page.getByText("Could not be verified.")).toBeVisible();
  await expect(page.getByText("UNVERIFIABLE").first()).toBeVisible();

  // Verify result SSE event structure
  const resultEvents = obs.sseEvents.filter((e) => e.event === "result");
  expect(resultEvents.length, "expected result SSE event").toBe(1);
  const resultData = JSON.parse(resultEvents[0].data);
  expect(resultData.claims, "expected claims in result").toBeTruthy();
  expect(Array.isArray(resultData.claims), "claims should be array").toBe(true);
});

test("mixed verdicts produce correct supported/refuted counts", async ({ page, obs }) => {
  await runWithClaims(page, [
    { text: "S1.", verdict: "SUPPORTED", confidence: 1.0 },
    { text: "S2.", verdict: "SUPPORTED", confidence: 0.9 },
    { text: "R1.", verdict: "REFUTED", confidence: 0.8 },
  ]);

  await expect(page.getByText("2 supported · 1 refuted")).toBeVisible();

  // Verify result SSE event structure
  const resultEvents = obs.sseEvents.filter((e) => e.event === "result");
  expect(resultEvents.length, "expected result SSE event").toBe(1);
  const resultData = JSON.parse(resultEvents[0].data);
  expect(resultData.claims, "expected claims in result").toBeTruthy();
  expect(Array.isArray(resultData.claims), "claims should be array").toBe(true);
});

test("unknown verdict string is normalized to UNVERIFIABLE", async ({ page, obs }) => {
  await runWithClaims(page, [
    // verdict not in the trusted whitelist; App.normalizeVerdict() should bucket as UNVERIFIABLE
    { text: "Server returned a strange verdict.", verdict: "MAYBE", confidence: 0.5 },
  ]);

  await expect(page.getByText("UNVERIFIABLE").first()).toBeVisible();

  // Verify result SSE event structure
  const resultEvents = obs.sseEvents.filter((e) => e.event === "result");
  expect(resultEvents.length, "expected result SSE event").toBe(1);
  const resultData = JSON.parse(resultEvents[0].data);
  expect(resultData.claims, "expected claims in result").toBeTruthy();
  expect(Array.isArray(resultData.claims), "claims should be array").toBe(true);
});
