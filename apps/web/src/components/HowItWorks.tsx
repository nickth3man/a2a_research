import { Rule } from "./Primitives";

export function HowItWorks() {
  const steps = [
    { n: "I", k: "Query", d: "State your research question." },
    { n: "II", k: "Retrieve", d: "Pull candidate passages from the corpus." },
    { n: "III", k: "Verify", d: "Cross-check claims against sources." },
    { n: "IV", k: "Synthesize", d: "Return a cited, structured report." },
  ];

  return (
    <div className="reveal reveal-1" style={{ marginBottom: 28 }}>
      <Rule label="§ how it works" />
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4,1fr)",
          gap: 0,
          marginTop: 20,
        }}
      >
        {steps.map((s, i) => (
          <div
            key={s.n}
            className="reveal"
            style={{
              animationDelay: `${0.15 + i * 0.08}s`,
              padding: "4px 24px 4px 0",
              borderRight: i < 3 ? "1px solid var(--rule)" : "none",
              marginRight: i < 3 ? 24 : 0,
            }}
          >
            <div
              className="serif"
              style={{
                fontSize: 34,
                lineHeight: 1,
                color: "var(--accent)",
                fontStyle: "italic",
                marginBottom: 10,
              }}
            >
              {s.n}.
            </div>
            <div
              style={{
                fontSize: 13.5,
                fontWeight: 600,
                color: "var(--ink)",
                marginBottom: 4,
              }}
            >
              {s.k}
            </div>
            <div
              style={{
                fontSize: 12.5,
                color: "var(--muted)",
                lineHeight: 1.55,
              }}
            >
              {s.d}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
