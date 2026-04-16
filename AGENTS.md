# AGENTS.md

When you are unsure how to do something or need external documentation, use the following tools.
Prioritize local codebase knowledge when available. Reach for external tools only when the answer is not in the repo.

## GitHub examples & repo docs

- **`searchGitHub`** — Search for real-world code patterns across public GitHub repositories. Best for finding production usage examples of unfamiliar APIs, frameworks, or libraries.
- **`read_wiki_structure`** — List the documentation topics and structure of a GitHub repository. Use this to quickly map what docs are available before reading them.
- **`read_wiki_contents`** — Read the full content of a specific documentation topic from a GitHub repository. Use after `read_wiki_structure` to pull the relevant guide.
- **`ask_question`** — Ask an AI-powered, context-grounded question about a GitHub repository. Useful when you need a synthesized answer instead of scrolling through raw code or docs.

## Web search & extraction

- **`tavily-search`** — Run a broad web search with AI-generated summaries and citations. Best for current best practices, framework changelogs, troubleshooting errors, or verifying facts.
- **`tavily-crawl`** — Start a structured crawl from a base URL and follow internal links. Use for deep documentation dives, blog series, or multi-page guides.
- **`tavily-map`** — Discover and list the URL structure of a website. Use this before crawling to identify the most relevant pages.
- **`tavily-extract`** — Fetch and parse raw content from one or more specific URLs. Use when you already know the exact page(s) you need.