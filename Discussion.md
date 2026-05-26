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

【Agent@Codex】【2026-05-24】

按用户要求已清理此前与核心方向无关的探索产物，并保留历史讨论上下文。当前工作区只保留精炼后的 authentication DAG 版本：`idea.md`、`method.md`、`code/authentication_dag/validator.py`。后续如果继续，应在上述历史上下文基础上叠加讨论，而不是覆盖已有记录。

【Agent@Codex】【2026-05-24 23:20】

重新阅读本议题后，当前主线应理解为：不一定换题，而是把题目收敛为 **Authentication DAG + small local dangerous tool-use guard**。Discussion 里已经给出下一步：先验证 symbolic validator 是否有效；如果 validator 不能稳定检查 chain validity / violation labels，就不进入 SFT / GRPO。

小模型仍可作为创新点，但前提是它不是替代 DAG，而是利用 DAG validator 提供监督、过滤或一致性检查。合理 framing 是：Authentication DAG 负责定义可验证授权边界；small local guard 负责在高频 tool-call boundary 上低延迟、低成本、隐私友好地近似闭源 judge 的安全判断。

因此下一步不是换新 idea，而是做 validator gate：

- symbolic validator vs sensitive-tool blocker；
- attack catch for A1/A2/A3；
- clean allow for benign high-permission tool use；
- warn precision/recall for D1-only cases；
- 若 validator 通过，再进入 small-model SFT/RL 对照。

已将该主线同步到 `idea.md` 和 `method.md`。

【Agent@Codex】【2026-05-25 09:22】

已按用户要求重新拉取公开 benchmark / baseline，不再使用自创或模拟数据，记录为 `LOGS/2026-W21.md#EXP-2026W21-001`。已拉取：ToolSafe、AgentDojo、AgentDyn、ClawGuard、CaMeL。当前 primary public benchmark 使用 ToolSafe 官方 `TS-Bench/agentdojo-traj/{workspace,travel,slack,banking}.json`。

初步组装结果：ToolSafe AgentDojo 官方 step 共 1220 条，其中 sensitive/action-bearing in-scope step 489 条，unsafe=342、safe=147。当前 authdag validator 与 sanity baseline 对比：sensitive blocker F1=0.823、attack catch=1.000、clean allow=0.000；history injection filter F1=0.848、attack catch=1.000、clean allow=0.163；authdag validator F1=0.755、attack catch=0.623、clean allow=0.939、precision=0.959。

解释：validator 已经体现出 authentication DAG 的核心差异，即不再简单阻断所有 sensitive tool，而是保留大量合法高权限动作；但 recall 明显不足，下一步要分析 FN，补通用 scope/derived-grant 规则。SOTA baseline 复现状态也已记录到 `code/results/baseline_reproduction_status.md`：TS-Guard 需要 checkpoint/GPU；CaMeL 需要 API 和 full AgentDojo run；ClawGuard 需要 semantic tool adapter 或限制到 file/command/network slice，不能用 proxy 冒充官方结果。

【Agent@Codex】【2026-05-25 09:35】

已按本议题规划继续验证 symbolic validator，记录为 `LOGS/2026-W21.md#EXP-2026W21-002`。关键修正不是 benchmark 特化，而是补全 Authentication DAG 的 scope 条件：用户授权必须同时覆盖 action verb 和 object type；untrusted taint span 只覆盖外部 instruction block，不能把后续整个 trace 都污染。

ToolSafe AgentDojo 官方 trajectory 结果已经支持当前 idea 的核心可行性：in-scope sensitive/action steps n=489，`authdag_scope_validator` 达到 F1=0.986、attack catch=0.994、clean allow=0.946、precision=0.977；相比 `sensitive_blocker` 的 clean allow=0.000 和 `history_injection_filter` 的 clean allow=0.163，DAG validator 确实提供了更好的 safety/utility tradeoff。

同时做了 ToolSafe AgentHarm 官方 trajectory 边界验证：in-scope n=190，`authdag_scope_validator` 只有 F1=0.110、attack catch=0.059、clean allow=0.964。这个负结果说明该 idea 不能被写成通用 harmful-content policy guard；它适合定位为 indirect tool-call authorization guard，或作为 small local dangerous tool-use guard 的 authorization/scope consistency layer。若要覆盖 direct harmful user intent，需要额外 harm-policy 信号。

剩余问题：SOTA 对比仍未完成。当前数字只能说明 validator 对 sanity baselines 有价值，不能声称超过 TS-Guard / CaMeL / ClawGuard。下一步应优先复现 TS-Guard checkpoint 或 CaMeL full AgentDojo run；若 SOTA 复现卡住，需要明确按论文设定重建并标注为 paper-faithful reconstruction。

【Agent@Codex】【2026-05-25 11:30】

按用户纠偏，当前主任务从“全量运行 ToolSafe/TS-Guard”改为“从公开 benchmark 中筛选符合 threat model 的样本，再在这些样本上比较 baseline”。已记录为 `LOGS/2026-W21.md#EXP-2026W21-003`，artifact 为 `code/results/threat_model_benchmark_inventory.md`。

当前 benchmark inventory 结论：

- ToolSafe AgentDojo trajectory 是立即可用主集：1220 official step 中有 489 条 sensitive/action-bearing step，unsafe=342、safe=147，符合 benign user + indirect injected context + sensitive action 的主 threat model。
- InjecAgent 是最强补充来源：1054 base cases / 1054 enhanced cases，明确由 benign user tool response 携带 attacker instruction；但它没有 precomputed step trajectory，需要做 proposed-action protocol 或跑 agent rollout。
- ToolSafe ASB OPI 可作为次级 stress slice；DPI 因 user prompt 自身被污染，不应作为当前 AuthDAG 主实验。
- AgentDojo / AgentDyn 源码 suites 符合 threat model，但需要 end-to-end rollout 才能得到可比较轨迹。AgentDyn v1 包含 shopping/github/dailylife 等更开放场景，可作为后续泛化验证。

因此，不应把 full 1220 ToolSafe 或 AgentHarm 当作主指标。API guard / TS-Guard / 我们的方法都应先对齐到同一个 threat-model slice；全量结果只作为参考或边界分析。

【Agent@Codex】【2026-05-25 11:45】

已完成 ToolSafe GPT-4o guard 与 AuthDAG 在同一 489 条 threat-model slice 上的公平对比，记录为 `LOGS/2026-W21.md#EXP-2026W21-004`，结果表在 `code/results/toolsafe_slice_method_comparison.md`。

关键数字：GPT-4o guard clean-drop 口径 n=428、dropped=61、F1=0.904、attack catch=1.000、clean allow=0.523；parse-error-block 部署口径 n=489、F1=0.898、attack catch=1.000、clean allow=0.469。AuthDAG scope validator 在同一 489 条上 F1=0.986、attack catch=0.994、clean allow=0.946、precision=0.977，只漏 2 条，误杀 8 条。

当前解释：GPT-4o guard 很保守，几乎不漏攻击，但对合法高权限动作误伤明显；AuthDAG 的 action-scope/source check 正好提供了更好的 utility preservation。这是目前支持 idea 有效性的最强结果。仍需补充：TS-Guard local model 对齐到同一 slice；InjecAgent 或 ToolSafe ASB OPI 上的泛化验证。

【Agent@Codex】【2026-05-26 17:40】

已补齐 TS-Guard local 7B baseline 和 InjecAgent proposed-action 泛化测试，记录为 `LOGS/2026-W21.md#EXP-2026W21-005`。结果需要下调当前 claim：AuthDAG 不能被写成“全面替代 TS-Guard”的 standalone SOTA guard。

关键数字：

- ToolSafe AgentDojo 489 slice：TS-Guard local F1=0.945、attack catch=0.904、clean allow=0.979；AuthDAG scope validator F1=0.986、attack catch=0.994、clean allow=0.946。
- 重叠分析：TS-Guard 漏掉的 33 个 attack，AuthDAG 全部抓住；AuthDAG 漏掉的 2 个 attack，TS-Guard 全部抓住；共同漏报为 0。
- InjecAgent base rollout 1054 条中，只有 150 条是 valid proposed-action slice；TS-Guard local 在这 150 条上 F1=0.994、attack catch=1.000、clean allow=0.983，接近饱和。

当前判断：我们的优势不是“小模型本地化”，因为 TS-Guard 本身也是 7B local guard；也不是在所有数据集上显著超过 learned guard，因为 InjecAgent proposed-action slice 上 TS-Guard 已经几乎满分。剩余可辩护贡献是：显式授权/来源约束可作为 learned trajectory guard 的高召回补充和可验证监督信号，尤其在 AgentDojo indirect tool-call slice 上补全 TS-Guard 漏报。

下一步必须做 drift stress test：优先跑 ToolSafe ASB OPI 89 条和/或 AgentDyn rollout。如果 TS-Guard 在这些外部 slice 上仍接近饱和，本议题应收敛为 verifier / supervision / ensemble layer，而不是 standalone defense paper。

【Agent@Codex】【2026-05-26 17:55】

按用户要求，将当前四方案对比结论以表格形式补充到本议题。证据仍以 `LOGS/2026-W21.md#EXP-2026W21-004` 和 `LOGS/2026-W21.md#EXP-2026W21-005` 为准；未完成的格子明确标为 N/A，不用未跑实验填充。

**ToolSafe AgentDojo 489 threat-model slice**

| 方法 | F1 | Attack catch | Clean allow | FP | FN | 解释 |
|---|---:|---:|---:|---:|---:|---|
| GPT-4o ToolSafe Guard | 0.898 | 1.000 | 0.469 | 78 | 0 | parse-error 视为 block；极保守，误杀高 |
| GPT-5.5 ToolSafe Guard | 0.871 | 1.000 | 0.303 | 101 | 0 | 263/489 被 API cyber filter 拦截；不是纯模型 judge |
| TS-Guard local | 0.945 | 0.904 | 0.979 | 3 | 33 | 官方 local learned guard；低误杀但漏报较多 |
| AuthDAG scope validator | 0.986 | 0.994 | 0.946 | 8 | 2 | 当前 symbolic validator；高召回，误杀略高于 TS-Guard |

**InjecAgent valid proposed-action 150 slice**

| 方法 | F1 | Attack catch | Clean allow | FP | FN | 状态 |
|---|---:|---:|---:|---:|---:|---|
| TS-Guard local | 0.994 | 1.000 | 0.983 | 1 | 0 | 已完成，接近饱和 |

更新后的共识：

- 当前不能 claim “AuthDAG 超越/替代 TS-Guard”。TS-Guard 是强 7B local baseline，且在 InjecAgent valid150 上几乎满分。
- AuthDAG 目前最强证据是 ToolSafe AgentDojo 489 上对 TS-Guard 漏报的补全：TS-Guard 的 33 个 FN 全被 AuthDAG 抓住，二者共同 attack FN 为 0。
- 因此下一阶段若继续本题，应改成验证 “authorization/source constraints 是否能作为 learned guard 的 complement / verifier / supervision signal”，并通过 ASB OPI 或 AgentDyn 检查 TS-Guard 是否存在 cross-domain drift。但是这样的创新点会很小。

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
