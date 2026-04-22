# hooks/

Custom React hooks used across the application for animations, timers, and reusable UI behavior.

## Hooks

### `useCountUp`

**File:** `useCountUp.ts`

Animates a numeric value counting up from zero to a target number over a specified duration. Uses `requestAnimationFrame` with cubic easing for smooth motion.

**Signature:**
```ts
function useCountUp(
  target: number,
  duration?: number,
  deps?: React.DependencyList
): number
```

**Parameters:**
- `target` — The final number to count up to.
- `duration` — Animation length in milliseconds. Defaults to `900`.
- `deps` — Optional dependency array that restarts the animation when changed. Defaults to an empty array.

**Returns:** The current animated value as a number.

**Example:**
```tsx
import { useCountUp } from "./useCountUp";

function StatCard({ value }: { value: number }) {
  const animated = useCountUp(value, 1000);
  return <span>{animated}</span>;
}
```

---

### `useTicker`

**File:** `useTicker.ts`

Cycles through an array of strings on a fixed interval, returning the most recent items as a stacked list. Newest entries appear first, and the list is capped to the original array length.

**Signature:**
```ts
function useTicker(
  lines: string[],
  interval?: number,
  active?: boolean
): string[]
```

**Parameters:**
- `lines` — Array of strings to rotate through.
- `interval` — Time between updates in milliseconds. Defaults to `1100`.
- `active` — Whether the ticker is running. Defaults to `true`.

**Returns:** An array of visible lines ordered newest to oldest.

**Example:**
```tsx
import { useTicker } from "./useTicker";

function StatusLog() {
  const visible = useTicker(["Loading...", "Fetching...", "Done"], 1000);
  return (
    <ul>
      {visible.map((line, i) => <li key={i}>{line}</li>)}
    </ul>
  );
}
```

---

### `useTyping`

**File:** `useTyping.ts`

Simulates a typing animation by revealing text one character at a time.

**Signature:**
```ts
function useTyping(
  text: string,
  speed?: number,
  startDelay?: number
): string
```

**Parameters:**
- `text` — The full string to type out.
- `speed` — Delay between characters in milliseconds. Defaults to `22`.
- `startDelay` — Optional wait in milliseconds before typing begins. Defaults to `0`.

**Returns:** The portion of the text revealed so far.

**Example:**
```tsx
import { useTyping } from "./useTyping";

function Typewriter({ message }: { message: string }) {
  const displayed = useTyping(message, 30, 500);
  return <p>{displayed}</p>;
}
```

## Conventions

- Hooks are camelCase and prefixed with `use`.
- Side effects live inside `useEffect` and always clean up on unmount.
- Where appropriate, accept refs or return memoized values to avoid unnecessary re-renders.
