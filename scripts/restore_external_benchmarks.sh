#!/usr/bin/env bash
# Restore third-party benchmarks after migrating this repo to a new server.
# These are git-cloneable and are NOT stored in our repo (size + GitHub 100MB limit).
# Run from the repo root:  bash scripts/restore_external_benchmarks.sh
#
# After this, follow MIGRATION.md for the LOCAL-ONLY data that has no upstream
# (benchmarks/external/mcptox, benchmarks/agentdojo, benchmarks/ASB, benchmarks/ToolSafe)
# and to re-create config.txt with your DEEPSEEK_API_KEY.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
ROOT="$(pwd)"
echo "Repo root: $ROOT"

# path<TAB>git-url  (one per line)
REPOS=$(cat <<'EOF'
benchmarks/SCR_Bench	https://github.com/saint-viperx/SCR_Bench.git
benchmarks/ToolPrivBench	https://github.com/AISafetyHub/agent-tool-selection-bias.git
benchmarks/external/MSB	https://github.com/dongsenzhang/MSB
benchmarks/external/MCP-Guard	https://github.com/GenTelLab/MCP-Guard
benchmarks/external/progent	https://github.com/sunblaze-ucb/progent
benchmarks/external/mcp-scan	https://github.com/invariantlabs-ai/mcp-scan
benchmarks/external/skill-safety-bench	https://github.com/AI45Lab/skill-safety-bench
benchmarks/external/skill-inject	https://github.com/aisa-group/skill-inject
benchmarks/external/MaliciousAgentSkillsBench	https://github.com/protectskills/MaliciousAgentSkillsBench
benchmarks/external/MCP-Universe	https://github.com/SalesforceAIResearch/MCP-Universe
benchmarks/external/MCPSafety	https://github.com/xjzzzzzzzz/MCPSafety
benchmarks/external/MCPSecBench	https://github.com/AIS2Lab/MCPSecBench
EOF
)

ok=0; skip=0; fail=0
while IFS=$'\t' read -r path url; do
  [ -z "$path" ] && continue
  if [ -d "$ROOT/$path/.git" ]; then
    echo "SKIP  $path (already present)"; skip=$((skip+1)); continue
  fi
  echo "CLONE $path  <-  $url"
  mkdir -p "$(dirname "$ROOT/$path")"
  if git clone --depth 1 "$url" "$ROOT/$path" >/dev/null 2>&1; then
    ok=$((ok+1))
  else
    echo "  !! FAILED to clone $url"; fail=$((fail+1))
  fi
done <<< "$REPOS"

echo "-----------------------------------------------------------"
echo "cloned=$ok  skipped=$skip  failed=$fail"
echo
echo "STILL NEEDED (no upstream — copy from the old server, e.g. rsync/scp):"
echo "  benchmarks/external/mcptox      (our WRAP MCPTox data; required for run_mcptox.py)"
echo "  benchmarks/agentdojo  benchmarks/ASB  benchmarks/ToolSafe   (optional, unused by active work)"
echo
echo "Then:  cp config.txt.example config.txt  &&  put your DEEPSEEK_API_KEY in it."
echo "Optional SOTA baseline weights (2.6GB):"
echo "  python -c \"from huggingface_hub import snapshot_download as s; s('GenTelLab/MCP-Guard', local_dir='benchmarks/external/MCP-Guard/learnableshield_models')\""
