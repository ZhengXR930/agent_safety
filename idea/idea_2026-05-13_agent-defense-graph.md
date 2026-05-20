# Hook-based Behavior Graph Defense for Long-Chain Agent Attacks

> 创建日期：2026-05-13
> 关键词：agent defense / runtime hook / behavior graph / memory poisoning / dangerous skill abuse / multi-turn

## 1. 一句话总结

- 一句话：在 LLM agent 运行时，通过 hook 拦截 tool call / prompt / memory & file access，把多轮执行 trace 建成一张**跨 turn / 跨 session 的类型化行为图**，把 memory 写入和 skill 调度作为一等公民节点，从而在 long-chain 攻击（memory 投毒 + 危险 skill 滥用）发生过程中做出低延迟告警与干预。

## 2. 一段话总结

LLM agent 的长链攻击难以防御的本质是：**单步看都合理，组合起来才恶意**——尤其是 memory 投毒（turn N 写入污染，turn N+K 触发）和危险 skill 滥用（看似分散的工具调用拼成攻击链）。现有 runtime 防御要么 per-call（AEGIS）、要么 per-session 顺序正则匹配（AgentTrust+RiskChain），都不能在跨 turn / 跨 session 的执行流上做因果级别的推理；少数做 graph 的工作（Agent-Sentry、ARGUS）也只在单次 execution 内，且**完全没有把 memory 当作节点**。我们提出在 agent 运行时通过 hook 持续拦截事件，构建一张以 tool-call / memory-write / memory-read / skill-dispatch 为节点、以 data-flow / causal-derivation 为边的行为图，并在图上做子图级别的可疑模式检测，先做 warn，再追求低延迟 block。面向研究方向是 agent safety / runtime defense 领域，**现在做的理由**：2026 年 3-5 月 graph-based agent monitoring 已成主流 motif（5 篇以上），但 memory + skill + cross-turn 三者整合是公认空白（Mnemonic Sovereignty 综述 2604.16548 明确指出 Execute / Share / Forget 阶段空白）。

## 3. 一页纸总结

### 3.1 背景 & 问题

- **现状**：
  - LLM agent 攻击面正在扩张：indirect prompt injection、恶意 tool 输出、被污染的文件、MCP supply chain、persistent memory 投毒、危险 skill 调度
  - 2026 年 OWASP Agentic Top 10 finalize，memory poisoning / tool abuse / supply chain 都在顶层
  - 4 月发生 "frontier model escape" 事件（2604.23425），社区呼吁五阶段 containment monitoring
- **现有防御的不足**：
  - **AgentTrust + RiskChain (2605.04785)**：170 条 YAML 规则 + 7 条手写正则 chain，**不是 graph 是有序列表**；作者自己在 §6.7 承认 RiskChain 在 stateless benchmark 上效果 = 0；**无 memory 概念，无跨 session 状态**
  - **AEGIS (2603.12621)**：3 阶段 firewall（递归参数提取 → 22 正则 → JSON Schema），8.3ms 延迟很好，但 **per-call 独立，无任何状态**
  - **Agent-Sentry / ARGUS / AgentArmor**：都做 graph，但都是**单次 execution graph**，无 cross-turn / 无 memory 节点
  - **NeuroTaint (2604.23374)**：唯一明确做 cross-session memory taint 的工作，但**离线** auditor，不是 runtime hook
  - 共同盲点：**没有人把 memory 写入和 skill 调度作为一等公民 graph 节点 + runtime + cross-turn 三件套整合**

### 3.2 目标 & 成功标准

- **面向**：agent 安全研究社区、agent 框架使用者（Claude Code Hooks / LangGraph / AutoGen 用户）、agent 部署方
- **成功时的可感知改变**：
  - 在 memory 投毒和 dangerous skill 攻击发生时，**在攻击完成之前**（不是事后审计）给出告警
  - 提供首个 cross-turn 行为图 schema 作为 agent safety 的通用基础设施
- **成功指标**：
  - 在 memory poisoning benchmark（AgentPoison / MINJA / MemoryGraft trace）上 ASR 显著低于 AgentTrust 和 NeuroTaint
  - 在 multi-turn benchmark（MT-AgentRisk）上跨 turn 检测准确率 vs AgentTrust 的 RiskChain 显著提升（利用作者自己承认的 §6.7 gap）
  - 单步告警延迟 < 50ms（warn 路径），block 路径 < 200ms
  - tool-call 密度 / trace 长度对检测效果的影响曲线（这是本工作要新引入的一等指标）

### 3.3 核心方案（High-level）

- **关键思路**：
  - **L1 Hook 层**：拦截 tool call（pre-exec）、prompt 注入点、memory read / write、file access、skill dispatch；以 Claude Code Hooks 为主推平台（社区动能正起，`async:true` 支持低延迟），LangGraph callbacks 作为可移植目标
  - **L2 事件流 → 图**：每个事件 → 一个 typed node；节点类型至少包括 `tool_call` / `memory_write` / `memory_read` / `file_access` / `skill_dispatch` / `prompt_segment`；边类型 `data_flow` / `causal_derivation` / `reads_from` / `writes_to` / `derived_from`
  - **L3 节点级特征**：借鉴 AEGIS — 递归参数提取（depth 32）、22 类正则 tag、JSON Schema 不变量；补它没做的 base64/hex/url 多层解码
  - **L4 子图级检测**：在图上识别可疑子图（memory-write 来源被污染 + 后续 memory-read 流向高权限 skill 这类模式）；起点先用模板 + 同构匹配，后续可上 GNN
  - **L5 跨 session 状态**：持久化图存储 + TTL eviction；以 AEGIS 的 Ed25519 哈希链 audit log 作为 graph 的输入流（自带 tamper-evident）
- **关键设计决策（部分仍是假设）**：
  - **memory 节点的抽象粒度**：raw write vs semantic-level（待定）
  - **跨 session 状态的存储后端**：嵌入式 graph DB vs 文件 + 内存索引
  - **检测层先模板再学习**：第一版用 hand-written subgraph patterns（借鉴 RiskChain 的 7 条 chain 模板做出图等价物），第二版考虑 learned GNN
  - **延迟预算分层**：warn 路径同步 hook < 50ms；block 路径允许 < 200ms 阻塞；深度子图查询走 async 路径

### 3.4 风险 & 开放问题

- **最大不确定性**：
  - **MT-AgentRisk 的 tool-call 密度是否够支撑行为图**（如果太稀疏只能退到数据流图为主，这是 fallback 路径）
  - **cross-session 状态的工程复杂度**——能否在 runtime 维护一个不影响 agent 性能的持久化图
  - **memory 节点的语义抽象**——raw byte 级 vs LLM 语义级，两者的代价完全不同
- **需要先验证的关键假设**：
  - 假设 1：MT-AgentRisk / AgentDojo / AgentPoison trace 平均 tool 调用数 ≥ 5（图才有意义）
  - 假设 2：memory 投毒的「写入污染 → 读取触发」存在可观测的 graph-level signature
  - 假设 3：Claude Code Hooks 的 `PreToolUse` async 模式延迟可控（要实测）

## 4. 相关工作 & 参考文献

### 主要对手（必须正面对位）

- [AgentTrust + RiskChain (2605.04785)](https://arxiv.org/abs/2605.04785) — 最像我们的 runtime interceptor；但**不是 graph，无 memory 概念，作者自己承认 RiskChain 在 stateless benchmark 上效果 = 0（§6.7）**；这是我们差异化的主要靶子
- [Agent-Sentry (2603.22868)](https://arxiv.org/abs/2603.22868) — per-execution data-flow provenance graph；但**单次执行内、无 memory 节点**
- [ARGUS (2605.03378)](https://arxiv.org/abs/2605.03378) — influence provenance graph + AgentLure benchmark；但**只针对 context injection，非 memory poisoning**
- [NeuroTaint / Ghost in the Agent (2604.23374)](https://arxiv.org/abs/2604.23374) — 唯一明确做 cross-session memory taint；**但离线 auditor，不是 runtime**

### 主要借鉴源

- [AEGIS (2603.12621)](https://arxiv.org/abs/2603.12621) — 3 阶段 firewall：递归参数提取（depth 32）+ 22 正则 + JSON Schema + Ed25519 哈希链 audit log；**这套 per-node feature 提取可以直接复用到 graph 节点上**
- [AgentArmor (2508.01249)](https://arxiv.org/abs/2508.01249) — PDG/CFG/DFG runtime trace + type system，3% ASR；**老 baseline，必引**
- [MindGuard (2508.20412)](https://arxiv.org/abs/2508.20412) — Decision-Dependence Graph from LLM attention；**graph 构造思路参考**

### Benchmark / 评测

- [MT-AgentRisk (2602.13379)](https://arxiv.org/abs/2602.13379) — 第一个多轮 attack benchmark，Claude-4.5-Sonnet ASR +27%；**待精读确认 tool-call 密度**
- [AgentPoison (NeurIPS'24)] / [MINJA (2503.03704)](https://arxiv.org/abs/2503.03704) / [MemoryGraft (2512.16962)](https://arxiv.org/abs/2512.16962) — memory poisoning 攻击 trace 来源
- AgentDojo / InjecAgent / AgentHarm / ASB — 经典 baseline benchmark

### 综述 / 动机

- [Mnemonic Sovereignty 综述 (2604.16548)](https://arxiv.org/abs/2604.16548) — 明确指出 Execute / Share / Forget 阶段空白，**直接背书我们的定位**
- [Containment after April 2026 escape (2604.23425)](https://arxiv.org/abs/2604.23425) — 呼吁五阶段 containment monitoring，**我们是它的具体实现**

### 平台 / 社区

- [Claude Code Hooks docs](https://code.claude.com/docs/en/agent-sdk/hooks) — 1 月扩展 `async:true`，主推平台
- OWASP Agentic Top 10 (2026) — 把 memory poisoning / tool abuse / supply chain 列在顶层
- OpenClaw 安全分析 (2603.10387) — 1 月底从 9K 飙到 210K+ stars 的攻击重灾区

## 5. TODO & 下一步

### 接下来 1–3 个可以做的小步骤

1. **精读 NeuroTaint (2604.23374)**：确认它"离线"这一点是否绝对（影响差异化叙述强度），抽取它的 cross-session taint 设计可借鉴部分
2. **实测 MT-AgentRisk 的 tool-call 密度**：决定是行为图为主还是数据流图为主（关键决策点）
3. **设计 graph schema v0.1**：列出所有节点类型 / 边类型 / 节点特征 / memory 节点的抽象粒度选项 → 形成 1 页设计文档

### 需要先回答的问题

- memory 节点是「raw write」还是「semantic-level」？两者代价差一个数量级
- cross-session 状态用什么后端？嵌入式 graph DB 还是文件 + 内存索引？
- 平台是 Claude Code Hooks-only 还是同时做 LangGraph 适配器？前者社区动能足但封闭，后者通用但实现成本高
- 子图检测先模板还是先学习？模板可解释但覆盖低，学习需要数据但难解释

## 6. 定位句草稿（投到 paper 时用）

> Prior runtime defenses for LLM agents fall into two camps: **rule-and-chain interceptors** such as AgentTrust+RiskChain, which match ordered regex sequences over a per-session action list (and whose authors candidly note in §6.7 that their stateless benchmarks fail to exercise the chain detector at all), and **content-firewall gateways** such as AEGIS, which apply deep-argument extraction, regex patterns, and JSON-Schema policies per individual tool call. Neither system models **agent long-term memory** or **skill dispatch** as first-class entities, so neither addresses memory poisoning or dangerous-skill abuse. Our work fills this gap by intercepting tool calls, prompts, and memory/file accesses into a **typed behavior graph that carries state across turns and sessions**, turning AEGIS-style per-node features and AgentTrust-style chain templates into edges of a single cross-turn data-flow structure.
