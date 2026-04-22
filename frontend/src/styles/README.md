# styles/

Global CSS files that apply across the entire application.

## Files

| File | Description |
|------|-------------|
| `globals.css` | Global CSS rules: CSS variables, resets, utility classes, animations, and base element styles |

## Design Tokens

The stylesheet defines CSS custom properties for a warm, editorial color palette built around ivory paper tones with a vivid blue accent.

### Background & Surface Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--ivory` | `#faf8f3` | Primary page background |
| `--ivory-2` | `#f3efe6` | Secondary surface, kbd backgrounds |
| `--paper` | `#ffffff` | Card and panel backgrounds |

### Text Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--ink` | `#0a0a0a` | Primary body text |
| `--ink-2` | `#1a1a1a` | Headings |
| `--ink-soft` | `#3a3a38` | Secondary labels |
| `--muted` | `#7a766d` | Captions, eyebrow text |
| `--muted-2` | `#a8a498` | Placeholders, hover states |

### Border & Rule Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--rule` | `#e8e3d6` | Borders, dividers |
| `--rule-soft` | `#efeae0` | Subtle separators |

### Accent Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--accent` | `#1e40ff` | Primary interactive accent |
| `--accent-2` | `#3b5cff` | Hover accent |
| `--accent-soft` | `#e8ecff` | Light tint backgrounds |
| `--amber` | `#b8720a` | Warning, pending states |
| `--amber-soft` | `#fcf3e2` | Warning tint backgrounds |
| `--emerald` | `#0a6b3d` | Success, verified states |
| `--emerald-soft` | `#e7f4ec` | Success tint backgrounds |
| `--crimson` | `#a3201c` | Error, failed states |
| `--crimson-soft` | `#fbe8e6` | Error tint backgrounds |

## Base Styles

### Reset & Box Sizing

All elements use `border-box` sizing with zeroed margins and padding.

```css
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
```

### Root Font Size

The base font size is set to `15px` for easier rem calculations.

```css
html { font-size: 15px; }
```

### Body

- Font family: `Inter` with `system-ui` fallback
- Background: warm ivory tone
- Antialiased font rendering with OpenType features (`ss01`, `cv11`)
- Subtle fixed gradient overlays and a grain texture are applied via `::before` and `::after` pseudo-elements
- The `#root` container sits above the decorative overlays (`z-index: 2`)

### Scrollbar

WebKit scrollbars are styled globally with a thin 8px track:

- Track: transparent
- Thumb: `--rule` on idle, `--muted-2` on hover
- Both horizontal and vertical scrollbars affected

## Typography Utility Classes

| Class | Description |
|-------|-------------|
| `.serif` | `Instrument Serif` with slight negative letter-spacing |
| `.mono` | `JetBrains Mono` monospace |
| `.eyebrow` | Monospace label style: 10px uppercase with wide letter-spacing (`0.18em`), muted color |

## Interactive Component Utilities

| Class | Behavior |
|-------|----------|
| `.link-hover` | Underline slides in from right on hover, exits to left |
| `.chip` | Slight lift (`translateY(-1px)`) on hover with shadow transition |
| `.btn-primary` | Shimmer sweep animation on hover, lift + blue shadow on hover, press down on active |
| `.scan-beam` | Animated horizontal light beam sweeping across the element |
| `.ants` | Marching ants border using `dash-flow` animation |
| `.caret` | Blinking cursor (`▍`) in accent color, animated with the `caret` keyframe |

### Keyboard Styling

`<kbd>` elements are styled with a subtle inset look: ivory background, border with thicker bottom edge, and monospace font.

## Animation Keyframes

| Name | Duration | Description |
|------|----------|-------------|
| `slide-up` | 0.3s ease | Fade + translate up into view |
| `fade-in` | (inline) | Opacity 0 to 1 |
| `reveal` | 0.55s cubic-bezier | Fade, translate up, and deblur |
| `pulse-glow` | (inline) | Expanding blue ring shadow |
| `pulse-ring-amber` | (inline) | Expanding amber ring shadow |
| `dash-flow` | 1.2s linear infinite | Scrolls background gradient for marching ants |
| `beam-sweep` | 2.8s linear infinite | Moves a light gradient across the element |
| `blink` | (inline) | 50% opacity toggle |
| `ticker-in` | (inline) | Slide up fade for ticker items |
| `spin` | (inline) | 360 degree rotation |
| `progress-stripes` | (inline) | Moving diagonal stripe background |
| `draw-line` | (inline) | SVG stroke draw-on effect |
| `orbit-particle` | (inline) | Particle opacity along a motion path |
| `number-flip` | (inline) | Vertical flip transition for numbers |
| `caret` | 1s step-end infinite | Cursor blink |

### Reveal Delay Modifiers

Add staggered entrance delays to `.reveal` elements:

| Class | Delay |
|-------|-------|
| `.reveal-1` | 0.05s |
| `.reveal-2` | 0.12s |
| `.reveal-3` | 0.20s |
| `.reveal-4` | 0.28s |
| `.reveal-5` | 0.36s |
| `.reveal-6` | 0.44s |

## Tweaks Panel

The stylesheet includes styles for `#tweaks-panel`, a fixed-position debug/settings panel that appears in the bottom-right corner when toggled with the `.open` class. It uses monospace labels and small controls.

## Scope

Use this directory for styles that need to be globally available, such as:

- CSS custom properties (design tokens)
- `@font-face` declarations
- Global scrollbar or selection styling
- Base element resets
- Cross-cutting animation keyframes
- Reusable utility classes used by multiple components

Component-specific styles should live next to their component (e.g., `App.css` beside `App.tsx`) rather than here.

## Conventions

- Colors are defined as semantic tokens, not raw values, to keep the palette consistent across components.
- Animations are defined once as keyframes and referenced by utility classes.
- Pseudo-element overlays on `body` provide global texture and depth without touching component markup.
