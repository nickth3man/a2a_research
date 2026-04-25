"""Private facade imports for ``core`` — imported by ``core.__init__``.

Import order matters: leaf modules (no internal deps) first, then modules
that depend on them, to avoid circular-import errors.

Symbols needed by circular imports (e.g. ``new_task`` for
``core.a2a.request_task``) are pre-imported in ``core.__init__``.
"""

from __future__ import annotations

# 1. Settings / 16. A2A card specs — depends on AgentRole
from core.a2a.card_specs import CARD_SPECS  # noqa: E402

# 17. A2A cards — depends on CARD_SPECS, settings, make_agent_card, make_skill
from core.a2a.cards import (  # noqa: E402
    AGENT_CARDS,
    build_cards,
    get_card,
)

# 19. A2A client — depends on registry, logging, settings
from core.a2a.client import A2AClient  # noqa: E402
from core.a2a.client_helpers import (  # noqa: E402
    build_message,
    extract_data_payload_or_warn,
    extract_data_payloads,
    extract_text,
)
from core.a2a.compat import (  # noqa: E402
    build_http_app,
    make_agent_card,
    make_skill,
)

# 18. A2A registry — depends on AgentRole, get_card, settings
from core.a2a.registry import (  # noqa: E402
    AgentRegistry,
    get_registry,
    reset_registry,
)

# 15. A2A proto — leaf module, no core deps (new_task in __init__)
from core.a2a.proto import (  # noqa: E402
    get_data_part,
    get_text_part,
    make_data_part,
    make_message,
    make_text_message,
    make_text_part,
    new_agent_text_message,
)

# 20. A2A request_task — depends on proto (new_task pre-imported in __init__)
from core.a2a.request_task import initial_task_or_new  # noqa: E402

# 5. Logging — settings already imported above
from core.logging.app_logging import (  # noqa: E402
    get_logger,
    log_event,
    setup_logging,
)
from core.logging.logging_streams import StreamToLogger  # noqa: E402

# 2. Enums — pure stdlib, no internal deps
from core.models.enums import (  # noqa: E402
    AgentCapability,
    AgentRole,
    AgentStatus,
    ProvenanceEdgeType,
    ReplanReasonCode,
    TaskStatus,
    Verdict,
)

# 9. Errors — depends on enums (AgentRole)
from core.models.errors import (  # noqa: E402
    ErrorCode,
    ErrorEnvelope,
    ErrorSeverity,
)

# 7. Claims — depends on enums (ReplanReasonCode, Verdict)
from core.models.claims import (  # noqa: E402
    Claim,
    ClaimDAG,
    ClaimDependency,
    ClaimFollowUp,
    FreshnessWindow,
    ReplanReason,
)

# 6. Evidence / Reports models — pure pydantic, no core deps
from core.models.evidence import (  # noqa: E402
    CredibilitySignals,
    EvidenceUnit,
    IndependenceGraph,
    Passage,
)

# 12. FactChecker output — depends on verification, workflow, enums
from core.models.fact_checker import FactCheckerOutput  # noqa: E402

# 8. Provenance — depends on enums (ProvenanceEdgeType)
from core.models.provenance import (  # noqa: E402
    ProvenanceEdge,
    ProvenanceNode,
    ProvenanceTree,
)
from core.models.reports import (  # noqa: E402
    Citation,
    ReportOutput,
    ReportSection,
    WebSource,
)

# 13. Session — depends on many models above
from core.models.session import (  # noqa: E402
    AgentResult,
    ResearchSession,
    workflow_roles,
)

# 10. Verification — depends on enums (Verdict), claims
from core.models.verification import (  # noqa: E402
    ClaimState,
    ClaimVerification,
    VerificationRevision,
)

# 11. Workflow models — depends on enums
from core.models.workflow import (  # noqa: E402
    AgentDefinition,
    BudgetConsumption,
    CircuitBreakerConfig,
    NoveltyTracker,
    RetryPolicy,
    WorkflowBudget,
)

# 14. Progress — relative imports internally
from core.progress import (  # noqa: E402
    PROMPT_DETAIL_MAX_CHARS,
    Bus,
    ProgressEvent,
    ProgressGranularity,
    ProgressPhase,
    ProgressQueue,
    ProgressReporter,
    create_progress_reporter,
    current_session_id,
    drain_progress_while_running,
    emit,
    emit_claim_verdict,
    emit_handoff,
    emit_llm_response,
    emit_prompt,
    emit_rate_limit,
    emit_tool_call,
    truncate_text,
    using_session,
)
from core.settings import (  # noqa: E402
    AppSettings,
    LLMSettings,
    WorkflowConfig,
    _validate_dotenv_keys,  # noqa: F401
    settings,
    validate_dotenv_keys,
)

# 4. Telemetry — only depends on logfire
from core.telemetry import configure_telemetry  # noqa: E402

# 3. Utility leaves — pure stdlib / json
from core.utils.json_utils import parse_json_safely  # noqa: E402
from core.utils.timing import perf_counter  # noqa: E402
from core.utils.validation import to_float, to_str_list  # noqa: E402
