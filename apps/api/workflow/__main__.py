"""CLI entry: ``python -m a2a_research.workflow "query"``.

Prints the final markdown report to stdout and a short per-agent summary to
stderr.
"""

from __future__ import annotations

import sys

from workflow import run_research_sync


def main() -> None:
    if len(sys.argv) < 2:
        print(
            'Usage: python -m a2a_research.workflow "your research query"',
            file=sys.stderr,
        )
        sys.exit(2)
    query = " ".join(sys.argv[1:]).strip()
    if not query:
        print("Empty query.", file=sys.stderr)
        sys.exit(2)

    session = run_research_sync(query)

    if session.error:
        print(f"[workflow error] {session.error}", file=sys.stderr)
    for role, result in session.agent_results.items():
        print(
            f"[{role.value}] {result.status.value}: {result.message}",
            file=sys.stderr,
        )
    print(session.final_report or "(no report produced)")


if __name__ == "__main__":
    main()
