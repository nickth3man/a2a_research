import { test as baseTest, expect } from "@playwright/test";

const MAX_CONSOLE = 500;
const MAX_CONSOLE_DETAILED = 500;
const MAX_PAGE_ERRORS = 50;
const MAX_API_REQUESTS = 200;
const MAX_SSE_EVENTS = 1000;
const MAX_SSE_GAPS = 1000;
const MAX_PARSED_SSE = 1000;
const MAX_REQUEST_TIMINGS = 200;
const MAX_DOM_SNAPSHOTS = 20;
type SseEvent = { ts: number; event: string; data: string };

type Observability = {
  consoleMessages: { ts: number; type: string; text: string }[];
  pageErrors: { ts: number; message: string; stack?: string }[];
  apiRequests: { ts: number; method: string; url: string; status?: number }[];
  sseEvents: SseEvent[];
};

interface ParsedProgressEvent {
  ts: number; event: string; type: "progress";
  session_id: string; phase: string; role: string | null;
  step_index: number; total_steps: number;
  substep_label: string; substep_index: number; substep_total: number;
  detail: string; elapsed_ms: number | null; gapMs: number;
}
interface ConsoleMessage {
  ts: number; type: string; text: string;
  location?: { url: string; lineNumber: number; columnNumber: number };
}
interface TimedSseEvent {
  ts: number; event: string; data: string; gapMs: number;
}
interface RequestTiming {
  url: string; method: string; startMs: number; durationMs: number;
  status: number; responseSize: number; responseBodySnippet?: string;
}
interface DomSnapshot {
  ts: number; html: string; role: string; phase: string; stepIndex: number;
}
interface WebVitals { lcp?: number; cls?: number; inp?: number; fcp?: number; }
interface ExtendedObservability extends Observability {
  parsedSse: ParsedProgressEvent[];
  sseGaps: TimedSseEvent[];
  requestTimings: RequestTiming[];
  webVitals: WebVitals;
  domSnapshots: DomSnapshot[];
  consoleMessagesDetailed: ConsoleMessage[];
}

export const test = baseTest.extend<{ obs: Observability & ExtendedObservability }>({
  obs: async ({ page }, use, testInfo) => {
    const pendingRequests = new Map<string, Observability["apiRequests"][number]>();
    let prevSseTs = 0;
    let lastDomSnapshot = 0;
    const obs: Observability & ExtendedObservability = {
      consoleMessages: [],
      pageErrors: [],
      apiRequests: [],
      sseEvents: [],
      parsedSse: [],
      sseGaps: [],
      requestTimings: [],
      webVitals: {},
      domSnapshots: [],
      consoleMessagesDetailed: [],
    };

    page.on("console", (msg) => {
      const ts = Date.now();
      const type = msg.type();
      const text = msg.text();
      if (obs.consoleMessages.length >= MAX_CONSOLE) return;
      obs.consoleMessages.push({ ts, type, text });
      const loc = msg.location();
      obs.consoleMessagesDetailed.push({
        ts, type, text,
        location: { url: loc.url, lineNumber: loc.lineNumber, columnNumber: loc.columnNumber },
      });
    });

    page.on("pageerror", (err) => {
      if (obs.pageErrors.length >= MAX_PAGE_ERRORS) return;
      obs.pageErrors.push({
        ts: Date.now(),
        message: err.message,
        stack: err.stack,
      });
    });

    page.on("request", (req) => {
      const url = req.url();
      if (!url.includes("/api/")) return;
      const ts = Date.now();
      const method = req.method();
      const key = url;
      const entry = { ts, method, url };
      if (obs.apiRequests.length >= MAX_API_REQUESTS) return;
      obs.apiRequests.push(entry);
      pendingRequests.set(key, entry);
    });
    page.on("response", (res) => {
      const url = res.url();
      if (!url.includes("/api/")) return;
      for (const [key, entry] of pendingRequests) {
        if (entry.url === url && entry.status === undefined) {
          entry.status = res.status();
          pendingRequests.delete(key);
          break;
        }
      }
    });

    page.on("requestfinished", async (req) => {
      const url = req.url();
      if (!url.includes("/api/")) return;
      if (obs.requestTimings.length >= MAX_REQUEST_TIMINGS) return;
      try {
        const timing = req.timing();
        const res = await req.response();
        const status = res?.status() ?? 0;
        const bodySize = (await res?.body())?.length ?? 0;

        // Capture response body for non-2xx (error diagnostics)
        let snippet: string | undefined;
        if (res && (status < 200 || status >= 300)) {
          const ct = res.headers()["content-type"] ?? "";
          if (
            !ct.includes("event-stream") &&
            !ct.startsWith("image/") &&
            !ct.startsWith("video/") &&
            !ct.startsWith("font/")
          ) {
            try {
              const body = await res.body();
              snippet = body.toString("utf-8").slice(0, 10_000);
            } catch {
              /* binary body — skip */
            }
          }
        }

        obs.requestTimings.push({
          url,
          method: req.method(),
          startMs: timing.startTime,
          durationMs: timing.responseEnd,
          status,
          responseSize: bodySize,
          responseBodySnippet: snippet,
        });
      } catch {
        /* timing may fail if request was aborted — skip */
      }
    });

    page.on("requestfailed", (req) => {
      const url = req.url();
      if (!url.includes("/api/")) return;
      if (obs.requestTimings.length >= MAX_REQUEST_TIMINGS) return;
      obs.requestTimings.push({
        url,
        method: req.method(),
        startMs: 0,
        durationMs: 0,
        status: 0,
        responseSize: 0,
        responseBodySnippet: req.failure()?.errorText ?? "unknown error",
      });
    });

    // SSE streams stay open until the page closes, so response.text() is too late
    // for in-test assertions. Use CDP Network.eventSourceMessageReceived which
    // fires per-message in real time.
    const cdp = await page.context().newCDPSession(page);
    await cdp.send("Network.enable");
    cdp.on("Network.eventSourceMessageReceived", (params) => {
      const ts = Date.now();
      const event = params.eventName || "message";
      const data = params.data;
      const gapMs = prevSseTs ? ts - prevSseTs : 0;
      prevSseTs = ts;

      // Keep existing push for backward compat
      if (obs.sseEvents.length < MAX_SSE_EVENTS) {
        obs.sseEvents.push({ ts, event, data });
      }

      // New: timed SSE with inter-event gap
      if (obs.sseGaps.length < MAX_SSE_GAPS) {
        obs.sseGaps.push({ ts, event, data, gapMs });
      }

      // New: parse progress events with isProgressEvent type guard
      try {
        const parsed = JSON.parse(data);
        if (typeof parsed === "object" && parsed !== null &&
            (parsed as Record<string, unknown>).type === "progress") {
          if (obs.parsedSse.length < MAX_PARSED_SSE) {
            obs.parsedSse.push({
              ts, event, gapMs,
              type: "progress",
              session_id: String((parsed as any).session_id ?? ""),
              phase: String((parsed as any).phase ?? ""),
              role: (parsed as any).role ? String((parsed as any).role) : null,
              step_index: Number((parsed as any).step_index ?? 0),
              total_steps: Number((parsed as any).total_steps ?? 0),
              substep_label: String((parsed as any).substep_label ?? ""),
              substep_index: Number((parsed as any).substep_index ?? 0),
              substep_total: Number((parsed as any).substep_total ?? 0),
              detail: String((parsed as any).detail ?? ""),
              elapsed_ms: (parsed as any).elapsed_ms != null ? Number((parsed as any).elapsed_ms) : null,
            });
        }
        }
        // DOM snapshot on step_completed (throttled 500ms)
        if ((parsed as Record<string,unknown>).phase === "step_completed" && ts - lastDomSnapshot >= 500) {
          lastDomSnapshot = ts;
          const snapRole = String((parsed as any).role ?? "");
          const snapStepIdx = Number((parsed as any).step_index ?? 0);
          setTimeout(async () => {
            try {
              const html = await page.evaluate(() => document.documentElement.outerHTML);
              if (html && html.length <= 200_000 && obs.domSnapshots.length < MAX_DOM_SNAPSHOTS) {
                obs.domSnapshots.push({ ts, html, role: snapRole, phase: "step_completed", stepIndex: snapStepIdx });
              }
            } catch { /* skip */ }
          }, 100);
        }
      } catch {
        /* not valid JSON — skip */
      }
    });


    // Collect Web Vitals once before test
    await page.evaluate(() => {
      const vitals: Record<string, number> = {};
      try {
        new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if (entry.entryType === "largest-contentful-paint") {
              vitals.lcp = (entry as any).startTime;
            }
          }
        }).observe({ type: "largest-contentful-paint", buffered: true });

        new PerformanceObserver((list) => {
          let cls = 0;
          for (const entry of list.getEntries()) {
            if (!(entry as any).hadRecentInput) {
              cls += (entry as any).value;
            }
          }
          vitals.cls = cls;
        }).observe({ type: "layout-shift", buffered: true });

        const paintEntries = performance.getEntriesByName("first-contentful-paint");
        if (paintEntries.length) vitals.fcp = paintEntries[0].startTime;
      } catch { /* PerformanceObserver not available */ }
      (window as any).__webVitals = vitals;
    });
    await use(obs);
    await cdp.detach().catch(() => {});

      // Disconnect PerformanceObservers
      try {
        await page.evaluate(() => {
          (window as any).__webVitals = undefined;
        });
      } catch { /* page may be closed */ }

      // CDP stability check: warn if SSE stream was silent but test passed
      const testPassed = testInfo.status === "passed";
      if (obs.sseEvents.length === 0 && testPassed) {
        console.warn(
          `[observability] CDP warning: test "${testInfo.title}" passed but captured 0 SSE events. ` +
          "CDP may have disconnected early or SSE endpoint did not stream. " +
          "Consider checking -- this could indicate a false-positive test."
        );
      }

    // Retrieve Web Vitals
    try {
      const vitals = await page.evaluate(() => (window as any).__webVitals);
      if (vitals) obs.webVitals = vitals;
    } catch { /* page may be closed */ }

    const attach = async (name: string, body: object | string, contentType: string) => {
      const buf = typeof body === "string" ? body : JSON.stringify(body, null, 2);
      if (!buf) return;
      await testInfo.attach(name, { body: buf, contentType });
    };

    await attach("console.json", obs.consoleMessages, "application/json");
    await attach("page-errors.json", obs.pageErrors, "application/json");
    await attach("api-requests.json", obs.apiRequests, "application/json");
    await attach(
      "sse-events.jsonl",
      obs.sseEvents.map((e) => JSON.stringify(e)).join("\n"),
      "application/x-ndjson",
    );

    await attach("parsed-sse.json", obs.parsedSse, "application/json");
    await attach(
      "sse-gaps.jsonl",
      obs.sseGaps.map((e) => JSON.stringify(e)).join("\n"),
      "application/x-ndjson",
    );
    await attach("console-detailed.json", obs.consoleMessagesDetailed, "application/json");

    // Heavy artifacts: only on failure or non-CI
    const failed = testInfo.status !== "passed" && testInfo.status !== "skipped";
    const isCI = !!process.env.CI;
    if (obs.webVitals.lcp != null) await attach("web-vitals.json", obs.webVitals, "application/json");
    if (obs.domSnapshots.length > 0 && (failed || !isCI)) {
      await attach("dom-snapshots.json", obs.domSnapshots, "application/json");
    }
    if (obs.requestTimings.length > 0) {
      await attach("request-timings.json", obs.requestTimings, "application/json");
    }
  },
});

export { expect };
