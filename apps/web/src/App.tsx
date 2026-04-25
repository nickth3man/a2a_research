import { useState, useEffect, useRef } from "react";
import { StateNav } from "./components/StateNav";
import { QueryInput } from "./components/QueryInput";
import { HowItWorks } from "./components/HowItWorks";
import { EmptyState } from "./components/EmptyState";
import { LoadingState } from "./components/LoadingState";
import { ResultsState } from "./components/ResultsState";
import { startResearch, normalizeRole } from "./services/api";
import { AGENTS } from "./mocks/data";
import type {
  UIState,
  StatusMap,
  Claim,
  Source,
  Verdict,
  DiagnosticItem,
} from "./types";

function initialStatuses(): StatusMap {
  return Object.fromEntries(AGENTS.map((a) => [a.key, "pending" as const]));
}

function normalizeVerdict(v: string): Verdict {
  if (v === "SUPPORTED" || v === "REFUTED") return v;
  return "UNVERIFIABLE";
}

export default function App() {
  const [uiState, setUiState] = useState<UIState>(() => {
    const saved = localStorage.getItem("a2a_ui_state");
    const valid: UIState[] = ["empty", "loading", "results"];
    if (saved && valid.includes(saved as UIState)) {
      if (saved === "loading") return "empty";
      return saved as UIState;
    }
    return "empty";
  });
  const [progress, setProgress] = useState(0);
  const [statuses, setStatuses] = useState<StatusMap>(initialStatuses);
  const [tickerLines, setTickerLines] = useState<string[]>([]);
  const [report, setReport] = useState("");
  const [claims, setClaims] = useState<Claim[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [diagnostics, setDiagnostics] = useState<DiagnosticItem[]>([]);
  const [degradedRoles, setDegradedRoles] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const cleanupRef = useRef<(() => void) | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      cleanupRef.current?.();
    };
  }, []);

  const setAndSave = (s: UIState) => {
    setUiState(s);
    localStorage.setItem("a2a_ui_state", s);
  };

  const handleSubmit = async (query: string) => {
    cleanupRef.current?.();
    cleanupRef.current = null;
    setProgress(0);
    setStatuses(initialStatuses());
    setTickerLines([]);
    setReport("");
    setClaims([]);
    setSources([]);
    setDiagnostics([]);
    setDegradedRoles(new Set());
    setError(null);
    setAndSave("loading");

    const result = await startResearch(query, {
      onProgress(e) {
        if (!mountedRef.current) return;
        const role = normalizeRole(e.role);
        if (role) {
          setStatuses((prev) => {
            const next = { ...prev };
            if (e.phase === "step_started") next[role] = "running";
            else if (e.phase === "step_completed") next[role] = "completed";
            else if (e.phase === "step_failed") next[role] = "failed";
            return next;
          });
        }
        setProgress(Math.round((e.step_index / e.total_steps) * 100));
        if (e.detail)
          setTickerLines((prev) => [e.detail, ...prev].slice(0, 20));
      },
      onResult(e) {
        if (!mountedRef.current) return;
        setReport(e.report);
        setClaims(
          e.claims.map((c) => ({
            text: c.text,
            verdict: normalizeVerdict(c.verdict),
            confidence: c.confidence,
            sources: c.sources,
            evidence: c.evidence ?? undefined,
          })),
        );
        setSources(
          e.sources.map((s) => {
            let host = s.url;
            try {
              host = new URL(s.url).hostname;
            } catch {
              /* keep url */
            }
            return { file: s.url, title: s.title || s.url, meta: host };
          }),
        );
        if (e.diagnostics?.length) setDiagnostics(e.diagnostics);
        setAndSave("results");
        localStorage.removeItem("a2a_session_id");
      },
      onError(msg) {
        if (!mountedRef.current) return;
        setError(msg);
        setAndSave("empty");
        localStorage.removeItem("a2a_session_id");
      },
      onWarning(e) {
        if (!mountedRef.current) return;
        if (e.envelope) setDiagnostics((prev) => [...prev, e.envelope!]);
        const role = normalizeRole(e.role);
        if (role) setStatuses((prev) => ({ ...prev, [role]: "warning" }));
        if (e.detail)
          setTickerLines((prev) => [`⚠ ${e.detail}`, ...prev].slice(0, 20));
      },
      onDegraded(e) {
        if (!mountedRef.current) return;
        if (e.envelope) setDiagnostics((prev) => [...prev, e.envelope!]);
        const role = normalizeRole(e.role);
        if (role) {
          setDegradedRoles((prev) => new Set([...prev, role]));
          setStatuses((prev) => ({ ...prev, [role]: "degraded" }));
        }
        if (e.detail)
          setTickerLines((prev) =>
            [`⚡ degraded: ${e.detail}`, ...prev].slice(0, 20),
          );
      },
      onRetrying(e) {
        if (!mountedRef.current) return;
        if (e.detail)
          setTickerLines((prev) =>
            [`↺ retrying: ${e.detail}`, ...prev].slice(0, 20),
          );
      },
      onFinalDiagnostics(e) {
        if (!mountedRef.current) return;
        if (e.detail)
          setTickerLines((prev) => [`✓ ${e.detail}`, ...prev].slice(0, 20));
      },
    });
    cleanupRef.current = result.cleanup;
    if (result.session_id) {
      localStorage.setItem("a2a_session_id", result.session_id);
    }
  };

  return (
    <>
      <main>
        <div
          style={{
            maxWidth: 1180,
            margin: "0 auto",
            padding: "28px 28px 60px",
          }}
        >
          <StateNav current={uiState} onChange={setAndSave} />
          {error && (
            <div
              style={{
                marginBottom: 16,
                padding: "12px 16px",
                background: "#fff0f0",
                border: "1px solid #ffcdd2",
                borderRadius: 4,
                color: "#c62828",
                fontSize: 13,
              }}
            >
              {error}
            </div>
          )}

          {uiState === "empty" && (
            <>
              <HowItWorks />
              <EmptyState />
            </>
          )}
          {uiState === "loading" && (
            <LoadingState
              progress={progress}
              statuses={statuses}
              tickerLines={tickerLines}
              degradedRoles={degradedRoles}
            />
          )}
          {uiState === "results" && (
            <ResultsState
              report={report}
              claims={claims}
              sources={sources}
              diagnostics={diagnostics}
            />
          )}

          <QueryInput onSubmit={handleSubmit} state={uiState} />

          <div
            style={{
              marginTop: 28,
              paddingTop: 20,
              borderTop: "1px solid var(--rule)",
              display: "flex",
              justifyContent: "space-between",
              fontSize: 10.5,
              color: "var(--muted)",
            }}
          >
            <span
              className="mono"
              style={{ letterSpacing: ".12em", textTransform: "uppercase" }}
            >
              A2A Research · fin.
            </span>
            <span className="mono" style={{ letterSpacing: ".12em" }}>
              v0.42.0 · built with{" "}
              <em style={{ color: "var(--accent)" }}>care</em>
            </span>
          </div>
        </div>
      </main>
    </>
  );
}
