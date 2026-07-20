# MCP Full Baseline Experiment Report

**Status: COMPLETE (MCPTox and maximal-reachable MSB cells verified)**

Both complete MCPTox cells exist and show a strong security/utility tradeoff. MCP-Guard reduces residual ASR to zero but rejects 79.56% of clean tool descriptions; StackOne leaves 9.12% residual ASR and rejects 36.74% of clean descriptions.

MSB integration, DeepSeek routing, response blocking, detection event logging, and official scoring passed. Per user direction, 21 remote MCP instances requiring OAuth or blocked by the development-host firewall were skipped. Both baselines produced all 725 raw runner cases with zero unclassified incomplete cases. Exact infrastructure evidence excluded 120 StackOne cases and 102 MCP-Guard cases; their completed-reachable intersection contains 605 cases.

On that identical N=605 denominator, StackOne has residual micro ASR 100/605=16.53% and MCP-Guard 63/605=10.41%. Official user-task-success utility is 301/411=73.24% for StackOne and 241/411=58.64% for MCP-Guard. The separate 15-tool clean metadata catalog gives FP 4/15=26.67% and 5/15=33.33%, respectively. Independent rerunning of the scorer produced a byte-identical JSON artifact (SHA-256 `997700f8ce9e686cebe4287d81d2b9e23c552e1df810d984673e6ac99ee2a0ed`).
