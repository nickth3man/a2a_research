# Assets

This directory holds static image and logo assets consumed by the React frontend. Vite bundles and hashes them automatically during production builds.

## Files

### `hero.png`

A decorative 3D illustration of layered rounded squares rendered in isometric perspective. The visible faces carry a purple gradient against a transparent background. This image is intended for prominent display near the top of the landing page or main view.

**Technical notes:**
- PNG format with alpha transparency
- Recommended use case: hero sections, feature banners

### `react.svg`

The official React logo. A blue atom-like emblem made of elliptical orbits around a central nucleus. This file is typically referenced by Vite's default starter template and can be used in documentation links, footer credits, or technology stack lists.

**Technical notes:**
- SVG, scalable without quality loss
- Inline styles and presentational attributes included

### `vite.svg`

The official Vite logo. A stylized purple lightning bolt mark with gradient glow effects and dark/light mode aware parenthesis shapes. Like `react.svg`, it often appears in template-generated markup and can be shown in stack lists or footer credits.

**Technical notes:**
- SVG with embedded `<title>` and `prefers-color-scheme` media query
- Includes filter effects for glow

## Usage

Import assets directly in TypeScript or TSX files. Vite resolves the path and handles cache busting.

```tsx
import heroImage from "../assets/hero.png";

function HeroSection() {
  return (
    <section>
      <img src={heroImage} alt="A2A research pipeline graphic" />
    </section>
  );
}
```

For SVGs, you can import them as React components if a suitable Vite plugin is configured. Otherwise, treat them as static URLs.

```tsx
import viteLogo from "../assets/vite.svg";

<img src={viteLogo} alt="Vite" />
```

## Conventions

- Prefer SVG for logos, icons, and simple illustrations. It keeps bundle size small and scales cleanly.
- Optimize PNGs and JPEGs before committing. Use tools like `oxipng` or an image compressor to reduce file size.
- Use lowercase kebab-case for filenames. For example, `hero-banner.png` rather than `heroBanner.png`.
- Include descriptive `alt` text when rendering images in JSX.
- Do not commit unused assets. Remove files that are no longer referenced to keep the repository lean.
