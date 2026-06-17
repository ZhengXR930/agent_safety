# AgentShield (复现)

复现自 **AgentShield: Cross-Lingual Detection of Indirect Prompt Injection via
Deception** (arXiv:2605.11026, 代码 https://github.com/Yassin-H-Rassul/AgentShield)。

本目录是 `active_defense` 议题 RQ2 的对照 baseline——"AgentShield-style fixed
traps"。三层基于欺骗的**检测式**(detection-only)防御:

| 层 | 模块 | 信号 |
|---|---|---|
| Layer 1 Honeytools | `defenses/honeytools.py` | 工具列表注入假工具,被调用即判定受陷 |
| Layer 2 Honeytokens | `defenses/honeytokens.py` | 环境植入假凭证,出现在出站 tool args 即判定外泄 |
| Layer 3 Parameter Validator | `defenses/parameter_validator.py` | allowlist / 外部域名 / 弱口令校验,违规即记录 |

三层检测器作为 `agentdojo` 的 `BasePipelineElement`,插在 `ToolsExecutor` 之前。

## 与上游的差异
- **LLM 接入**:默认走内部 OpenAI 兼容网关(`internal_client.py`,从仓库根
  `config.txt` 读 `OPENAI_API_KEY`,`Api-Key` header)。`--no-internal` 可回退到
  上游 OpenAI/ModelsEnum/together/ollama 行为。
- 其余 defense 逻辑、176 条跨语言攻击(`attacks/attack_prompts.py`)**原样移植**。

## 安装
```bash
pip install -e ../../benchmarks/agentdojo   # 本地 agentdojo v0.1.35
# 或: pip install -r requirements.txt
```

## 运行
所有命令在本目录(`baselines/AgentShield/`)下执行。

```bash
# 1) Dry-run:不调外部 API,用 MockLLM 验证注入+三层检测+落盘
python -m agentshield.run_pilot --dry-run --limit 5

# 2) Live Pilot:单 suite,内部网关
python -m agentshield.run_pilot --suite banking --limit 5 --model gpt-4o-mini-2024-07-18

# 3) 全量:4 suites x 176 攻击
python -m agentshield.run_all_suites --model gpt-4o-mini-2024-07-18
```

结果写入 `agentshield/results/*.json`。

## 注意
- `parameter_validator` 的 IBAN allowlist 与 banking v1.2.2 测试数据绑定;
  `send_email` allowlist 上游为空(原样保留),扩展到其他 suite 时需按需补充。
- 检测式防御:违规 tool call 仍会在模拟环境中执行,只记录信号,不阻断。
