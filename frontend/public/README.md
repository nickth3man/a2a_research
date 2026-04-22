# public/

Static assets in this directory are served by Vite without being processed by the build pipeline.

## Purpose

Use this folder for files that should be available at fixed URLs at runtime, such as:

- icons
- images
- favicons
- other static files

## Current Usage

The existing frontend HTML references:

- `/favicon.svg` in `index.html`

So the favicon is expected to live in this directory and be served directly by Vite.

## How These Assets Are Used

Files in `public/` are copied as-is into the production build and can be referenced with root-relative paths like:

```html
<link rel="icon" href="/favicon.svg" />
```

## Notes

- Do not place generated build output here.
- Do not place dependencies here.
- Keep only static files that should be publicly accessible.
