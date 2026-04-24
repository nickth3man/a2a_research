import { useState, useEffect } from "react";

export function useCountUp(
  target: number,
  duration = 900,
  deps: React.DependencyList = [],
) {
  const [n, setN] = useState(0);

  useEffect(() => {
    let raf: number;
    let start: number | null = null;

    const step = (t: number) => {
      if (!start) start = t;
      const p = Math.min(1, (t - start) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setN(Math.round(target * eased));
      if (p < 1) raf = requestAnimationFrame(step);
    };

    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return n;
}
