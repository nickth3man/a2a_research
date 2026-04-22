# Frontend

React + TypeScript + Vite frontend for the A2A research and verification pipeline.

## Purpose

This directory contains the browser UI for the project. The app is built with React and Vite, and it is designed to work alongside the Python backend services that power the agent pipeline.

During development, the Vite dev server proxies requests from `/api` to the backend at `http://localhost:8000`, so the frontend can talk to backend services without CORS setup in the browser.

## Quick Start

From the `frontend/` directory:

```bash
npm install
npm run dev
```

Or with pnpm:

```bash
pnpm install
pnpm dev
```

## Available Scripts

Defined in `package.json`:

- `npm run dev` / `pnpm dev` - Start the Vite development server
- `npm run build` / `pnpm build` - Type-check and build the production bundle
- `npm run preview` / `pnpm preview` - Preview the production build locally
- `npm run lint` / `pnpm lint` - Run ESLint

## Build and Development

The app uses:

- React 19
- TypeScript
- Vite
- ESLint

The production build runs TypeScript compilation first and then bundles with Vite.

## Backend Integration

The frontend is configured to proxy `/api` requests to:

- `http://localhost:8000`

This means frontend code can call backend endpoints with paths like `/api/...`, and Vite forwards those requests to the local backend service during development.

## Key Files

| File | Purpose |
|------|---------|
| `package.json` | Scripts and dependencies |
| `vite.config.ts` | Vite configuration and `/api` proxy |
| `index.html` | HTML entry point and app shell |
| `src/main.tsx` | React bootstrap entry point |
| `src/App.tsx` | Root application component |

## Directory Layout

```text
frontend/
├── public/    # Static assets served as-is
└── src/       # React application source code
```

## Notes

- `node_modules/` and `dist/` are generated or installed artifacts and are not part of the source layout.
- The frontend is intended to be run together with the Python backend agent services for full functionality.
