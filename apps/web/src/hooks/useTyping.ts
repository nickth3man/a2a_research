import { useState, useEffect } from "react";

export function useTyping(text: string, speed = 22, startDelay = 0) {
  const [shown, setShown] = useState("");

  useEffect(() => {
    let i = 0;
    let id: ReturnType<typeof setInterval>;

    const t = setTimeout(() => {
      id = setInterval(() => {
        i++;
        setShown(text.slice(0, i));
        if (i >= text.length) clearInterval(id);
      }, speed);
    }, startDelay);

    return () => {
      clearTimeout(t);
      clearInterval(id);
    };
  }, [text, speed, startDelay]);

  return shown;
}
