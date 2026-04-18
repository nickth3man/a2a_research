# AGENTS.md

## Shell and command syntax (Windows)

**Use [Git Bash](https://git-scm.com/) (the Bash that ships with Git for Windows) when proposing or running terminal commands in this repo.**

- Prefer **POSIX / Bash** syntax: `cp`, `mv`, `rm`, `mkdir -p`, `export VAR=value`, `command && other`, here-strings, `/c/Users/...` or `c:/Users/...` style paths when a full path is needed.
- **Do not** default to **PowerShell** (`Copy-Item`, `Remove-Item`, `$env:VAR`) or **cmd.exe** (`dir`, `set VAR=`, `%VAR%`) unless the user explicitly asks for that shell.
- `make` targets in this project assume a **Unix-like** environment; Git Bash provides `make`, `awk`, and a usable `PATH` for `uv` and Python. If `make` is missing, run the equivalent `uv` commands from the Makefile verbatim in the same Git Bash session.

### Quick translation table

| Task | Git Bash (use this) | Avoid as default |
|------|---------------------|-------------------|
| Copy env template | `cp .env.example .env` | `Copy-Item .env.example .env` |
| Set env for one command | `export FOO=bar && make test` | `$env:FOO = "bar"; …` (then run the equivalent target) |
| Remove directory | `rm -rf dirname` | `Remove-Item -Recurse` |
| List files | `ls` or `find . -maxdepth 1` | `dir`, `Get-ChildItem` |

---

## Project overview

HTTP-orchestrated multi-agent research pipeline (`a2a_research`): planner, search, read, fact-check, synthesize, with Mesop UI. See `README.md` for architecture and ports.

---

## Repository structure (high level)

- **`src/a2a_research/`** — application code (agents, A2A client, tools, UI, workflow).
- **`tests/`** — pytest suite.
- **`Makefile`** — primary developer commands (`make help`).
- **`pyproject.toml`** — dependencies, Ruff, pytest, mypy/pyright.

---

## Tech stack

- **Language:** Python `>=3.11` (see `pyproject.toml` `requires-python`).
- **Package manager:** `uv` (lockfile: `uv.lock`).
- **Lint / format:** Ruff (`pyproject.toml` `[tool.ruff]`).
- **Tests:** pytest (`pyproject.toml` `[tool.pytest.ini_options]`).

---

## Build and development commands

Run in **Git Bash**. **Authoritative recipes for install, tests, lint, format, typecheck, services, and UI are in `Makefile` — do not copy their underlying `uv` invocations here.** Use:

```bash
make help
```

Common targets (see `Makefile` for exact definitions): `install`, `dev`, `test`, `watch`, `lint`, `format`, `format-check`, `typecheck`, `typecheck-ty`, `check`, `all`, `clean`, `mesop`, `serve-all`, `serve-planner`, `serve-searcher`, `serve-reader`, `serve-fact-checker`, `serve-synthesizer`, `htmlcov`.

### Not duplicated in the Makefile

CI also runs **`uv lock --check`** (`.github/workflows/ci.yml`) to verify `uv.lock`; use that when you need the same check locally. CI’s pytest step adds **`--cov-report=xml`** for coverage upload — see the workflow file if you need to match CI exactly.

---

## Agent guardrails

### Do

- Assume the developer is on **Windows** and uses **Git Bash** for copy-paste commands.
- Prefer **`make <target>`** when `Makefile` defines it; use raw **`uv …`** only for steps that exist in CI but have no `make` target (e.g. lockfile check above), or when `make` is unavailable and you are copying a recipe from `Makefile` verbatim.

### Do not

- Do not sprinkle PowerShell-only snippets without labeling them as PowerShell and offering a Git Bash equivalent.
- Do not commit secrets; use `.env` (from `.env.example`) locally.

### Ask before

- Deleting large directories, changing CI, or pushing commits (unless the user asked).

---

## Unknowns and TODOs

- If a command fails only in Git Bash, confirm `PATH` includes the `uv` shims and that `make` is available (e.g. via Git for Windows / optional packages).

---

## Further reading

- `README.md` — quick start, ports, configuration.
- `Makefile` — full list of targets (`make help`).
