# Verifiable Authorization-Chain Reasoning for Secure Tool-Using Agents

## 1. 一句话总结（必填）

> 用一句话说明这个 idea 在做什么，以及最核心的价值/改变是什么。

- 一句话：把 agent 的每次高风险 tool call 建模为一条可验证的授权链，并训练一个小型 LLM reasoner 用 symbolic rewards 判断 Fabricated / Escalated / Exceeded / Tainted 四类授权违规，从而在执行前做 allow / warn / block。


## 2. 一段话总结（必填）

> 用一小段话（3–6 句）解释：
> - 解决什么问题 / 满足什么需求
> - 面向谁
> - 大致怎么做（非常高层级）
> - 为什么现在值得做

- 一段话总结：

  Tool-using agents 和 skill ecosystems 的核心安全问题，不只是 prompt injection 本身，而是 agent 经常把 tool return、skill output、advisor 建议、scan 结果等非用户授权内容错误地当成执行依据。这个 idea 面向需要部署多工具、多 skill agent 的研究者和系统开发者，目标是在每次敏感动作前重建 authorization chain，检查动作是否真正由用户授权、是否类型兼容、是否超出 scope、是否经过不可信数据链。方法上，先定义 tool manifest、Authorization DAG、trust/source/scope 规则，再训练一个 7B 级 authorization reasoner 输出结构化 JSON，并用 DAG consistency、scope containment、taint-flow consistency、benchmark label 等可验证信号做 SFT + RLVR。现在值得做的原因是 AgentDojo、InjecAgent、SkillInject、AgentTrap、TraceSafe 等 benchmark 已经证明 agent 轨迹风险真实存在，但现有防御多停留在 prompt filtering、LLM-as-judge、任务对齐或边界拦截，缺少一个可训练、可验证、跨 benchmark 的授权链推理层。


## 3. 一页纸总结（必填，上限约 1 页 A4）

> 可以按下面的提示简要填，不一定每条都要很长。

### 3.1 背景 & 问题

- 当前现状 / 痛点：
  - LLM agents 已经可以调用邮件、文件、浏览器、代码执行、安装、审批、支付等高权限工具。
  - 间接 prompt injection、恶意 skill、tool selection attack、multi-step trajectory attack 会把恶意意图混入正常任务链。
  - 很多失败不是明显 jailbreak，而是 agent 在多步执行中把“发现”“建议”“审查结果”“不可信内容”误当成“授权”。
  - 典型例子包括 `review(X) -> safe -> install(X)`、`scan(workspace) -> found T -> modify(T)`、`web_fetch -> injection -> send_email(attacker)`。

- 为什么现有做法不够好：
  - Prompt-level defense 容易被 adaptive attack 绕过。
  - LLM-as-judge 缺少结构约束，容易给出看似合理但不可验证的判断。
  - 纯 boundary enforcement / least privilege 对简单授权有效，但对条件授权、多步派生、scope 继承和 tainted data-flow 的解释能力有限。
  - 现有 benchmark 分散在 IPI、skill injection、tool selection、trace guardrail 等不同任务上，缺少统一的 authorization reasoning 视角。

### 3.2 目标 & 成功标准

- 这个 idea 成功时，**对谁** 有什么可感知的改变？
  - 对 agent security 研究者：提供一个把多类 agent attack 统一到 authorization-chain violation 的可复现实验框架。
  - 对 agent runtime 开发者：提供一个可插在 tool-call boundary 前的结构化 allow / warn / block reasoner。
  - 对 benchmark 维护者：提供可检查的中间推理标签，而不是只看最终 attack success。

- 粗略的成功指标（可以是定性或定量）：
  - 在 AgentDojo / InjecAgent / SkillInject 至少两个 benchmark 上降低 attack success rate，同时保持 clean task success。
  - Violation type macro-F1 高于 LLM-as-judge 和 prompt-only defense。
  - Structured reasoning validity：JSON parse rate、step existence、DAG consistency、scope consistency 均显著高于 SFT-only。
  - Utility under attack 高于保守 block-all / require-confirmation baseline。

### 3.3 核心方案（High-level）

- 关键思路 / 机制：
  - 把 agent trace 表示为事件序列：`user_task`、tool call、tool return、skill output、intermediate reasoning、proposed action。
  - 每个 tool 有 manifest：
    - `requires`: 执行该 tool/action 需要什么 authorization。
    - `emits`: 执行后产生什么 evidence，而不是自动产生什么 authorization。
  - 定义 Authorization DAG：
    - 用户显式授权可以导出 action authorization。
    - 用户授权可以导出更窄 scope 的子授权。
    - review result、risk advice、target discovered、tool return content 不能导出用户授权。
  - 定义四类 violation：
    - Fabricated：动作驱动力不是 user / authorized source。
    - Escalated：upstream evidence 被错误升级成 downstream authorization。
    - Exceeded：动作参数超出用户授权 scope。
    - Tainted：授权或 sensitive sink 的数据链经过 untrusted source。
  - 训练 Authorization Reasoner：
    - 输入 trace、proposed action、manifest、DAG rules。
    - 输出 required authorization、reconstructed chain、violation flags、decision、brief reasoning。
  - 用可验证奖励训练：
    - R1 Chain Structural Validity：step existence、DAG consistency、flag-chain consistency。
    - R2 Violation Detection Accuracy：与 benchmark / synthetic label 对齐。
    - R3 Decision Quality：attack trace 应 block/warn，benign trace 应 allow，tainted-but-authorized trace 可 warn。

- 有哪些关键设计决策（哪怕还在假设阶段）：
  - 先做 validator，再做 RLVR；没有 validator 时不要直接训练 reasoner。
  - Gold reasoning 可以由强模型生成，但必须经 symbolic validator 过滤或修正。
  - 先覆盖 20-40 个常见 tool/action 类型，避免一开始追求通用 manifest。
  - 把 `warn` 明确定义为“用户授权动作成立，但数据链或证据链存在不可信来源”，避免所有风险都 block。

### 3.4 风险 & 开放问题（可选）

- 最大的不确定性：
  - 不同 benchmark 的 trace schema 差异很大，统一成本可能高于模型训练成本。
  - 现有工作已经在 task alignment、source authorization、data isolation、IFC、least privilege 上快速推进，创新表述必须更精确。
  - RLVR 可能只学会输出格式和标签，而没有学会可迁移的授权链推理。

- 需要先验证的关键假设：
  - 四类 violation 是否足以覆盖主流 multi-tool / multi-skill 风险。
  - Symbolic rewards 是否能显著提升 chain validity 和跨数据集泛化。
  - Authorization reasoner 相比 deterministic boundary enforcement 是否在条件授权、多步派生和 tainted data-flow 场景有优势。


## 4. 相关工作 & 参考文献（ref / papers）

> 用来记录和这个 idea 强相关的 paper / 文章 / 项目，方便以后在 proposal/paper 模式下直接引用。

- Paper / 资料列表（可用「标题 + 链接 + 一句说明」）：
  - [AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents](https://arxiv.org/abs/2406.13352) — 核心 benchmark，可用于 IPI 防御和 utility/security tradeoff。
  - [InjecAgent: Benchmarking Indirect Prompt Injections in Tool-Integrated Large Language Model Agents](https://arxiv.org/abs/2403.02691) — 提供 1,054 个 tool-integrated IPI case，适合做跨工具泛化测试。
  - [Agent Security Bench (ASB): Formalizing and Benchmarking Attacks and Defenses in LLM-based Agents](https://arxiv.org/abs/2410.02644) — 多场景、多攻击、多防御 benchmark，可作为广义 agent security 对照。
  - [The Task Shield: Enforcing Task Alignment to Defend Against Indirect Prompt Injection in LLM Agents](https://arxiv.org/abs/2412.16682) — 强相关 baseline，强调每个指令和 tool call 是否服务用户目标。
  - [RTBAS: Defending LLM Agents Against Prompt Injection and Privacy Leakage](https://arxiv.org/abs/2502.08966) — IFC-style baseline，和本 idea 的 taint / trust-chain 设计直接相关。
  - [Adaptive Attacks Break Defenses Against Indirect Prompt Injection Attacks on LLM Agents](https://arxiv.org/abs/2503.00061) — 说明必须评估 adaptive attack，否则防御说服力不足。
  - [Prompt Injection Attack to Tool Selection in LLM Agents](https://arxiv.org/abs/2504.19793) — tool selection 被污染的代表性攻击，可测试 Fabricated / Escalated 分类。
  - [AgentVigil: Generic Black-Box Red-teaming for Indirect Prompt Injection against LLM Agents](https://arxiv.org/abs/2505.05849) — 黑盒 red-teaming 攻击，可作为 adaptive stress test。
  - [Skill-Inject: Measuring Agent Vulnerability to Skill File Attacks](https://arxiv.org/abs/2602.20156) — skill-file attack benchmark，和 multi-skill authorization mismatch 高度相关。
  - [AgentTrap: Measuring Runtime Trust Failures in Third-Party Agent Skills](https://arxiv.org/abs/2605.13940) — runtime skill trust failure benchmark，适合验证 skill output 不等于 authorization。
  - [TraceSafe: A Systematic Assessment of LLM Guardrails on Multi-Step Tool-Calling Trajectories](https://arxiv.org/abs/2604.07223) — 中间轨迹 guardrail benchmark，适合测试 structured reasoning validity。
  - [MiniScope: A Least Privilege Framework for Authorizing Tool Calling Agents](https://arxiv.org/abs/2512.11147) — least-privilege baseline，需直接比较 permission minimization 与 authorization reasoning。
  - [A Framework for Formalizing LLM Agent Security](https://arxiv.org/abs/2603.19469) — 相关形式化框架，尤其是 task alignment、action alignment、source authorization、data isolation。
  - [ClawGuard: A Runtime Security Framework for Tool-Augmented LLM Agents Against Indirect Prompt Injection](https://arxiv.org/abs/2604.11790) — runtime boundary enforcement baseline。
  - [Reinforcement Learning with Verifiable Rewards Implicitly Incentivizes Correct Reasoning in Base LLMs](https://arxiv.org/abs/2506.14245) — RLVR 机制依据，用于支撑 symbolic reward 训练 authorization reasoning。
  - 其它：后续需要补一个 100 篇文献矩阵，按 Attack / Benchmark / Defense / Formal Security / RLVR 五类整理。


## 5. TODO & 下一步（可选，但推荐）

> 把 idea 阶段已经明确的「下一步行动」列出来，方便后面直接推进。

- 接下来 1–3 个可以做的小步骤：
  1. 在 `method.md` 形式化 Authorization DAG、trust lattice、scope containment 和 reward functions。
  2. 新建 `data/authorization_trace_schema.json`，定义统一 trace / manifest / proposed action / label schema。
  3. 实现 `code/validator.py` 的最小版本，先支持 50 条手写或半自动构造的 authorization traces。

- 需要先回答的问题（再深入前要搞清楚什么）：
  - `warn` 与 `block` 的边界如何定义，尤其是用户授权动作但 body 含 untrusted content 的情况？
  - 哪些 benchmark 有完整 trace，哪些只有最终输入输出，需要额外重放 agent 才能得到 authorization chain？
  - 在已有 Task Shield / RTBAS / MiniScope / ClawGuard 等 baseline 下，本方法的优势场景到底是条件授权、多步 evidence laundering，还是跨 benchmark 泛化？

