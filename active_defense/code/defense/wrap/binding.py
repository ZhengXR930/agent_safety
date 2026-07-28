"""One semantic Binding Placement Agent for runtime edges and projections."""
from __future__ import annotations

from .expansion import BindingOriginPlacement
from .projector import ProjectionPlacement


class BindingPlacementAgent(BindingOriginPlacement, ProjectionPlacement):
    """Propose bindings; deterministic runtime code validates and replays them.

    Dynamic workflow selection and static Clause projection share one Agent
    identity, one model connection, and task-local caches.  They are two typed
    operations of the same role, never independent authorization oracles.
    """

    def __init__(self, client, model: str, agent_runner=None):
        BindingOriginPlacement.__init__(
            self, client, model, agent_runner=agent_runner)
        self.output_schemas = {}
        self.agent_trace = []

