export function Logo() {
  return (
    <svg
      width="36"
      height="36"
      viewBox="0 0 36 36"
      fill="none"
      style={{ display: "block" }}
    >
      <rect x="0.5" y="0.5" width="35" height="35" rx="4" fill="var(--ink)" />
      <circle
        cx="18"
        cy="18"
        r="5.5"
        stroke="#fff"
        strokeWidth="1"
        fill="none"
        opacity=".3"
      />
      <circle
        cx="18"
        cy="18"
        r="9.5"
        stroke="#fff"
        strokeWidth="0.6"
        fill="none"
        opacity=".2"
        strokeDasharray="1.5 3"
      />
      <circle cx="18" cy="8.5" r="1.9" fill="var(--accent)">
        <animateTransform
          attributeName="transform"
          type="rotate"
          from="0 18 18"
          to="360 18 18"
          dur="6s"
          repeatCount="indefinite"
        />
      </circle>
      <circle cx="27.5" cy="18" r="1.4" fill="#fff" opacity=".85">
        <animateTransform
          attributeName="transform"
          type="rotate"
          from="120 18 18"
          to="480 18 18"
          dur="8s"
          repeatCount="indefinite"
        />
      </circle>
      <circle cx="8.5" cy="18" r="1.4" fill="#fff" opacity=".85">
        <animateTransform
          attributeName="transform"
          type="rotate"
          from="240 18 18"
          to="600 18 18"
          dur="7s"
          repeatCount="indefinite"
        />
      </circle>
      <circle cx="18" cy="18" r="1.6" fill="#fff" />
    </svg>
  );
}
