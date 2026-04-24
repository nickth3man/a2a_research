import { useState } from "react";
import { Paper, Eyebrow } from "./Primitives";
import { useCountUp } from "../hooks/useCountUp";
import { useTicker } from "../hooks/useTicker";
import { AGENTS, STAGES, MOCK_METRICS, TICKER_LINES } from "../mocks/data";
import type { StatusMap } from "../types";

const AGENT_LABELS = new Map(AGENTS.map((agent) => [agent.key, agent.label]));

function statusFor(statuses: StatusMap, key: string) {
  return statuses[key] || "pending";
}

function isRunningLike(status: ReturnType<typeof statusFor>) {
  return status === "running" || status === "warning" || status === "degraded";
}

function isCompletedLike(status: ReturnType<typeof statusFor>) {
  return status === "completed";
}

function nodeColors(status: ReturnType<typeof statusFor>) {
  if (status === "failed") {
    return {
      fill: "#fdeaea",
      stroke: "#c62828",
      text: "#c62828",
      background: "#fff0f0",
      border: "#f3c6c6",
      dot: "#c62828",
    };
  }

  if (status === "degraded") {
    return {
      fill: "#fff8db",
      stroke: "#7c5f00",
      text: "#7c5f00",
      background: "#fffbe6",
      border: "#ffe58f",
      dot: "#7c5f00",
    };
  }

  if (status === "warning") {
    return {
      fill: "#fff4db",
      stroke: "var(--amber)",
      text: "var(--amber)",
      background: "var(--amber-soft)",
      border: "#f3dfa8",
      dot: "var(--amber)",
    };
  }

  if (status === "running") {
    return {
      fill: "var(--amber)",
      stroke: "var(--amber)",
      text: "var(--amber)",
      background: "var(--amber-soft)",
      border: "#f3dfa8",
      dot: "var(--amber)",
    };
  }

  if (status === "completed") {
    return {
      fill: "var(--accent)",
      stroke: "var(--accent)",
      text: "var(--ink)",
      background: "transparent",
      border: "transparent",
      dot: "var(--accent)",
    };
  }

  return {
    fill: "var(--paper)",
    stroke: "var(--rule)",
    text: "var(--muted)",
    background: "transparent",
    border: "transparent",
    dot: "var(--muted-2)",
  };
}

function PipelineFlow({ statuses }: { statuses: StatusMap }) {
  const byStage = STAGES.map((st) => ({
    ...st,
    agents: AGENTS.filter((a) => a.stage === st.key),
  }));

  const W = 1080;
  const H = 300;
  const colX = [80, 280, 540, 780, 990];

  const nodes: Record<string, { x: number; y: number; stage: string }> = {};
  byStage.forEach((st, si) => {
    const n = st.agents.length;
    const centerY = H / 2 + 10;
    const spacing = 58;
    st.agents.forEach((a, ai) => {
      const y = centerY + (ai - (n - 1) / 2) * spacing;
      nodes[a.key] = { x: colX[si], y, stage: st.key };
    });
  });

  const edges: { from: string; to: string }[] = [];
  for (let i = 0; i < byStage.length - 1; i++) {
    byStage[i].agents.forEach((a) => {
      byStage[i + 1].agents.forEach((b) => {
        edges.push({ from: a.key, to: b.key });
      });
    });
  }

  const edgeColor = (a: string, b: string) => {
    const sa = statusFor(statuses, a);
    const sb = statusFor(statuses, b);
    if (sa === "failed" || sb === "failed") return "#c62828";
    if (sa === "completed" && (sb === "completed" || isRunningLike(sb)))
      return "var(--accent)";
    if (sa === "completed" || isRunningLike(sb)) return "var(--accent)";
    return "var(--rule)";
  };
  const edgeActive = (a: string, b: string) =>
    statusFor(statuses, a) === "completed" &&
    (isRunningLike(statusFor(statuses, b)) ||
      statusFor(statuses, b) === "completed");

  return (
    <Paper
      style={{
        padding: "22px 24px 20px",
        overflow: "hidden",
        position: "relative",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 14,
        }}
      >
        <Eyebrow dot color="var(--amber)">
          § 02 · Live pipeline
        </Eyebrow>
        <span
          className="mono"
          style={{
            fontSize: 10.5,
            color: "var(--muted)",
            letterSpacing: ".1em",
          }}
        >
          12 agents · 5 stages · dag-flow
        </span>
      </div>

      <div style={{ position: "relative", width: "100%", overflow: "hidden" }}>
        <svg
          viewBox={`0 0 ${W} ${H}`}
          width="100%"
          style={{ display: "block", maxHeight: 300 }}
        >
          <defs>
            <marker
              id="arrow"
              viewBox="0 0 10 10"
              refX="9"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto"
            >
              <path d="M0,0 L10,5 L0,10 z" fill="var(--accent)" />
            </marker>
            <linearGradient id="edgeGrad" x1="0" x2="1">
              <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.15" />
              <stop offset="50%" stopColor="var(--accent)" stopOpacity="0.6" />
              <stop
                offset="100%"
                stopColor="var(--accent)"
                stopOpacity="0.15"
              />
            </linearGradient>
          </defs>

          {byStage.map((st, si) => {
            const x = colX[si];
            return (
              <g key={st.key}>
                <line
                  x1={x}
                  y1={32}
                  x2={x}
                  y2={H - 16}
                  stroke="var(--rule)"
                  strokeDasharray="2 3"
                />
                <text
                  x={x}
                  y={18}
                  textAnchor="middle"
                  fontSize="9"
                  fill="var(--muted)"
                  letterSpacing="0.18em"
                  fontFamily="JetBrains Mono"
                  fontWeight="500"
                  style={{ textTransform: "uppercase" }}
                >
                  {st.n} · {st.label}
                </text>
              </g>
            );
          })}

          {edges.map((e, i) => {
            const a = nodes[e.from];
            const b = nodes[e.to];
            const c = edgeColor(e.from, e.to);
            const active = edgeActive(e.from, e.to);
            const midX = (a.x + b.x) / 2;
            const path = `M${a.x + 11},${a.y} C${midX},${a.y} ${midX},${b.y} ${b.x - 11},${b.y}`;
            return (
              <g key={i}>
                <path
                  d={path}
                  fill="none"
                  stroke={c}
                  strokeWidth={active ? 1.2 : 0.6}
                  opacity={active ? 0.8 : 0.3}
                />
                {active && (
                  <path
                    d={path}
                    fill="none"
                    stroke="var(--accent)"
                    strokeWidth="1.4"
                    strokeDasharray="4 6"
                    opacity="0.9"
                    style={{ animation: "dash-flow 1s linear infinite" }}
                  />
                )}
              </g>
            );
          })}

          {AGENTS.map((a) => {
            const { x, y } = nodes[a.key];
            const s = statusFor(statuses, a.key);
            const isRunning = isRunningLike(s);
            const isDone = isCompletedLike(s);
            const colors = nodeColors(s);
            const labelY = y - 16;
            const approxTextW = a.label.length * 6.4 + 8;
            return (
              <g key={a.key} style={{ cursor: "default" }}>
                <rect
                  x={x - approxTextW / 2}
                  y={labelY - 9}
                  width={approxTextW}
                  height={13}
                  fill="var(--paper)"
                  rx="2"
                />
                <text
                  x={x}
                  y={labelY + 1}
                  textAnchor="middle"
                  fontSize="10.5"
                  fill={colors.text}
                  fontFamily="Inter, system-ui, sans-serif"
                  fontWeight={isRunning ? 600 : 500}
                  letterSpacing="0.01em"
                >
                  {a.label}
                </text>

                {isRunning && (
                  <circle
                    cx={x}
                    cy={y}
                    r={14}
                    fill="none"
                    stroke="var(--amber)"
                    strokeOpacity="0.35"
                    strokeWidth="1"
                  >
                    <animate
                      attributeName="r"
                      from="10"
                      to="22"
                      dur="1.4s"
                      repeatCount="indefinite"
                    />
                    <animate
                      attributeName="stroke-opacity"
                      from="0.45"
                      to="0"
                      dur="1.4s"
                      repeatCount="indefinite"
                    />
                  </circle>
                )}
                <circle
                  cx={x}
                  cy={y}
                  r={8}
                  fill={colors.fill}
                  stroke={colors.stroke}
                  strokeWidth="1.5"
                />
                {isDone && (
                  <path
                    d={`M${x - 3},${y} L${x - 0.5},${y + 2.5} L${x + 3.5},${y - 2.5}`}
                    stroke="#fff"
                    strokeWidth="1.4"
                    fill="none"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                )}
                {isRunning && <circle cx={x} cy={y} r={2} fill="#fff" />}
              </g>
            );
          })}
        </svg>
      </div>
    </Paper>
  );
}

function LiveTicker({ tickerLines }: { tickerLines: string[] }) {
  const lines = useTicker(
    tickerLines.length ? tickerLines : TICKER_LINES,
    900,
    true,
  );
  const [baseTime] = useState(() => Date.now());
  return (
    <Paper style={{ padding: 0, overflow: "hidden" }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "10px 16px",
          borderBottom: "1px solid var(--rule)",
          background: "var(--ivory)",
        }}
      >
        <span
          style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: "var(--amber)",
            animation: "blink 1.2s steps(2) infinite",
          }}
        />
        <span
          className="mono"
          style={{
            fontSize: 10.5,
            color: "var(--muted)",
            letterSpacing: ".14em",
            textTransform: "uppercase",
          }}
        >
          § 03 · Agent log · reader
        </span>
        <div style={{ flex: 1 }} />
        <span
          className="mono"
          style={{ fontSize: 10, color: "var(--muted-2)" }}
        >
          live
        </span>
      </div>
      <div
        style={{
          background: "var(--ink)",
          color: "#e8e3d6",
          padding: "14px 18px",
          height: 220,
          overflow: "hidden",
          position: "relative",
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: 0,
            pointerEvents: "none",
            background:
              "repeating-linear-gradient(0deg, rgba(255,255,255,0.02) 0 1px, transparent 1px 3px)",
          }}
        />
        {lines.map((line, i) => (
          <div
            key={i + line}
            style={{
              fontFamily: "JetBrains Mono, monospace",
              fontSize: 11.5,
              lineHeight: 1.85,
              color:
                i === 0
                  ? "#faf8f3"
                  : `rgba(232,227,214,${Math.max(0.2, 1 - i * 0.15)})`,
              animation: i === 0 ? "ticker-in .35s ease both" : "none",
              display: "flex",
              gap: 8,
            }}
          >
            <span style={{ color: "var(--accent-2)", opacity: 0.7 }}>▸</span>
            <span
              className="mono"
              style={{ color: "rgba(232,227,214,0.4)", minWidth: 68 }}
            >
              {new Date(baseTime - i * 900).toLocaleTimeString("en-US", {
                hour12: false,
              })}
            </span>
            <span>{line}</span>
          </div>
        ))}
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            bottom: 0,
            height: 60,
            background: "linear-gradient(transparent, var(--ink))",
            pointerEvents: "none",
          }}
        />
      </div>
    </Paper>
  );
}

function BigProgress({ pct, statuses }: { pct: number; statuses: StatusMap }) {
  const count = useCountUp(pct, 600, [pct]);
  const C = 2 * Math.PI * 54;

  const stageAgents = STAGES.map((st) => ({
    key: st.key,
    agents: AGENTS.filter((a) => a.stage === st.key),
  }));

  const stageStatus = (stageKey: string) => {
    const agents = stageAgents.find((s) => s.key === stageKey)?.agents ?? [];
    if (agents.some((a) => statusFor(statuses, a.key) === "failed"))
      return "failed";
    if (agents.every((a) => statusFor(statuses, a.key) === "completed"))
      return "done";
    if (agents.some((a) => isRunningLike(statusFor(statuses, a.key))))
      return "running";
    return "pending";
  };

  const runningAgent = AGENTS.find((a) =>
    isRunningLike(statusFor(statuses, a.key)),
  );

  return (
    <Paper
      style={{
        padding: 28,
        display: "flex",
        alignItems: "center",
        gap: 26,
        position: "relative",
        overflow: "hidden",
      }}
    >
      <div className="scan-beam" />
      <div
        style={{ position: "relative", width: 132, height: 132, flexShrink: 0 }}
      >
        <svg
          width="132"
          height="132"
          viewBox="0 0 132 132"
          style={{ transform: "rotate(-90deg)" }}
        >
          <circle
            cx="66"
            cy="66"
            r="54"
            fill="none"
            stroke="var(--rule)"
            strokeWidth="6"
          />
          <circle
            cx="66"
            cy="66"
            r="54"
            fill="none"
            stroke="var(--accent)"
            strokeWidth="6"
            strokeDasharray={C}
            strokeDashoffset={C * (1 - pct / 100)}
            strokeLinecap="round"
            style={{
              transition: "stroke-dashoffset .7s cubic-bezier(.2,.65,.2,1)",
            }}
          />
          {[...Array(36)].map((_, i) => (
            <line
              key={i}
              x1="66"
              y1="6"
              x2="66"
              y2="10"
              stroke={i * 10 < pct * 0.36 ? "var(--accent)" : "var(--rule)"}
              strokeWidth="1"
              transform={`rotate(${i * 10} 66 66)`}
              opacity={i * 10 < pct * 0.36 ? 1 : 0.5}
            />
          ))}
        </svg>
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <div
            className="serif"
            style={{
              fontSize: 42,
              lineHeight: 1,
              color: "var(--ink)",
              letterSpacing: "-0.02em",
            }}
          >
            {count}
            <span style={{ fontSize: 20, color: "var(--muted)" }}>%</span>
          </div>
          <div
            className="mono"
            style={{
              fontSize: 9,
              letterSpacing: ".2em",
              color: "var(--muted)",
              textTransform: "uppercase",
              marginTop: 2,
            }}
          >
            complete
          </div>
        </div>
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        <Eyebrow dot color="var(--amber)">
          Now running
        </Eyebrow>
        <h3
          className="serif"
          style={{
            fontSize: 32,
            lineHeight: 1.1,
            marginTop: 10,
            letterSpacing: "-0.015em",
          }}
        >
          {runningAgent ? (
            <>
              <em style={{ color: "var(--accent)" }}>{runningAgent.label}</em>{" "}
              is processing
            </>
          ) : (
            <em style={{ color: "var(--accent)" }}>Pipeline running…</em>
          )}
        </h3>

        <div style={{ display: "flex", gap: 6, marginTop: 18 }}>
          {STAGES.map((st) => {
            const s = stageStatus(st.key);
            const done = s === "done";
            const running = s === "running";
            const failed = s === "failed";
            return (
              <div key={st.key} style={{ flex: 1 }}>
                <div
                  style={{
                    height: 4,
                    borderRadius: 2,
                    background: failed
                      ? "#c62828"
                      : done
                        ? "var(--accent)"
                        : running
                          ? "linear-gradient(90deg, var(--accent) 0%, var(--amber) 60%, var(--rule) 60%)"
                          : "var(--rule)",
                    backgroundSize: running ? "200% 100%" : undefined,
                    animation: running
                      ? "progress-stripes 1.2s linear infinite"
                      : "none",
                  }}
                />
                <div
                  className="mono"
                  style={{
                    marginTop: 6,
                    fontSize: 9.5,
                    letterSpacing: ".12em",
                    textTransform: "uppercase",
                    color: failed
                      ? "#c62828"
                      : done
                        ? "var(--accent)"
                        : running
                          ? "var(--amber)"
                          : "var(--muted)",
                    fontWeight: running ? 600 : 500,
                  }}
                >
                  {st.n} · {st.label}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </Paper>
  );
}

function AgentRoster({ statuses }: { statuses: StatusMap }) {
  return (
    <Paper style={{ padding: "20px 22px" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 12,
        }}
      >
        <Eyebrow>§ 04 · Agent roster</Eyebrow>
        <span
          className="mono"
          style={{ fontSize: 10, color: "var(--muted)", letterSpacing: ".1em" }}
        >
          ● completed &nbsp; ● running &nbsp; ○ pending
        </span>
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(2, 1fr)",
          gap: 6,
        }}
      >
        {AGENTS.map((a, i) => {
          const s = statusFor(statuses, a.key);
          const m = MOCK_METRICS[a.key];
          const isRunning = isRunningLike(s);
          const isDone = isCompletedLike(s);
          const colors = nodeColors(s);
          return (
            <div
              key={a.key}
              className="reveal"
              style={{
                animationDelay: `${i * 0.04}s`,
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "9px 12px",
                background:
                  isRunning || s === "failed"
                    ? colors.background
                    : "transparent",
                border: `1px solid ${isRunning || s === "failed" ? colors.border : "transparent"}`,
                borderRadius: 3,
                position: "relative",
                overflow: "hidden",
              }}
            >
              {isRunning && <div className="scan-beam" />}
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  background:
                    isDone || isRunning || s === "failed"
                      ? colors.dot
                      : "transparent",
                  border: `1.5px solid ${colors.dot}`,
                  animation: isRunning
                    ? "pulse-ring-amber 1.5s ease-out infinite"
                    : "none",
                  flexShrink: 0,
                }}
              />
              <span
                className="mono"
                style={{
                  fontSize: 9.5,
                  color: "var(--muted)",
                  letterSpacing: ".1em",
                  textTransform: "uppercase",
                  minWidth: 24,
                }}
              >
                {String(i + 1).padStart(2, "0")}
              </span>
              <span
                style={{
                  fontSize: 12.5,
                  color: colors.text,
                  fontWeight: isRunning ? 600 : 500,
                  flex: 1,
                }}
              >
                {a.label}
              </span>
              {(isDone || isRunning) && m.tokens > 0 && (
                <span
                  className="mono"
                  style={{ fontSize: 10, color: "var(--muted)" }}
                >
                  {m.tokens.toLocaleString()}
                  <span style={{ opacity: 0.6 }}>t</span>
                </span>
              )}
              {(isDone || isRunning) && (
                <span
                  className="mono"
                  style={{
                    fontSize: 10,
                    color: isRunning ? colors.text : "var(--muted)",
                    minWidth: 36,
                    textAlign: "right",
                  }}
                >
                  {m.elapsed}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </Paper>
  );
}

export function LoadingState({
  progress,
  statuses,
  tickerLines,
  degradedRoles,
}: {
  progress: number;
  statuses: StatusMap;
  tickerLines: string[];
  degradedRoles?: Set<string>;
}) {
  const degradedLabels = degradedRoles
    ? [...degradedRoles].map((role) => AGENT_LABELS.get(role) || role)
    : [];

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 14,
        marginBottom: 24,
      }}
    >
      {degradedRoles && degradedRoles.size > 0 && (
        <div
          role="status"
          aria-live="polite"
          aria-atomic="true"
          style={{
            padding: "8px 14px",
            background: "#fffbe6",
            border: "1px solid #ffe58f",
            borderRadius: 4,
            fontSize: 12,
            color: "#7c5f00",
          }}
        >
          ⚡ Degraded mode active for: {degradedLabels.join(", ")}
        </div>
      )}
      <div className="reveal reveal-1">
        <BigProgress pct={progress} statuses={statuses} />
      </div>
      <div className="reveal reveal-2">
        <PipelineFlow statuses={statuses} />
      </div>
      <div
        className="reveal reveal-3"
        style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}
      >
        <LiveTicker tickerLines={tickerLines} />
        <AgentRoster statuses={statuses} />
      </div>
    </div>
  );
}
