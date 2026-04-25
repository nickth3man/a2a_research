import type { CSSProperties, ReactNode } from "react";

interface RuleProps {
  label?: string;
  style?: CSSProperties;
}

export function Rule({ label, style }: RuleProps) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, ...style }}>
      {label && <span className="eyebrow">{label}</span>}
      <div style={{ flex: 1, height: 1, background: "var(--rule)" }} />
    </div>
  );
}

interface EyebrowProps {
  children: ReactNode;
  dot?: boolean;
  color?: string;
}

export function Eyebrow({
  children,
  dot,
  color = "var(--accent)",
}: EyebrowProps) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      {dot && (
        <span
          style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: color,
            boxShadow: `0 0 0 3px ${color}22`,
          }}
        />
      )}
      <span className="eyebrow">{children}</span>
    </div>
  );
}

interface PaperProps {
  children: ReactNode;
  style?: CSSProperties;
  className?: string;
}

export function Paper({ children, style = {}, className = "" }: PaperProps) {
  return (
    <div
      className={className}
      style={{
        background: "var(--paper)",
        border: "1px solid var(--rule)",
        borderRadius: 4,
        boxShadow:
          "0 1px 0 rgba(10,10,10,0.02), 0 10px 30px -20px rgba(10,10,10,0.12)",
        ...style,
      }}
    >
      {children}
    </div>
  );
}
