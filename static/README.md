# static

Static web assets served by the application.

## Files

| File       | Purpose                                              |
| ---------- | ---------------------------------------------------- |
| `robots.txt` | Crawler directives for search engines and other bots |

## What this directory contains

This directory is reserved for files that should be served directly, without code processing or transformation. Assets placed here are intended to be accessible at the web root.

Current contents are minimal:

- `robots.txt` — allows all crawlers to access the site

## Serving behavior

Files in this directory are served as-is from the site root. That makes this directory suitable for:

- `robots.txt`
- favicons and other small site assets
- simple static HTML files
- other files that must be reachable directly by URL

## Operational / deployment relevance

- `robots.txt` affects how search engines and other crawlers index the site.
- Because files are served directly, anything placed here becomes public-facing if the application exposes this directory.
- Keep this directory minimal and deliberate; large or application-specific frontend assets should live in `frontend/public/` instead.

## Notes

- No build step or transformation is applied to files in this directory.
- If you add new files here, document them here so deployment and SEO behavior stays clear.
