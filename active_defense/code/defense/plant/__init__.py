"""Public PLANT API split into placement, structure, and runtime responsibilities."""
from .model import Plant, PlantDeployment, PlantEvent, PlantSlotTrace
from .placement import PlantPlacementAgent
from .runtime import PlantRuntime
from .structure import (_changes_atomic_collection_member, _contains, _leaves,
                        _valid_rewrite, replace_observation)

__all__ = [
    "Plant",
    "PlantDeployment",
    "PlantEvent",
    "PlantPlacementAgent",
    "PlantRuntime",
    "PlantSlotTrace",
    "replace_observation",
]
