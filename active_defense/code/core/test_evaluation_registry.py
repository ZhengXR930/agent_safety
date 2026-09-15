import unittest

from code.core.evaluation_registry import (
    PAPER_BASELINES,
    PAPER_BENCHMARKS,
    matrix_rows,
)
from code.run import validate_registry


class EvaluationRegistryTest(unittest.TestCase):
    def test_paper_scope_is_six_by_thirteen(self) -> None:
        self.assertEqual(len(PAPER_BENCHMARKS), 6)
        self.assertEqual(len(PAPER_BASELINES), 13)
        self.assertEqual(len(set(PAPER_BASELINES)), 13)

    def test_matrix_has_one_cell_per_baseline(self) -> None:
        rows = matrix_rows()
        self.assertEqual(len(rows), 6)
        for row in rows:
            self.assertEqual(set(row["baselines"]), set(PAPER_BASELINES))

    def test_protocols_and_commands_match_registry(self) -> None:
        report = validate_registry()
        self.assertEqual(report["status"], "PASS", report)


if __name__ == "__main__":
    unittest.main()
