# src

Source code root. Contains the main Python package `a2a_research/`.

## Structure

```
src/
└── a2a_research/
    ├── backend/        # Core backend logic
    │   ├── agents/     # Agent implementations
    │   ├── core/       # Core models and utilities
    │   ├── entrypoints/# Application entry points
    │   ├── llm/        # LLM provider integrations
    │   ├── tools/      # External tool integrations
    │   └── workflow/   # Workflow orchestration
    └── ui/             # Mesop-based user interface
        ├── components/ # Reusable UI components
        └── ...         # Pages, handlers, theming
```

## Key Directories

### `a2a_research/backend/`
The heart of the application. Contains agent implementations using different frameworks (PocketFlow, LangGraph, Pydantic AI, smolagents), core data models, LLM integrations, and workflow orchestration.

### `a2a_research/ui/`
The Mesop-based web interface. Provides a visual frontend for interacting with the research pipeline.

## Conventions

- All Python code targets Python 3.11+
- Type hints are required (enforced by mypy in strict mode)
- Import from `a2a_research` using absolute imports
- The package is marked with `py.typed` for PEP 561 compliance
