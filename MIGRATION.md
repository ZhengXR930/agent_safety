# Migrating this repo to a new server

Git carries **code + docs + LOGS + restore scripts**. It does **not** carry the
benchmarks/data (too large; GitHub rejects files >100MB and the benchmarks contain
nested `.git` repos). Restore those after cloning.

## 1. Get the code
```bash
git clone git@github.com:ZhengXR930/agent_safety.git
cd agent_safety
```

## 2. Re-create secrets
```bash
cp config.txt.example config.txt
# edit config.txt: set DEEPSEEK_API_KEY (and OPENAI_API_KEY if used)
```

## 3. Restore third-party benchmarks (auto, git-cloneable)
```bash
bash scripts/restore_external_benchmarks.sh
```
This re-clones: SCR_Bench, MSB, MCP-Guard, progent, mcp-scan, skill-safety-bench,
skill-inject, MaliciousAgentSkillsBench, MCP-Universe, MCPSafety, MCPSecBench, ToolPrivBench.

## 4. Copy LOCAL-ONLY data (no upstream — must transfer from the old server)
These have no git remote, so copy them directly (rsync/scp):
```bash
# REQUIRED for current MCP work (run_mcptox.py):
rsync -a OLD:/…/agent_safety/benchmarks/external/mcptox/  benchmarks/external/mcptox/
# OPTIONAL (not used by active work):
#   benchmarks/agentdojo  benchmarks/ASB  benchmarks/ToolSafe
```

## 5. Python env
```bash
# active_defense backend uses the openai client + (for MCP-Guard baseline) transformers/torch.
pip install openai anthropic mcp transformers sentence-transformers torch huggingface_hub onnx onnx2pytorch
```

## 6. (Optional) SOTA baseline weights — MCP-Guard stage-2 (~2.6GB, not committed)
```bash
python -c "from huggingface_hub import snapshot_download as s; \
  s('GenTelLab/MCP-Guard', local_dir='benchmarks/external/MCP-Guard/learnableshield_models')"
pip install onnx onnx2pytorch
# Note: README in that repo names the wrong HF id (MCP-Guard-Shield 404); the real id is GenTelLab/MCP-Guard.
# Also re-apply the empty-issue bugfix at src/mcp_guard/api/routers/guardrail.py:201
#   end_time = model_issues[0].end_time if model_issues else time.time()
```

## 7. External runtimes (not via pip)
- **Docker** (for skill-sandbox / SkillSafetyBench harbor runs).
- **Claude Code CLI** + `uv tool install harbor` (for SkillSafetyBench).
- The defense backend drives `claude` (Claude Code CLI) pointed at DeepSeek via env in `defense/backend.py`.

## What continues to work after steps 1–5
- MCP: `active_defense/code/run_mcptox.py`, `run_msb.py` (WRAP) + `run_mcpguard_baseline.py` (baseline).
- SCR-Bench PLANT: `run_engine.py` (+ adapters_scr).
- Skill sandbox: `run_skill_plant.py` (needs Docker).
- All LOGS/, Formal.md, Discussion.md, idea.md carry over via git.
