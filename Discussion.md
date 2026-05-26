# Discussion · 当前 Active 议题

> **协议要求**：本文件同一时刻只承载 **1 个 active 议题**。议题关闭后整体迁移到 `Discussion/Archive/YYYY-MM-DD-<slug>.md`，本文件用模板重置或立即承载下一个议题。
> 
> Merge note：本文件从旧版 `discussion/Discussion.md` 导入，旧文件保留为迁移前快照。

---

## Issue Header

| 字段 | 值 |
|---|---|
| **议题号 (ID)** | `DISC-2026W21-001` |
| **标题 (Title)** | 是否从 Authorization-Chain RLVR 转向小模型快速本地危险 tool-use guard |
| **状态 (Status)** | `Open` |
| **发起人 (Owner)** | `Angus` / `Agent` |
| **开题时间 (Opened)** | `2026-05-20` |
| **关联 idea/method** | `idea.md`; `idea/idea_2026-05-20_authorization-chain-rlvr.md`; `method.md` |
| **关联实验** | `READ-2026W21-001`, `IDEA-2026W21-001` |

---

## Open Questions（待决清单）

- [ ] Q1：一作是否确认从“完整授权链形式化防御”转向“小模型快速本地危险 tool-use guard”？ (owner: `Angus`, due: `TBD`)
- [ ] Q2：Pilot 是否先定义 benign / suspicious / unauthorized / scope-exceeded / tainted-sensitive-sink 的危险 tool-use 分类或排序任务？ (owner: `Agent`, due: `TBD`)
- [ ] Q3：MemSifter 应作为工程 baseline、训练路线参考，还是正式论文 baseline？ (owner: `Angus`, due: `TBD`)

---

## Posts（回帖区）

> **格式**：新增回帖请以 `【角色@姓名】【YYYY-MM-DD HH:MM】` 开头。
> **角色**：`PI` / `Lead` / `Collab` / `Agent`。
> **Agent 发言必须**尽量链接到 `LOGS/...#EXP-...` 或对应 READ/IDEA 记录，并贴关键判断。

【Agent@Codex】【2026-05-20 00:00】

已从旧版 `discussion/Discussion.md` 导入以下讨论内容，作为 `DISC-2026W21-001` 的完整上下文。后续新增讨论应直接写入本文件。

---

# Discussion：当前问题讨论区

- **当前问题（一句话）：**
  5 月 20 日之后，idea 是否应从“完整授权链形式化防御”进一步转向“小模型快速本地危险 tool-use guard”，并在一作确认后再更新 idea 文件？
- **关联日志：**
  - `LOGS/2026-W21.md` / `READ-2026W21-001`
  - `LOGS/2026-W21.md` / `IDEA-2026W21-001`
- **关联材料：**
  - `idea/manual.md`
  - `idea/literature_assessment_2026-W21.md`
  - `idea/authorization-chain-rlvr.md`

---

## Thread #1：Idea 转向：从单一 benchmark 防御到 Authorization-Chain RLVR

【User】【2026-05-20】

我希望继续判断这个方向的创新性、可行性、实验怎么做、baseline 选什么，并根据 `idea/idea-template.md` 在 `idea/` 文件夹下生成新的 idea。

【Agent】【2026-05-20】

这是当前 idea 的第一次明确转向：研究对象不再是“在某一个 benchmark 上做防御”，而是升级为“跨 benchmark 的 agent action 授权链推理”。这个转向的核心是把单点 benchmark 依赖降级，把论文贡献放在 threat model 统一、结构化中间推理、以及可验证 reward 训练上。

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

**转向含义：**

现在的方案是把单一 skill-composition benchmark 降级为一个风险来源，而不是唯一实验基础；同时引入 AgentDojo、InjecAgent、ASB、SkillInject、AgentTrap、TraceSafe 等 benchmark，统一到 authorization-chain violation schema 下。这样即使某一个 benchmark 的构造存在争议，论文的核心贡献仍然可以落在跨数据源的 threat model 统一、结构化中间推理、以及可验证 reward 训练上。

**阶段性结论：**

方向仍然可做，但创新表述必须收窄。不要声称“新的 prompt injection 防御”，更稳妥的定位是：

> Verifiable Authorization-Chain Reasoning for Secure Tool-Using Agents

也就是证明：相比 prompt-only defense、LLM-as-judge、task-alignment、IFC-style、least-privilege / boundary-enforcement baseline，显式重建 authorization chain 能在条件授权、多步 evidence laundering、scope overreach、tainted data-flow 等场景上带来更好的 safety / utility tradeoff。

**下一步：**

- [ ] 梳理哪些 benchmark 有完整 trace、哪些只有 final IO、哪些需要重放 agent。
- [ ] 暂缓更新 `method.md` 中完整的 Authorization DAG、trust lattice、scope containment 和 reward functions，避免过早把工作卡在大而全的理论定义上。
- [ ] 构造 50 条统一 authorization trace schema，优先覆盖 `review -> install`、`scan -> modify`、`assess -> approve`、`tool return injection -> action`、`tainted data -> sink`、`wrong tool`、`scope exceeded` 七类场景。
- [ ] 实现 symbolic validator 后，再决定是否进入 SFT / GRPO；如果 validator 不能稳定检查 chain validity，暂时不要训练。

---

## Thread #2：Angus 对 baseline 与训练路线的调整建议

【Angus】【2026-05-20】

目前可以先推荐 [MemSifter](https://github.com/plageon/MemSifter) 作为一个 baseline 尝试或训练路线参考。它不是直接做 agent authorization defense，但它的“小模型代理推理 + outcome-driven ranking / RL 训练”思路可以借鉴：先把复杂授权链问题降到一个更可控的危险 tool use 分类或排序任务上，比较 SFT 和 RL 两条路线是否真的带来差异。

当前先不要把“确定完整 method 数学形式化”作为最优先 TODO。也就是说，`idea/idea_2026-05-20_authorization-chain-rlvr.md` 里“在 `method.md` 形式化 Authorization DAG、trust lattice、scope containment 和 reward functions”这一项先划掉，避免过早把工作卡在大而全的理论定义上。

更实际的下一步建议：

- SFT 和 RL 都要尝试，先用同一批危险 tool use 样本做分类或排序对照。
- 如果算力不足，优先用 LoRA / QLoRA 做小模型适配，不要一开始就假设必须全参训练。
- Pilot 阶段先定义“危险 tool use 分类”：例如 benign / suspicious / unauthorized / scope-exceeded / tainted-sensitive-sink，再看这些标签是否能映射回后续的 authorization-chain violation。
- MemSifter 可以作为工程 baseline 和训练参考，但论文定位上仍要小心：它更接近 memory retrieval / proxy reasoning，不应被写成现成的安全防御 baseline。

---

## Thread #3：Idea 转向：小模型快速本地危险 tool-use guard

【Angus】【2026-05-20】

在 Tainted / IFC / provenance 相关工作已经比较拥挤的情况下，idea 可以进一步转向“小模型快速本地反应”。重点不再是声称提出全新的 taint tracking 或完整 runtime provenance system，而是训练一个可本地部署的小型 authorization / dangerous-tool-use guard，在每次危险 tool call 前快速判断是否存在授权违规或高风险执行。

新的核心卖点可以是：

- 与闭源大模型 judge 对比，安全判断性能不明显下降，但 p50 / p95 latency、调用成本、隐私暴露和部署可控性明显更好。
- 小模型可以本地部署，agent trace、tool arguments、用户上下文不必发给闭源 API，更适合高频 tool-call boundary 检查。
- Pilot 先做危险 tool use 分类或排序，而不是一开始追求完整 Authorization DAG 形式化。
- SFT 和 RL 都要尝试；如果算力不足，先用 LoRA / QLoRA 验证小模型是否能接近闭源模型 judge。
- `Tainted` 保留为风险维度之一，但不作为主创新；主创新更偏“快速、本地、低成本、接近闭源 judge 的危险 tool-use 判别器”。

**待确认事项：**

- 该转向需要先给一作确认。
- 在一作确认前，暂不修改 `idea/idea_2026-05-20_authorization-chain-rlvr.md` 或 `idea/idea.md`。
- 确认后再把 idea 文件从 “Verifiable Authorization-Chain Reasoning” 调整为 “Fast Local Authorization Guards / Dangerous Tool-Use Guard” 方向。

---

## Agent 维护区

- 2026-05-17：新增 `LOGS/2026-W20.md` 的 `READ-2026W20-002`，记录对 AgentLAB 论文与代码仓库的数据结构、tool-call 评测机制与五类攻击构造方式的拆解。
- 2026-05-20：新增 `LOGS/2026-W21.md` 的 `READ-2026W21-001` 和 `idea/literature_assessment_2026-W21.md`，记录第一次 idea 转向：authorization-chain RLVR 防御想法可行，但创新点应聚焦在可验证授权链推理，而不是泛化的 prompt injection 防御。
- 2026-05-20：新增 `idea/authorization-chain-rlvr.md`，根据 `idea/idea-template.md` 将当前想法整理成正式 idea 卡片；对应日志为 `LOGS/2026-W21.md` / `IDEA-2026W21-001`。
- 2026-05-20：新增 Angus 对 baseline 与训练路线的建议：先把 MemSifter 作为 baseline / 训练参考尝试；SFT 与 RL 都做；算力不足先 LoRA；Pilot 从危险 tool use 分类开始。
- 2026-05-20：新增第二次 idea 转向 session：考虑从完整授权链形式化进一步转为“小模型快速本地危险 tool-use guard”；待一作确认后再更新 idea 文件。

## Thread #4：公开 benchmark 上的验证结果与当前结论

【Agent@Codex】【2026-05-26 18:10】

按用户要求，将 5 月 24–26 日的实验压缩为当前议题的实验结论。本轮只使用公开 benchmark / 官方 baseline，不把 `code/`、`benchmarks/` 或中间实验产物作为正式讨论内容。证据记录见 `LOGS/2026-W21.md#EXP-2026W21-001` 至 `LOGS/2026-W21.md#EXP-2026W21-005`。

**实验设定**

- Threat model：benign user request + indirect injected context/tool output + proposed sensitive/action-bearing tool call。
- 主集：ToolSafe AgentDojo trajectory 中筛出的 489 条 in-scope step，unsafe=342、safe=147。
- 泛化检查：InjecAgent base rollout 1054 条中转换出的 150 条 valid proposed-action step，unsafe=90、safe=60。该集只用于 proposed-action guard，不代表完整 InjecAgent ASR。
- Baseline：ToolSafe GPT-4o guard、GPT-5.5 API guard、官方 `MurrayTom/TS-Guard` local checkpoint。
- Our method：AuthDAG scope validator，检查 action scope 和 source/authorization consistency。

**ToolSafe AgentDojo 489**

| 方法 | F1 | Attack catch | Clean allow | FP | FN | 备注 |
|---|---:|---:|---:|---:|---:|---|
| GPT-4o ToolSafe Guard | 0.898 | 1.000 | 0.469 | 78 | 0 | parse-error 视为 block |
| GPT-5.5 ToolSafe Guard | 0.871 | 1.000 | 0.303 | 101 | 0 | 263/489 被 API filter 拦截，不是纯 judge |
| TS-Guard ToolSafe Guard | 0.945 | 0.904 | 0.979 | 3 | 33 | 官方 local learned guard |
| AuthDAG scope validator | 0.986 | 0.994 | 0.946 | 8 | 2 | 当前 symbolic validator |

重叠结果：TS-Guard 漏掉的 33 个 attack，AuthDAG 全部抓住；AuthDAG 漏掉的 2 个 attack，TS-Guard 全部抓住；共同 attack FN 为 0。

**InjecAgent valid proposed-action 150**

| 方法 | F1 | Attack catch | Clean allow | FP | FN | 备注 |
|---|---:|---:|---:|---:|---:|---|
| TS-Guard ToolSafe Guard | 0.994 | 1.000 | 0.983 | 1 | 0 | 已完成，接近饱和 |

**当前结论**

- 不能 claim “AuthDAG 替代或整体超过 TS-Guard”。TS-Guard 本身就是强 7B local guard，并且在 InjecAgent valid150 上几乎饱和。
- AuthDAG 当前最强价值是作为 learned guard 的 authorization/source consistency complement：在 AgentDojo 489 上显著补齐 TS-Guard 的漏报，但 clean allow 略低。
- 如果继续本题，下一步必须做 drift stress test：ToolSafe ASB OPI 或 AgentDyn。若 TS-Guard 在外部 slice 上仍接近饱和，本方向只能收敛为 verifier / supervision / ensemble layer，创新空间偏小。

---

## Resolution（关闭议题时必填）

> Status 切到 `Resolved` 时，本节必须全部填好；否则不许关闭。

- **Decision**：
- **Rationale**：
- **Propagated to**：
  - `method.md § X`（写明改了什么）
  - `idea.md § Y`（如有）
  - `EXP-YYYYWww-NNN`（受影响的实验）
- **Closed by**：
- **Closed at**：

---

## 关闭流程（Agent 执行）

1. 校验 `Resolution` 各字段非空。
2. 用 `mv Discussion.md Discussion/Archive/$(date +%F)-<slug>.md` 归档。
3. 从模板重置本文件（保留 Issue Header 骨架，清空 Posts/Resolution）。
4. 在 `method.md` / `idea.md` 受影响章节追加一条 changelog 条目，并反向链回归档路径。
