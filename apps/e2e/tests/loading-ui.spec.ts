import { test, expect } from "../fixtures/observability";
import {
  mockResearchSession,
  progressEvent,
} from "../fixtures/mock-api";

const SESSION = "00000000-0000-4000-8000-000000000001";

test("progress percent reflects step_index/total_steps", async ({ page, obs }) => {
  // Stop short of the terminal event so the loading state stays visible.
  await mockResearchSession(page, {
    events: [
      progressEvent(SESSION, {
        phase: "step_started",
        role: "searcher",
        step_index: 6,
        total_steps: 12,
        substep_label: "search_started",
      }),
    ],
  });

  await page.goto("/");
  await page.getByLabel("Research query").fill("test");
  await page.getByRole("button", { name: /run pipeline/i }).click();

  // 6 / 12 = 50%; useCountUp animates so we wait for the digits to settle.
  await expect(page.getByText(/^50$/)).toBeVisible({ timeout: 5_000 });
  await expect(page.getByText(/connection lost/i)).toBeVisible();

  const progressEvents = obs.parsedSse.filter((e) => e.type === "progress");
  expect(progressEvents.length, "expected parsed progress events").toBeGreaterThan(0);
  const searcherEvent = progressEvents.find((e) => e.role === "searcher");
  expect(searcherEvent, "expected searcher progress event").toBeTruthy();
  expect(searcherEvent!.step_index, "searcher step_index").toBe(6);
  expect(searcherEvent!.total_steps, "searcher total_steps").toBe(12);
});

test("ticker shows the most recent progress detail", async ({ page, obs }) => {
  await mockResearchSession(page, {
    events: [
      progressEvent(SESSION, {
        phase: "step_substep",
        role: "reader",
        step_index: 5,
        substep_label: "fetch_url_1",
        detail: "fetching https://example.com/article-1",
      }),
    ],
  });

  await page.goto("/");
  await page.getByLabel("Research query").fill("test");
  await page.getByRole("button", { name: /run pipeline/i }).click();

  await expect(page.getByText(/fetching https:\/\/example\.com\/article-1/)).toBeVisible();

  const readerEvents = obs.parsedSse.filter((e) => e.role === "reader");
  expect(readerEvents.length, "expected reader progress events").toBeGreaterThan(0);
  expect(readerEvents[0].substep_label, "reader substep").toBe("fetch_url_1");
});

test("degraded_mode event renders the degraded banner", async ({ page, obs }) => {
  await mockResearchSession(page, {
    events: [
      progressEvent(SESSION, {
        phase: "step_started",
        role: "searcher",
        step_index: 3,
      }),
      {
        event: "degraded_mode",
        data: {
          type: "degraded_mode",
          session_id: SESSION,
          phase: "degraded",
          role: "searcher",
          detail: "Tavily rate limit; falling back to Brave",
          envelope: {
            role: "searcher",
            code: "RATE_LIMIT",
            severity: "warning",
            retryable: true,
            root_cause: "Tavily rate limit",
            remediation: "switched to Brave",
            trace_id: "trace-1",
          },
        },
      },
    ],
  });

  await page.goto("/");
  await page.getByLabel("Research query").fill("test");
  await page.getByRole("button", { name: /run pipeline/i }).click();

  await expect(page.getByText(/degraded mode active for/i)).toBeVisible();
  await expect(page.getByText(/falling back to Brave/i)).toBeVisible();

  const searcherSse = obs.parsedSse.filter((e) => e.role === "searcher");
  expect(searcherSse.length, "expected searcher SSE events").toBeGreaterThan(0);
});
