# Discussion：当前问题讨论区

- **当前问题（一句话）：**
  在确认单一 Agent Skill Ecosystems benchmark 说服力不足后，是否可以把研究重心转为跨 benchmark 的可验证授权链推理防御？
- **关联日志：**
  - `LOGS/2026-W20.md` / `READ-2026W20-001`
  - `LOGS/2026-W21.md` / `READ-2026W21-001`
  - `LOGS/2026-W21.md` / `IDEA-2026W21-001`
- **关联材料：**
  - `/Users/bytedance/Downloads/Benign_in_Isolation__Harmful_in_Composition__Security_Risks_in_Agent_Skill_Ecosystems__3___Copy_ (1).pdf`
  - `idea/manual.md`
  - `idea/literature_assessment_2026-W21.md`
  - `idea/authorization-chain-rlvr.md`

---

## Thread #1：Benchmark 可信度与防御工作的说服力

【User】【2026-05-13】

我阅读了论文 `Benign in Isolation, Harmful in Composition: Security Risks in Agent Skill Ecosystems`，觉得论文存在一些问题。这些问题可能影响之后在这个 benchmark 上做防御的可能性。进一步说，如果这篇论文没中稿，那么基于此设计的防御策略是否不具备说服力，也需要认真判断。

主要疑问如下：

1. 论文测试的模型是加上 tool 后由作者自己构建的吗？是否依赖某些特定 agent 框架？
2. trace 是怎么采集和标注的？case 的来源是什么？筛选过程是什么？Mock sandbox 是什么？
3. 这个工作和 memory 污染的区别是什么？

【Agent】【2026-05-13】

当前更稳妥的判断是：先不要直接假设该 benchmark 足以支撑防御论文，而是把它当作一个需要审计的研究对象。防御策略是否有说服力，不只取决于原论文是否中稿，也取决于 benchmark 是否满足以下条件：

- agent/tool 构造方式清楚，并且不只绑定某个过窄的框架实现；
- trace 采集、case 来源、筛选标准和人工/自动标注规则可复现；
- mock sandbox 的安全边界明确，能够解释它与真实 agent 执行环境之间的差距；
- 与 memory poisoning / memory pollution 的威胁模型边界清楚，避免只是换一个表述重复已有问题。

**阶段性结论：**

目前这个方向仍然可以继续探索，但下一步应优先做 benchmark audit，而不是立刻设计防御方法。只有当 benchmark 的构造逻辑、标注可信度和威胁模型边界被说明清楚后，基于它的防御策略才更容易形成独立说服力。

**下一步：**

- [ ] 回到论文中逐项定位 model/tool setup、agent framework、trace collection、annotation protocol、case source、filtering criteria、mock sandbox definition。
- [ ] 写一段 threat model 对比：skill composition risk vs memory poisoning / memory pollution。
- [ ] 判断是否需要自己补一个更可复现的 mini-benchmark，作为后续防御工作的 Pilot。

---

## Thread #2：从单一 benchmark 防御转向 Authorization-Chain RLVR

【User】【2026-05-20】

我希望基于 `idea/manual.md` 继续判断这个方向的创新性、可行性、实验怎么做、baseline 选什么，并根据 `idea/idea-template.md` 在 `idea/` 文件夹下生成新的 idea。

【Agent】【2026-05-20】

这个问题和 5 月 13 日的 benchmark 可信度讨论是连续的。5 月 13 日的结论是：不要把防御工作的说服力押在单一 Agent Skill Ecosystems benchmark 上，因为它的 agent/tool 构造、trace 采集、case 来源、标注规则、mock sandbox 和 threat model 边界都还需要审计。现在的新判断是：这个方向可以继续，但研究对象应从“在某一个 benchmark 上做防御”升级为“跨 benchmark 的 agent action 授权链推理”。

新的 idea 已整理为 `idea/idea_2026-05-20_authorization-chain-rlvr.md`，核心不再是泛化的 prompt injection detection，而是：

- 把 agent 的高风险 tool call 表示为 authorization chain / Authorization DAG；
- 区分 user grant、tool return、skill output、review result、risk advice、target discovered 等不同 authority type；
- 用四类 violation 统一 multi-tool / multi-skill 风险：
  - Fabricated：动作驱动力不是用户授权；
  - Escalated：上游 evidence / advice / discovery 被错误升级为下游 authorization；
  - Exceeded：动作参数超出用户授权 scope；
  - Tainted：授权链或 sensitive sink 的数据链经过 untrusted source；
- 训练一个 7B 级 Authorization Reasoner 输出结构化 JSON；
- 用 symbolic validator + benchmark label 构造 RLVR 奖励，而不是只依赖 LLM-as-judge。

**和 5 月 13 日讨论的关系：**

5 月 13 日担心的是：如果 Agent Skill Ecosystems benchmark 本身不够可靠，那么基于它做防御会不会缺少说服力。现在的方案是把该 benchmark 降级为一个 skill-composition 风险来源，而不是唯一实验基础；同时引入 AgentDojo、InjecAgent、ASB、SkillInject、AgentTrap、TraceSafe 等 benchmark，统一到 authorization-chain violation schema 下。这样即使某一个 benchmark 的构造存在争议，论文的核心贡献仍然可以落在跨数据源的 threat model 统一、结构化中间推理、以及可验证 reward 训练上。

**阶段性结论：**

方向仍然可做，但创新表述必须收窄。不要声称“新的 prompt injection 防御”，更稳妥的定位是：

> Verifiable Authorization-Chain Reasoning for Secure Tool-Using Agents

也就是证明：相比 prompt-only defense、LLM-as-judge、task-alignment、IFC-style、least-privilege / boundary-enforcement baseline，显式重建 authorization chain 能在条件授权、多步 evidence laundering、scope overreach、tainted data-flow 等场景上带来更好的 safety / utility tradeoff。

**下一步：**

- [ ] 把 5 月 13 日的 benchmark audit 问题保留，但范围从单篇 Skill Ecosystems 扩展为“哪些 benchmark 有完整 trace、哪些只有 final IO、哪些需要重放 agent”。
- [ ] 更新 `method.md`：形式化 Authorization DAG、trust lattice、scope containment、taint-flow 和 reward functions。
- [ ] 构造 50 条统一 authorization trace schema，优先覆盖 `review -> install`、`scan -> modify`、`assess -> approve`、`tool return injection -> action`、`tainted data -> sink`、`wrong tool`、`scope exceeded` 七类场景。
- [ ] 实现 symbolic validator 后，再决定是否进入 SFT / GRPO；如果 validator 不能稳定检查 chain validity，暂时不要训练。

---

## Agent 维护区

- 2026-05-13：新增 `LOGS/2026-W20.md` 的 `READ-2026W20-001`，记录本周围绕 Agent Skill Ecosystems benchmark 的阅读疑问与下一步计划。
- 2026-05-17：新增 `LOGS/2026-W20.md` 的 `READ-2026W20-002`，记录对 AgentLAB 论文与代码仓库的数据结构、tool-call 评测机制与五类攻击构造方式的拆解。
- 2026-05-20：新增 `LOGS/2026-W21.md` 的 `READ-2026W21-001` 和 `idea/literature_assessment_2026-W21.md`，记录 authorization-chain RLVR 防御想法的第一轮文献判断：方向可行，但创新点应聚焦在可验证授权链推理，而不是泛化的 prompt injection 防御。
- 2026-05-20：新增 `idea/authorization-chain-rlvr.md`，根据 `idea/idea-template.md` 将当前想法整理成正式 idea 卡片；对应日志为 `LOGS/2026-W21.md` / `IDEA-2026W21-001`。
