# src/

Main React application source directory for the frontend.

## Purpose

This directory contains the application entry points, root component, styles, and UI modules used by the Vite app.

## Entry Points

### `main.tsx`
Bootstraps React and mounts the app into the DOM element with `id="root"`.

It also imports the global stylesheet:

- `./styles/globals.css`

### `App.tsx`
Root application component. It imports the main UI pieces and manages the top-level UI state.

## Current Source Structure

From the files currently present:

- `main.tsx` - React bootstrap and render root
- `App.tsx` - Root UI composition
- `components/` - UI components used by the app
- `types/` - Shared TypeScript types
- `styles/` - Global CSS files

## Observed App Behavior

`App.tsx` currently:

- imports UI components such as:
  - `Masthead`
  - `StateNav`
  - `QueryInput`
  - `HowItWorks`
  - `EmptyState`
  - `LoadingState`
  - `ResultsState`
- stores the current UI state in `localStorage` under `a2a_ui_state`
- simulates loading progress before transitioning to results
- renders the main content area and footer-like status text

## Conventions

- React components are organized into feature-focused files under `components/`
- Shared TypeScript types live under `types/`
- Global styling lives under `styles/`
- Entry files stay small and focused on bootstrapping/rendering

## Notes

- This source tree is the application layer only.
- Backend communication is handled through the frontend's `/api` requests, which are proxied to `http://localhost:8000` during development.
