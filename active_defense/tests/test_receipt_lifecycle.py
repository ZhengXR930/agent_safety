import hashlib
import unittest
from pathlib import Path

from code.defense.memory import CapabilitySurface
from code.defense.taskcontractor import (
    Clause, TaskContract, _REHEARSAL_PROMPT, _TASK_CONTRACT_SKILL)
from code.defense.wrap import (
    AcquireBinding, RuntimeReceiptRecorder, WrapRuntime)


class TaskContractSkillTests(unittest.TestCase):
    def test_runtime_prompt_has_single_skill_source(self):
        text = Path(_TASK_CONTRACT_SKILL).read_text(encoding="utf-8")
        body = text[text.find("\n---\n", 4) + len("\n---\n"):].strip()
        self.assertEqual(body, _REHEARSAL_PROMPT)
        self.assertIn("{task}", body)
        self.assertIn("{manifest}", body)


class RuntimeReceiptLifecycleTests(unittest.TestCase):
    @staticmethod
    def _runtime(task_id):
        contract = TaskContract("read record 1", [
            Clause("c0", "read the requested record", ["read_record"],
                   "record", arguments={"id": {"literal": 1}}),
        ])
        capability = CapabilitySurface(
            "read_record", arguments=("id",), observation=True)
        return WrapRuntime(contract, {"read_record": capability}, task_id=task_id)

    def test_same_receipt_content_is_isolated_by_task_id(self):
        left = RuntimeReceiptRecorder("run-left").issue("read", {"id": 1}, "value")
        right = RuntimeReceiptRecorder("run-right").issue("read", {"id": 1}, "value")
        self.assertNotEqual(left.digest, right.digest)
        self.assertEqual("run-left", left.task_id)
        self.assertEqual("run-right", right.task_id)

    def test_clause_binding_requires_receipt_owned_by_same_task(self):
        runtime = self._runtime("run-a")
        receipt = runtime.receipt_recorder.issue(
            "read_record", {"id": 1}, "value")
        binding = AcquireBinding(
            "run-b", runtime._task_receipt.digest, runtime._contract_digest,
            "c0", receipt.digest, receipt.source,
            hashlib.sha256(b"args").hexdigest())
        with self.assertRaises(ValueError):
            runtime.binding_store.add(binding)
        runtime.close()

    def test_runtime_binds_task_clause_and_destroys_receipts_on_close(self):
        runtime = self._runtime("run-1")
        self.assertTrue(runtime.admit_observation_call(
            "read_record", {"id": 1}, "c0", "call-1"))
        receipt = runtime.observe(
            "read_record", {"id": 1}, {"secret": "runtime-value"},
            call_id="call-1")
        self.assertEqual("run-1", receipt.task_id)
        self.assertEqual(1, len(runtime.receipt_bindings))
        binding = runtime.receipt_bindings[0]
        self.assertEqual("run-1", binding.task_id)
        self.assertEqual("c0", binding.clause_id)
        self.assertEqual(receipt.digest, binding.receipt_digest)

        audit = runtime.close()
        self.assertTrue(audit["closed"])
        self.assertEqual("run-1", audit["task_id"])
        self.assertEqual([], runtime.observations)
        self.assertEqual([], runtime.receipt_bindings)
        self.assertIsNone(runtime._task_receipt)
        self.assertIsNone(receipt.value)
        self.assertEqual({}, receipt.arguments)
        self.assertNotIn("runtime-value", repr(audit))
        self.assertNotIn("arguments", audit["receipts"][0])
        with self.assertRaises(RuntimeError):
            runtime.observe("read_record", {"id": 1}, "late")

    def test_default_task_ids_are_unique_for_identical_tasks(self):
        contract = TaskContract("same task", [])
        first = WrapRuntime(contract)
        second = WrapRuntime(contract)
        self.assertNotEqual(first.task_id, second.task_id)
        first.close()
        second.close()


if __name__ == "__main__":
    unittest.main()
