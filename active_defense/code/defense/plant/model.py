"""Immutable PLANT runtime and experiment records."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Plant:
    source: str
    token: str
    payload: object


@dataclass(frozen=True)
class PlantEvent:
    plant: str
    source: str
    channel: str
    argument_locator: str = ""


@dataclass(frozen=True)
class PlantDeployment:
    """Task-owned materialization trace with an exact canonical receipt node."""
    plant: str
    source: str
    locator: str
    before: object
    after: object
    receipt_digest: str = ""
    canonical_ref: str = ""
    canonical_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlantSlotTrace:
    """One unique runtime instance of a trusted skeleton slot."""
    source_kind: str
    version: str
    source: str
    outcome: str
