import { useState, useEffect } from "react";

export function useTicker(lines: string[], interval = 1100, active = true) {
  const [visible, setVisible] = useState<string[]>(lines.slice(0, 1));

  useEffect(() => {
    if (!active) return;
    let i = 1;
    const id = setInterval(() => {
      setVisible((v) => {
        const next = [lines[i % lines.length], ...v].slice(0, lines.length);
        return next;
      });
      i++;
    }, interval);
    return () => clearInterval(id);
  }, [active, interval, lines]);

  return visible;
}
