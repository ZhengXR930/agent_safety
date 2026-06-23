"""Generic placement optimizer for active-defense markers.

The optimizer is intentionally benchmark-agnostic.  It treats placement as a
black-box constrained optimization problem: an evaluator runs a candidate
placement and returns metrics such as TPR and I(M); the optimizer searches over
placement choices using UCT/MCTS.
"""

from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass, field
from typing import Callable, Hashable


@dataclass(frozen=True)
class PlacementArm:
    """One discrete placement choice for one unit, e.g. skill policy=strict."""
    unit_id: str
    option: str
    meta: tuple[tuple[str, str], ...] = ()


@dataclass
class PlacementMetrics:
    tpr: float
    im: float
    utility: float = 1.0
    cost: float = 0.0
    asr: float = 1.0          # attack success rate under this placement
    asr_base: float = 1.0     # attack success rate WITHOUT any marker (baseline)
    extra: dict = field(default_factory=dict)

    @property
    def detected_given_success(self) -> float:
        """TPR conditioned on the attack actually succeeding.

        This is the metric we really care about: catching real attacks, not
        catching runs we accidentally disrupted into failing.
        """
        if self.asr <= 0:
            return 0.0
        # tpr is over all attack runs; detected_and_success / total ≈ tpr when
        # detections only happen on successful attacks.  When the evaluator can
        # report it directly it should override via extra["detected_given_success"].
        if "detected_given_success" in self.extra:
            return float(self.extra["detected_given_success"])
        return min(1.0, self.tpr / self.asr)


def default_reward(metrics: PlacementMetrics, *, fp_penalty: float = 4.0,
                   cost_penalty: float = 0.1, utility_penalty: float = 1.0,
                   disrupt_penalty: float = 1.5) -> float:
    """Constrained objective as scalar reward.

    We reward catching *real* attacks (detected_given_success), heavily penalize
    any benign touch I(M) (near-zero-FP target), and—critically—penalize a
    placement that suppresses the attack itself.  A honey action placed too far
    IN can scare the agent off the attack chain entirely: that yields tpr≈0,
    im≈0 and would otherwise look "harmless" while being useless.  The
    disrupt_penalty on (asr_base - asr) captures exactly the "too far in"
    failure mode the midpoint theory predicts.
    """
    disruption = max(0.0, metrics.asr_base - metrics.asr)
    return (
        metrics.detected_given_success
        - fp_penalty * metrics.im
        - utility_penalty * max(0.0, 1.0 - metrics.utility)
        - cost_penalty * metrics.cost
        - disrupt_penalty * disruption
    )


Evaluator = Callable[[dict[str, str]], PlacementMetrics]


class RepeatedEvaluator:
    """Average an evaluator over N repeats to suppress LLM stochasticity.

    Each placement is evaluated ``repeats`` times; the mean of every numeric
    field is returned, and per-field sample stdev is stored in ``extra`` so the
    search can reason about confidence.  This directly addresses the observed
    high variance of single-run sweeps (EXP-2026W25-020).
    """

    def __init__(self, evaluator: Evaluator, repeats: int = 3):
        self.evaluator = evaluator
        self.repeats = max(1, repeats)

    def __call__(self, assignment: dict[str, str]) -> PlacementMetrics:
        runs = [self.evaluator(dict(assignment)) for _ in range(self.repeats)]

        def mean(attr: str) -> float:
            return statistics.fmean(getattr(r, attr) for r in runs)

        def stdev(attr: str) -> float:
            vals = [getattr(r, attr) for r in runs]
            return statistics.pstdev(vals) if len(vals) > 1 else 0.0

        dgs = statistics.fmean(r.detected_given_success for r in runs)
        agg = PlacementMetrics(
            tpr=mean("tpr"), im=mean("im"), utility=mean("utility"),
            cost=mean("cost"), asr=mean("asr"), asr_base=mean("asr_base"),
            extra={
                "repeats": self.repeats,
                "detected_given_success": dgs,
                "std": {k: stdev(k) for k in ("tpr", "im", "asr")},
                "runs": [r.__dict__ for r in runs],
            },
        )
        return agg


@dataclass
class _Node:
    assignment: dict[str, str]
    remaining: tuple[str, ...]
    parent: "_Node | None" = None
    option_from_parent: tuple[str, str] | None = None
    children: dict[tuple[str, str], "_Node"] = field(default_factory=dict)
    visits: int = 0
    total_reward: float = 0.0

    @property
    def value(self) -> float:
        return self.total_reward / self.visits if self.visits else 0.0


class PlacementMCTS:
    """UCT search over discrete placement choices.

    Search space format:
      {"skill-a-invoice-reviewer": ["strict", "balanced", "aggressive"], ...}

    The evaluator receives a complete assignment {unit_id: option}.  In expensive
    LLM settings, use a small iteration budget and cache evaluations.
    """

    def __init__(self, search_space: dict[str, list[str]], evaluator: Evaluator,
                 reward_fn: Callable[[PlacementMetrics], float] | None = None,
                 exploration: float = 1.4, seed: int = 0):
        self.search_space = {k: list(v) for k, v in search_space.items() if v}
        self.units = tuple(self.search_space.keys())
        self.evaluator = evaluator
        self.reward_fn = reward_fn or default_reward
        self.exploration = exploration
        self.rng = random.Random(seed)
        self.cache: dict[tuple[tuple[str, str], ...], tuple[PlacementMetrics, float]] = {}
        self.best_assignment: dict[str, str] | None = None
        self.best_metrics: PlacementMetrics | None = None
        self.best_reward: float = -float("inf")

    def _key(self, assignment: dict[str, str]) -> tuple[tuple[str, str], ...]:
        return tuple(sorted(assignment.items()))

    def _complete_random(self, assignment: dict[str, str], remaining: tuple[str, ...]) -> dict[str, str]:
        full = dict(assignment)
        for u in remaining:
            full[u] = self.rng.choice(self.search_space[u])
        return full

    def _eval(self, assignment: dict[str, str]) -> tuple[PlacementMetrics, float]:
        key = self._key(assignment)
        if key not in self.cache:
            metrics = self.evaluator(dict(assignment))
            reward = self.reward_fn(metrics)
            self.cache[key] = (metrics, reward)
            if reward > self.best_reward:
                self.best_reward = reward
                self.best_assignment = dict(assignment)
                self.best_metrics = metrics
        return self.cache[key]

    def _uct_child(self, node: _Node) -> _Node:
        assert node.children
        log_parent = math.log(max(1, node.visits))
        def score(child: _Node) -> float:
            if child.visits == 0:
                return float("inf")
            return child.value + self.exploration * math.sqrt(log_parent / child.visits)
        return max(node.children.values(), key=score)

    def _expand(self, node: _Node) -> _Node:
        if not node.remaining:
            return node
        unit = node.remaining[0]
        for opt in self.search_space[unit]:
            edge = (unit, opt)
            if edge not in node.children:
                child_assign = dict(node.assignment)
                child_assign[unit] = opt
                child = _Node(
                    assignment=child_assign,
                    remaining=node.remaining[1:],
                    parent=node,
                    option_from_parent=edge,
                )
                node.children[edge] = child
                return child
        return self._uct_child(node)

    def search(self, iterations: int = 32) -> tuple[dict[str, str], PlacementMetrics, float]:
        if not self.units:
            metrics, reward = self._eval({})
            return {}, metrics, reward

        root = _Node(assignment={}, remaining=self.units)
        for _ in range(iterations):
            node = root
            while node.remaining and node.children and len(node.children) == len(self.search_space[node.remaining[0]]):
                node = self._uct_child(node)
            node = self._expand(node)
            full = self._complete_random(node.assignment, node.remaining)
            metrics, reward = self._eval(full)
            while node is not None:
                node.visits += 1
                node.total_reward += reward
                node = node.parent

        assert self.best_assignment is not None and self.best_metrics is not None
        return self.best_assignment, self.best_metrics, self.best_reward


class TableEvaluator:
    """Small helper for tests/offline sweeps with precomputed metrics."""
    def __init__(self, table: dict[Hashable, PlacementMetrics], key_fn: Callable[[dict[str, str]], Hashable]):
        self.table = table
        self.key_fn = key_fn

    def __call__(self, assignment: dict[str, str]) -> PlacementMetrics:
        return self.table[self.key_fn(assignment)]

