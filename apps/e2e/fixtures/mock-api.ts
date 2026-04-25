import type { Page } from "@playwright/test";

export type SseEvent = { event: string; data: object | string };

const SESSION_ID = "00000000-0000-4000-8000-000000000001";

function encode(events: SseEvent[]): string {
  return events
    .map((e) => {
      const data = typeof e.data === "string" ? e.data : JSON.stringify(e.data);
      return `event: ${e.event}\ndata: ${data}\n\n`;
    })
    .join("");
}

export interface MockResearchOpts {
  events?: SseEvent[];
  postStatus?: number;
  postBody?: object | string;
  postNetworkError?: boolean;
  sessionId?: string;
}

export async function mockResearchSession(page: Page, opts: MockResearchOpts = {}) {
  const sessionId = opts.sessionId ?? SESSION_ID;
  const events = opts.events ?? defaultPipelineEvents(sessionId);

  await page.route("**/api/research", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    if (opts.postNetworkError) return route.abort("failed");
    const status = opts.postStatus ?? 200;
    const body =
      opts.postBody !== undefined
        ? typeof opts.postBody === "string"
          ? opts.postBody
          : JSON.stringify(opts.postBody)
        : JSON.stringify({ session_id: sessionId });
    await route.fulfill({
      status,
      contentType: "application/json",
      body,
    });
  });

  await page.route(`**/api/research/${sessionId}/stream*`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      headers: { "Cache-Control": "no-cache", Connection: "keep-alive" },
      body: encode(events),
    });
  });

  return { sessionId };
}

export function progressEvent(
  sessionId: string,
  partial: Partial<{
    phase: string;
    role: string | null;
    step_index: number;
    total_steps: number;
    substep_label: string;
    detail: string;
  }>,
): SseEvent {
  return {
    event: "progress",
    data: {
      type: "progress",
      session_id: sessionId,
      phase: partial.phase ?? "step_started",
      role: partial.role ?? null,
      step_index: partial.step_index ?? 0,
      total_steps: partial.total_steps ?? 12,
      substep_label: partial.substep_label ?? "",
      substep_index: 0,
      substep_total: 1,
      detail: partial.detail ?? "",
      elapsed_ms: null,
    },
  };
}

export function resultEvent(
  sessionId: string,
  partial: Partial<{
    report: string;
    claims: Array<{
      text: string;
      verdict: string;
      confidence: number;
      sources: string[];
      evidence: string | null;
    }>;
    sources: Array<{ url: string; title: string }>;
    diagnostics: Array<{
      role: string;
      code: string;
      severity: string;
      retryable: boolean;
      root_cause: string;
      remediation: string;
      trace_id: string;
    }>;
  }>,
): SseEvent {
  return {
    event: "result",
    data: {
      type: "result",
      session_id: sessionId,
      report: partial.report ?? "## Result\nMocked.",
      claims: partial.claims ?? [],
      sources: partial.sources ?? [],
      diagnostics: partial.diagnostics ?? [],
      error: null,
    },
  };
}

export function defaultPipelineEvents(sessionId: string): SseEvent[] {
  const roles = [
    "preprocessor",
    "clarifier",
    "planner",
    "searcher",
    "ranker",
    "reader",
    "deduplicator",
    "fact_checker",
    "adversary",
    "synthesizer",
    "critic",
    "postprocessor",
  ];
  const events: SseEvent[] = [];
  roles.forEach((role, i) => {
    events.push(
      progressEvent(sessionId, {
        phase: "step_started",
        role,
        step_index: i,
        total_steps: 12,
        substep_label: `${role}_started`,
      }),
      progressEvent(sessionId, {
        phase: "step_completed",
        role,
        step_index: i,
        total_steps: 12,
        substep_label: `${role}_completed`,
      }),
    );
  });
  events.push(
    resultEvent(sessionId, {
      report: "## Mocked Report\nThis is a fixture-driven response.",
      claims: [
        {
          text: "A mocked claim that is supported.",
          verdict: "SUPPORTED",
          confidence: 0.95,
          sources: ["https://example.com/a"],
          evidence: null,
        },
      ],
      sources: [{ url: "https://example.com/a", title: "Example A" }],
    }),
  );
  return events;
}
