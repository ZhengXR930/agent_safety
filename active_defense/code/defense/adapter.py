"""Adapter — the ONLY environment-specific code: the external interface that reads a benchmark and
exposes it to the generic Engine as a set of target-agent ENVIRONMENTS + tasks.

A benchmark integration is just: "here are the env directories, and the attack / benign task for each."
Everything else (perceive units, route must-take, design+certify decoys, deploy, run, detect) is the
generic Engine.  No per-dataset perceive/deploy/detect.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Env:
    """One target-agent environment the Engine will defend + probe."""
    key: str
    case_dir: Path                 # the benchmark case directory (copied into an isolated work dir per run)
    attack_task: str               # the prompt that drives the laundered/over-reach episode
    benign_task: str               # the read-only / in-scope episode (for benign-fit + FP)
    benign_case_dir: Path = None   # if set, benign episodes run in THIS dir (attack/benign-by-DIRECTORY,
                                   # e.g. TrustLift experiment-group vs control-group); else case_dir
    meta: dict = field(default_factory=dict)
    # SPEECH-ACT benchmarks (harm = a text decision, e.g. AuthBlur's DECISION:1) have NO file effect,
    # so the engine's file-snapshot detection can't see the commitment.  Such an adapter supplies this
    # hook: given the agent's output, return True iff the agent made an ENABLING commitment.  When set,
    # the engine also flags a decoy whose marker is CITED in the output of a committed episode.
    commitment_signal: object = None    # callable(output:str)->bool | None (None => file-effect only)


class Adapter(ABC):
    """Thin benchmark interface.  Subclass per benchmark; provide ONLY envs()."""
    name: str = "adapter"

    @abstractmethod
    def envs(self) -> list[Env]:
        """Read the benchmark; return the list of target environments + their attack/benign tasks."""
