# Utils

Small, focused helpers used across the backend. Each module has zero or minimal internal dependencies so it can be imported from anywhere in the package without risking circular imports.

## Modules

### `citation_sanitize.py`

Guards the Synthesizer output against hallucinated citations. Structured models do not validate that URLs are real, so this module enforces an allowlist built from actual pipeline sources.

**Key functions:**

- `normalize_url(url: str) -> str` — Strip trailing slashes, lowercase the host, and drop `www.` so URLs can be compared reliably.
- `allowed_urls_from_evidence(sources, claims) -> frozenset[str]` — Collect every URL that appeared in verified `WebSource` rows and in `Claim.sources`.
- `sanitize_report_output(report, sources, claims) -> ReportOutput` — Drop any citation whose URL is not on the allowlist, and strip untrusted markdown links (`[label](url)`) from prose, leaving just the label text.

### `json_utils.py`

Low-level JSON parsing with no internal dependencies. Both provider code and agent helpers can import it safely.

**Key functions:**

- `parse_json_safely(content: str) -> dict[str, Any]` — Extract a JSON object from raw text. Handles fenced code blocks, bare objects, and prose that wraps JSON. Returns `{}` if nothing valid is found.

### `timing.py`

Thin wrapper around the standard library performance counter.

**Key functions:**

- `perf_counter() -> float` — Returns fractional seconds from `time.perf_counter()`.

### `validation.py`

Small coercion helpers for untyped or external data.

**Key functions:**

- `to_str_list(value: Any) -> list[str]` — Turn a list into a list of strings, skipping `None` items. Returns `[]` for non-list input.
- `to_float(value: Any, default: float) -> float` — Convert a value to float, falling back to `default` on `ValueError` or `TypeError`.

## Package Exports

`__init__.py` re-exports the most commonly used helpers so callers can import them directly from `a2a_research.backend.core.utils`:

- `perf_counter`
- `to_float`
- `to_str_list`

## Design Notes

- Keep dependencies minimal. `json_utils` and `timing` have no internal imports.
- `citation_sanitize` depends on `core.models` and `core.logging`, but only because it operates on domain objects.
- These are pure functions or thin wrappers. No state, no side effects, no I/O.
