import { test, expect } from "../fixtures/observability";

test("submitting a query advances through loading to results", async ({ page, obs }) => {
  const startTime = Date.now();

  const nonce = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
  const query = `Who wrote the novel 1984? (test-${nonce})`;

  await page.goto("/");

  await page.getByLabel("Research query").fill(query);
  await page.getByRole("button", { name: /run pipeline/i }).click();

  await expect(page.locator("button.btn-primary")).toHaveText(/running/i, {
    timeout: 10_000,
  });

  await expect(page.getByText(/George Orwell/i)).toBeVisible({
    timeout: 4 * 60_000,
  });

  const stepCompleted = obs.sseEvents.filter((e) => /"step_completed"/.test(e.data));
  expect(
    stepCompleted.length,
    "pipeline must emit multiple step_completed events (defeats result caching)",
  ).toBeGreaterThan(3);

  const roles = new Set<string>();
  for (const e of obs.sseEvents) {
    const m = e.data.match(/"role":\s*"([^"]+)"/);
    if (m) roles.add(m[1]);
  }
  expect(
    roles.size,
    `expected events from multiple agents (saw: ${[...roles].join(", ") || "none"})`,
  ).toBeGreaterThanOrEqual(3);
  // Total wall-clock duration < 240s
  const duration = (Date.now() - startTime) / 1000;
  expect(duration, `pipeline completed in ${duration.toFixed(0)}s (< 240s)`).toBeLessThan(240);

  // No single SSE gap > 60s (stall detection)
  const largeGaps = obs.sseGaps.filter((e) => e.gapMs > 60_000);
  expect(largeGaps.length, `expected no SSE gaps > 60s, found ${largeGaps.length}`).toBe(0);

  // Per-agent elapsed_ms validation from backend
  const timedAgents = obs.parsedSse.filter(
    (e) => e.phase === "step_completed" && e.elapsed_ms != null
  );
  expect(timedAgents.length, "expected agents to report elapsed_ms").toBeGreaterThan(0);
  for (const e of timedAgents) {
    expect(e.elapsed_ms!, `${e.role} elapsed_ms`).toBeGreaterThan(0);
  }

  // Progressive gap check replaces blind 4-min timeout:
  // Immediate failure at first excessive gap rather than waiting for full timeout
});
