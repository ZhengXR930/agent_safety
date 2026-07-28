"""Public WRAP API.

WRAP is split by responsibility while preserving the original import surface:
immutable proof models and schema helpers live in :mod:`model`, semantic
projection lives in :mod:`projector`, and runtime receipt/gate resolution lives
in :mod:`runtime`.
"""

from ..contract import (
    AcquireBinding, ClauseBinding, ClauseBindingStore, ClauseReceiptBinding,
    ConditionalBinding, DeriveBinding, EffectBinding,
)
from .model import (
    ArgumentProvenance,
    GateResult,
    InstalledGate,
    Observation,
    RuntimeReceiptRecorder,
    Provenance,
    _Resolved,
    _contains_value,
    _is_prose_node,
    _nodes,
    _replace_pointer,
    _resolve_ref,
    _schema_accepts,
    _schema_field_catalog,
    _source_names,
    _stable,
)
from .binding import BindingPlacementAgent
from .runtime import SavedStateStore, WrapRuntime


__all__ = [
    "ArgumentProvenance",
    "ClauseBinding",
    "EffectBinding",
    "DeriveBinding",
    "ConditionalBinding",
    "ClauseBindingStore",
    "AcquireBinding",
    "ClauseReceiptBinding",
    "GateResult",
    "InstalledGate",
    "Observation",
    "RuntimeReceiptRecorder",
    "Provenance",
    "SavedStateStore",
    "BindingPlacementAgent",
    "WrapRuntime",
]
