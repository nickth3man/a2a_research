"""Private facade imports for ``core`` — imported by ``core.__init__``.

Import order matters: leaf modules (no internal deps) first, then modules
that depend on them, to avoid circular-import errors.

Symbols needed by circular imports (e.g. ``new_task`` for
``core.a2a.request_task``) are pre-imported in ``core.__init__``.
"""

from __future__ import annotations

# 1. Settings / 16. A2A card specs — depends on AgentRole
# 17. A2A cards — depends on CARD_SPECS, settings, make_agent_card, make_skill
# 19. A2A client — depends on registry, logging, settings
# 15. A2A proto — leaf module, no core deps (new_task in __init__)
# 18. A2A registry — depends on AgentRole, get_card, settings
# 20. A2A request_task — depends on proto (new_task pre-imported in __init__)
# 5. Logging — settings already imported above
# 7. Claims — depends on enums (ReplanReasonCode, Verdict)
# 2. Enums — pure stdlib, no internal deps
# 9. Errors — depends on enums (AgentRole)
# 6. Evidence / Reports models — pure pydantic, no core deps
# 12. FactChecker output — depends on verification, workflow, enums
# 8. Provenance — depends on enums (ProvenanceEdgeType)
# 13. Session — depends on many models above
# 10. Verification — depends on enums (Verdict), claims
# 11. Workflow models — depends on enums
# 14. Progress — relative imports internally
from core.settings import (
    _validate_dotenv_keys,  # noqa: F401
)

# 4. Telemetry — only depends on logfire
# 3. Utility leaves — pure stdlib / json
