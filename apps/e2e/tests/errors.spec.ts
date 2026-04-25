import { test, expect } from "../fixtures/observability";
import {
  mockResearchSession,
  progressEvent,
} from "../fixtures/mock-api";

test("backend POST 500 surfaces detail in error banner", async ({ page, obs }) => {
  await mockResearchSession(page, {
    postStatus: 500,
    postBody: { detail: "internal kaboom" },
  });

  await page.goto("/");
  await page.getByLabel("Research query").fill("anything");
  await page.getByRole("button", { name: /run pipeline/i }).click();

  await expect(page.getByText("internal kaboom")).toBeVisible();

  // Verify requestTimings captures the 500
  const err500 = obs.requestTimings.filter((r) => r.status === 500);
  expect(err500.length, "expected 500 status in requestTimings").toBeGreaterThan(0);
});

test("network failure on POST surfaces a connection-failed message", async ({ page, obs }) => {
  await mockResearchSession(page, { postNetworkError: true });

  await page.goto("/");
  await page.getByLabel("Research query").fill("anything");
  await page.getByRole("button", { name: /run pipeline/i }).click();

  await expect(page.getByText(/failed to connect/i)).toBeVisible();

  const failures = obs.requestTimings.filter((r) => r.status === 0 && r.responseBodySnippet);
  expect(failures.length, "expected failed request in requestTimings").toBeGreaterThan(0);
});

test("server-side app-error event is shown to the user", async ({ page, obs }) => {
  const { sessionId } = await mockResearchSession(page, {
    events: [
      progressEvent("00000000-0000-4000-8000-000000000001", {
        phase: "step_started",
        role: "planner",
        step_index: 1,
      }),
      {
        event: "app-error",
        data: {
          type: "error",
          session_id: "00000000-0000-4000-8000-000000000001",
          message: "synthesizer crashed",
        },
      },
    ],
  });
  expect(sessionId).toBeTruthy();

  await page.goto("/");
  await page.getByLabel("Research query").fill("anything");
  await page.getByRole("button", { name: /run pipeline/i }).click();

  await expect(page.getByText("synthesizer crashed")).toBeVisible();

  expect(obs.pageErrors.length, "expected no page errors").toBe(0);
});

test("SSE stream that closes before terminal event raises 'Connection lost'", async ({ page, obs }) => {
  await mockResearchSession(page, {
    events: [
      progressEvent("00000000-0000-4000-8000-000000000001", {
        phase: "step_started",
        role: "planner",
        step_index: 1,
      }),
    ],
  });

  await page.goto("/");
  await page.getByLabel("Research query").fill("anything");
  await page.getByRole("button", { name: /run pipeline/i }).click();

  await expect(page.getByText(/connection lost/i)).toBeVisible();

  expect(obs.sseGaps.length, "expected SSE gap data").toBeGreaterThan(0);
});
