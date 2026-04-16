"""In-process A2A-style contracts used by the PocketFlow orchestration path.

Provides a small server/client façade over registered callables (see ``register_a2a_agent``), so :class:`~a2a_research.workflow.nodes.ActorNode` can
dispatch by :class:`~a2a_research.models.AgentRole` without HTTP.
"""

from __future__ import annotations

from a2a_research.a2a.server import (
    A2AClient as A2AClient,
)
from a2a_research.a2a.server import (
    A2AServer as A2AServer,
)
from a2a_research.a2a.server import (
    get_a2a_handler as get_a2a_handler,
)
from a2a_research.a2a.server import (
    get_server_registry as get_server_registry,
)
from a2a_research.a2a.server import (
    register_a2a_agent as register_a2a_agent,
)
from a2a_research.models import (
    A2AMessage as A2AMessage,
)
from a2a_research.models import (
    AgentCard as AgentCard,
)
from a2a_research.models import (
    AgentResult as AgentResult,
)
from a2a_research.models import (
    AgentRole as AgentRole,
)
from a2a_research.models import (
    AgentStatus as AgentStatus,
)
from a2a_research.models import (
    get_agent_card as get_agent_card,
)

__all__ = [
    "A2AClient",
    "A2AMessage",
    "A2AServer",
    "AgentCard",
    "AgentResult",
    "AgentRole",
    "AgentStatus",
    "get_a2a_handler",
    "get_agent_card",
    "get_server_registry",
    "register_a2a_agent",
]
