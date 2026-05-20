# Discussion：当前问题讨论区

- **当前问题（一句话）：**
  基于 Agent Skill Ecosystems benchmark 做防御研究前，是否需要先验证该 benchmark 的构造、标注和风险定义是否足够可靠？
- **关联日志：**
  - `LOGS/2026-W20.md` / `READ-2026W20-001`
- **关联材料：**
  - `/Users/bytedance/Downloads/Benign_in_Isolation__Harmful_in_Composition__Security_Risks_in_Agent_Skill_Ecosystems__3___Copy_ (1).pdf`

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

## Agent 维护区

- 2026-05-13：新增 `LOGS/2026-W20.md` 的 `READ-2026W20-001`，记录本周围绕 Agent Skill Ecosystems benchmark 的阅读疑问与下一步计划。
- 2026-05-17：新增 `LOGS/2026-W20.md` 的 `READ-2026W20-002`，记录对 AgentLAB 论文与代码仓库的数据结构、tool-call 评测机制与五类攻击构造方式的拆解。
