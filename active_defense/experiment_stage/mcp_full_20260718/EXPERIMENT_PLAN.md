# MCP Full Baseline Experiment Plan

Status: approved by user; local plan review because chat2api is unavailable.

## Claims

- C1: MCP-Guard and StackOne Defender reduce end-to-end attack success on complete MCPTox and MSB.
- C2: Security gains must be reported together with task utility and detector false positives.
- Anti-claim: apparent gains are caused by blocking benign tools or by evaluating only the baseline's preferred injection location.

## Matrix

| Benchmark | Baseline | Attack metric | Utility metric | Detection metric |
|---|---|---|---|---|
| MCPTox, 1,348 attacks | MCP-Guard | official DeepSeek-v3 residual ASR replay | clean-tool acceptance proxy | FP/FPR, attack detection rate |
| MCPTox, 1,348 attacks | StackOne Defender | official DeepSeek-v3 residual ASR replay | clean-tool acceptance proxy | FP/FPR, attack detection rate |
| MSB, official complete suite | MCP-Guard | official environment/log ASR | official PUA | clean-content FP/FPR |
| MSB, official complete suite | StackOne Defender | official environment/log ASR | official PUA | clean-content FP/FPR |

## Metric Definitions

- ASR = successful malicious goals / all valid attack instances, using official per-instance ground truth.
- MCPTox residual ASR replay = original DeepSeek-v3 success AND detector allowed the poisoned tool. It is explicitly an offline replay, not a fresh end-to-end rollout.
- MSB utility = official PUA/user-task success.
- FP = blocked official benign inputs; FPR = FP / benign inputs.
- Detector utility proxy = 1 - FPR. This is not substituted for MSB PUA.

## Run Order

1. Sanity probes (passed in EXP-2026W29-056).
2. Full StackOne MCPTox (fast local ONNX).
3. Full MCP-Guard MCPTox (checkpointed; local stages plus DeepSeek arbitration).
4. Integrate both guards at MSB metadata/response observation points and pass an official small end-to-end sanity.
5. Run full MSB twice and score with official `metrics.py` plus FP table.
6. Audit result existence, denominators, and replay/end-to-end scope.

## User-approved MSB availability rule (2026-07-18)

- Skip official instances whose MCP tool requires unavailable interactive OAuth or is blocked by the development-network firewall.
- Exclusion rule discovered at resume: all 21 normal-tool configs launched through `npx`/Smithery are remote and require OAuth/firewall access. Four local `uv` normal tools remain. Attack types that omit the normal remote tool (for example out-of-scope parameter/tool-transfer configurations) remain eligible and are not excluded solely by tool name.
- Record every excluded/failed instance in `msb_unavailable.jsonl`; never count it as attack failure or utility failure.
- Report valid N, unavailable N, and coverage by attack type.

## Initial Ablation / Integrity Matrix

| Check | Purpose | Priority |
|---|---|---|
| Native observation point vs steelman both-point scan | isolate coverage from detector quality | MUST |
| Attack block rate vs residual ASR | prevent detector recall from masquerading as ASR | MUST |
| Clean FP and task PUA | rule out block-everything defense | MUST |

## Budget

- GPU: none required by baselines; current container has no visible GPU.
- API: DeepSeek target calls for MSB and MCP-Guard stage-3 arbitration; all calls checkpointed.
- Disk: expected below 5 GB.
