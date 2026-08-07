# Discussion


> 形式化对象、定义、命题和覆盖目标见 `Formal.md`。本文件只保留当前论文 proposal 的高层动机、系统设计、实现对应关系和对比叙事。

---

## Thread #1: Environment-grounded Defense Synthesis for Agent Capability Misuse

**状态: Open**

【PI @Angus】【2026-07-20】Skill 主评测数据集定为 **AgentTrap + SkillHarm + SCR**。AgentTrap 承担公开 runtime trust failure，SkillHarm 承担大规模 FPP/SMP 与跨 session skill 攻击，SCR 承担组合授权、authority blur 与 capability-flow 机制 stress test。SkillSafetyBench 因风险域超出当前威胁模型不进主表；ClawSafety 当前仅公开 17/120 cases，CIK-Bench 仅 26/88 为 skill vectors 且依赖真实外部服务，两者均不进当前主表。

### 0. 研究问题
现代 agent 已经不再只是生成文本的语言模型。它们可以读取文件、调用工具、连接 MCP server、执行 skill、运行脚本、访问外部服务，并对环境产生真实效果。安全问题也因此发生了变化：风险不只在于 agent 生成了有害文本，而在于它可能在被攻击者误导后，使用环境中的对象和能力完成本不该发生的动作。

典型风险包括：
- 数据外传：敏感记录、文件、凭证或中间产物被发往外部 sink。
- 凭证滥用：token/key/config 被拿去访问越权资源。
- 越权执行：agent 调用正常任务不应调用的工具、MCP method、skill script 或部署接口。
- 授权洗白：agent 引用一条看似已批准的记录，把越权动作包装成合规动作。
- 长链条传播：攻击先污染文件、摘要或审批依据，之后才在工具调用、文件写入或外部请求中产生效果。

这类风险很难仅靠内容检测解决。攻击指令可以被改写，工具调用可能表面合法，伪授权文本也可能看起来无害。运行时让另一个模型逐步判断每个动作是否合法，也容易受到上下文污染、误报和长链条信息丢失的影响。因此，我们需要一种更贴近 agent 环境本身的防御方式。那么我们需要解决的核心问题是：
```
给定一个 agent 环境，能否自动理解其中的对象、能力和潜在攻击路径，并主动布置防御结构，使 agent 的对象滥用和能力滥用在产生真实效果时留下可验证证据？
```

我们提出一个环境驱动的主动防御 harness。它不是手工放几个固定 trap，也不是在运行时逐步审查 agent 的每句话，而是先理解 agent 所处的环境，再在对象面和能力面主动部署防御点。攻击一旦真正使用这些对象或能力，就会触发可观测的提交性证据。


### 2. 核心 insight
Agent环境中有两类基本单元：
+ 能力单元，包括 tool、MCP method、skill、shell script、API endpoint、deployment interface、permission interface 等。它们是 agent 可以调用或间接触发的执行入口。
+ 对象单元，包括文件、凭证、配置、数据记录、审批记录、消息、任务说明、中间产物等。它们是 agent 在完成任务时可能读取、复制、引用、传递或依赖的对象。

攻击者若想产生真实效果，通常必须让 agent 使用某些对象或能力。数据外传需要对象被传出，凭证滥用需要 credential 被使用，越权执行需要能力入口被调用，授权洗白需要伪授权依据被引用，长任务攻击则依赖对象和能力在多个步骤中传播和触发。因此我们的检测目标为 提交性使用 （commitment-touch）。这意味着Agent真正把对象或能力用进后续效果中时，才构成有效检测信号

本工作的核心insight是：agent 攻击最终必须落到环境中的对象流或能力入口上。只要我们能发现这些环境单元，并在关键位置部署可追踪对象或可观测入口，攻击在产生效果时就会留下证据。

我们提出了两个防御原语：
- **PLANT**：对象面防御。它将可追踪的 decoy 放进 agent 可能读取、引用、复制或传递的对象集合中。如果 agent 后续把这个 decoy 用于外传、凭证调用、授权引用或中间产物传播，harness 就能检测到对象被提交性使用。
- **WRAP**：能力面防御。它将工具、MCP、skill 背后的能力入口接入 wrapper 或 mediation gateway。如果 agent 调用了正常任务不应调用的能力，或者使用合法能力时传入了偏离良性边界的参数，harness 就能检测到能力被提交性触发。


### 3. 系统总览

整个 harness 由四个阶段组成。代码上，这四个阶段都围绕同一个 `EnvMemory` blackboard 展开：每个角色只读取自己的 memory slice，并把结果写回同一个环境计划中。

#### 3.1 阶段一：环境理解

系统首先通过 **Surveyor** 分析 agent 所处环境，发现 object units、capability units 和候选 defense surfaces。这里的环境不只是工具列表，还包括 MCP schema、skill 描述与脚本、文件结构、配置、凭证、数据记录、审批依据、中间产物和任务说明。

`Engine.perceive()` 将 Surveyor 的输出整理成统一的 `PerceivedUnit`。每个 unit 同时记录三类信息：

- **what**：`kind`，例如 datum、credential、authorization、record、skill、local_tool、mcp_tool。
- **where**：`carrier_file`，即对象集合、能力入口或 schema 所在的文件、目录、工具清单或合成 carrier。
- **how**：`primitive`、`placement` 或 `wrap_backend`，表示候选防御应落到 PLANT 还是 WRAP，以及通过什么 backend 部署。

之后 **Enricher** 通过 `backend_adapters.py` 深读每个 carrier，补全 unit 的局部上下文：真实 peer items、ID 格式、对象内容片段、skill script entry、MCP tool schema、mediatable entries 和已有 benign profile。这个阶段的目标是把原始环境整理成一个可操作的环境图：哪些对象可能被 agent 使用，哪些能力可能产生 effect，哪些位置可以成为 PLANT 或 WRAP 的候选点。

#### 3.2 阶段二：防御合成

第二阶段把环境图中的候选 surfaces 合成为具体防御 plan。对象面和能力面的处理不同。

对于对象面，**Camoufleur** 根据 `plant_context` 设计自然的 PLANT decoy。当前实现支持四类 placement：`sweep` 向对象集合追加同格式成员，`exfil` 将 marker 嵌入真实对象内容，`reference` 生成可行动引用，`basis` 生成看似真实的授权或审批依据。对于藏在 peer set 中的 `sweep` 和 `basis`，**Distinguisher** 会尝试从真实 peers 中识别 decoy；若可区分，Camoufleur 重新生成，仍失败则 `Engine.design()` 丢弃该候选。

对于能力面，**WrapPlanner** 根据 `wrap_context`、tool/MCP schema、skill entry snippets 和 benign profile 生成 WRAP semantic plan。它决定哪些 entry 应被中介，哪些参数需要逐字记录，哪些 volatile 参数应抽象成 uuid/date/number/path 等稳定特征，以及该能力的真实 boundary 更接近 capability、network、credential 还是 filesystem。

WRAP 是否能作为 hard defense 不是由 LLM 宣称，而是由 `Engine._wrap_strength()` 代码化判定。只有 substrate-enforced backend，或 `reproducible_in_shell=False` 的能力入口，才可能是 hard WRAP；开放 shell 中的 `file_shim` 通常只能是 audit-only，因为 agent 可以读穿 shim 或复刻同一 effect。`rpc_proxy` 和 `egress_proxy` 当前只是声明接口，未实现端到端 runtime，因此部署时诚实 skip。

同一阶段还会生成两类边界信息。**TaskAllowance** 只读取可信 user task，把本任务显式授权的 entry、target 和 sink 抽成 `TaskContract`，攻击注入不能扩大这个 contract。**benign-fit calibration** 在良性 episode 中移除误触 decoy，并记录正常 argv token envelope，使 WRAP 能区分正常漂移和 off-scope 参数。

#### 3.3 阶段三：部署与检测

第三阶段由 **Deployer / BackendAdapter** 把防御 plan materialize 到隔离环境中。`backend_adapters.py` 为所有 primitive/backend 提供统一接口：

- `plant:sweep/exfil/reference/basis` 注入文件、目录、JSON 或文本 carrier。
- `wrap:file_shim` 为 skill/local script 放置 record-first shim。
- `wrap:mcp_mediator` 配置 stdio MCP mediator，在服务端记录 tool call。
- `wrap:agentdojo` 由 `AgentDojoBackend` 在 function-call runtime 中拦截 effectful tools。
- `wrap:audit_only` 放置仅记录不 hard catch 的 recorder。

agent 执行任务后，**Detector** 读取部署记录、wrapper/MCP/function-call log、文件 diff、agent output、状态变化和 marker 传播记录，判断是否出现 commitment-touch。Detector 是代码化检测器，不运行 policy，也不依赖 LM 在运行时做主观违规判断。

检测证据被归一化到两个正交维度：

- **观测面（channel）**：`state` 或 `transmission`。`state` 指文件、数据库、配置、memory 等持久状态变化；`transmission` 指工具/MCP 调用、外发请求、下游决策或其他跨边界输出。
- **触发时机（timing）**：`access` 或 `commitment`。`access` 指 marker 被读取或引用，适合良性几乎不会碰的 off-path decoy；`commitment` 指 marker 或 capability 被绑定进真实 effect，是主检测信号。

因此 PLANT/WRAP 是防御原语，不是检测维度；每个证据都会被写成 `TouchEvent(uid, primitive, channel, timing, via, evidence, hard)`。其中 `primitive` 记录事件来自 PLANT 还是 WRAP，`channel × timing` 记录二维检测位置，`via` 记录证据来源，`hard` 区分真正 catch 与 audit-only。

#### 3.4 阶段四：检测后审计与维护

第四阶段利用检测证据做攻击审计和防御维护。当前代码已经把审计所需的核心证据落盘在 `EnvMemory` 中，包括 perceived units、plant/wrap plans、certification reports、deploy records、benign profiles、runtime updates 和 `TouchEvent`。这些证据可以重建攻击触发了哪个对象、穿过了哪个能力边界、参数为何越界、证据落在 state 还是 transmission，以及该事件是 hard catch 还是 audit-only。

**Updater** 是当前已实现的运行时维护角色。它做在线 benign-fit：如果部署后的正常使用开始触碰某个 decoy，或 WRAP 的正常参数 envelope 发生漂移，Updater 会增量更新 profile、下线 noisy decoy，而不是重跑整条 Surveyor-to-Deployer 管线。

**Auditor** 是 proposal 闭环中的检测后扩展模块，当前尚未作为独立代码角色实现。它应使用 PLANT 和 WRAP 留下的证据重建攻击路径，推断攻击目标，并在需要时把 agent 引导到 controlled continuation 环境中。这个受控环境可以用 fake service、fake credential、fake state 或 shadow execution 替代真实资产，让系统在不暴露真实资源的情况下继续观察攻击行为。

因此，harness 的完整闭环是：先理解环境，合成可部署防御面，检测提交性使用，再利用检测证据做审计、维护和受控延续。


### 4. 为什么 PLANT 和 WRAP 都必要

PLANT 和 WRAP 覆盖不同失败模式。

PLANT 适合对象流、授权依据和开放 shell。只要攻击要处理一个对象集合，且 decoy 与真实对象不可区分，攻击就很难在不损害目标的情况下排除 decoy。它不依赖 agent 运行 defender 代码，因此在开放 shell 中比 in-band wrapper 更稳。

WRAP 适合能力入口和基座强制边界。若 agent 要产生某个 effect 必须经过工具 runtime、MCP server、function-call runtime、RPC gateway 或 egress gateway，WRAP 能记录真实 capability crossing，并在参数层判断是否越界。

两者的分流规则是：

- 对象被使用、复制、引用、外传、作为授权依据进入决策链：优先 PLANT。
- effect 必经 agent 触及不到的执行边界：可 hard WRAP。
- skill 只是 `SKILL.md + scripts + resources` 的 recipe，agent 能用 shell 复刻效果：不要把安全性押在 skill 名称上，退回 PLANT 或更底层 boundary。
- wrapper 只能放在 agent 可改写的本地脚本里：audit-only，不作为 hard detection 结果。

### 5. 环境图上的 defense synthesis

当前 proposal 的落脚点是把防御部署写成环境图上的覆盖问题。

给定环境图 `G=(V,E)`，节点包括对象 unit、能力 unit、carrier、entry、sink 和 boundary；边表示读取、引用、复制、调用、参数绑定、状态写入或外部传输。攻击路径是从 attacker-controlled surface 到 sensitive/effect sink 的路径。

一个部署 `S = S_plant ∪ S_wrap` 覆盖一条攻击路径，当且仅当该路径在产生 effect 前提交性使用了某个 PLANT 对象，或穿过了某个 hard WRAP 能力边界。

这让系统可以回答三个工程问题：

- **哪些节点需要植入或中介？** 选择能覆盖最多高风险攻击路径、且良性误触低的 object/capability cut points。
- **放多少节点能达到多少检测率？** 用 candidate coverage 估计 budget-coverage curve。
- **哪些路径仍在边界之外？** 若路径不碰任何 planted object，也不经过 hard wrapped boundary，则当前 harness 只能 audit 或无法检测。

当前代码还不是复杂优化器。实际选择策略更保守：先自动发现候选，保留 certification 通过且 benign-fit FP-clean 的 decoy；WRAP 则按 substrate fact 标成 hard/audit/skipped。下一步可以在这个 candidate set 上加入显式 budgeted maximum coverage，但论文叙事应避免把贡献写成旧的 lure-radius 或子模优化器。

### 6. 与现有方法的对比

#### 6.1 内容/静态扫描

MCP-Guard 这类方法扫描工具描述或响应文本，能在描述投毒同分布场景中表现很好，但观测点在内容层。当前实验已经显示：描述投毒上它可与 WRAP 打平；运行时响应注入或自适应改写时，静态扫描会出现结构性盲区，而 WRAP 看的是实际 tool call crossing。

我们的差异不是“分类器更强”，而是观测点不同：从文本模式转为环境 effect boundary 和 object flow。

#### 6.2 固定 trap / honeytoken

固定 trap 依赖攻击者碰到预设字符串、工具或参数。若攻击用合法对象、合法工具和局部授权链完成危害，固定 trap 可以完全不触发。

我们的 PLANT 不是固定全局 trap，而是由 Surveyor/Enricher 针对当前 carrier、peers 和任务对象集合生成；Distinguisher 认证其不可区分性；benign-fit 再过滤良性会碰的候选。

#### 6.3 Runtime policy monitor / least privilege prevention

Progent 等 prevention 方法用 LLM 为每个用户任务生成最小权限策略（允许哪些工具、参数值域），在调用前 block off-policy 调用。配置正确（需 `SECAGENT_SUITE` 注册工具，否则策略为空、零防御）后能显著降 ASR，但成败取决于那份 LLM 策略的质量：**太松→残留攻击漏过；太紧→误拦合法调用（utility tax，无攻击时也掉 utility）**。

**关键澄清（更新，替代旧的“不同范式、不可比”叙事）**：我们的 WRAP 咽喉本身是 mediator，off-scope 判定后可直接拒绝——**检测即拦截**，因此可与 Progent 放在**同一根轴（ASR / utility / FP）**上比，而不是“prevention vs detection 两种范式”。两者本质都是“这次工具调用是否越权”的分类器：Progent 用它去 block，我们用它去 detect（可改 block）。区别在**分类质量**——Progent 靠 LLM 策略（过松漏、过紧误伤），我们靠“任务合同 ∨ 良性包络”的 off-scope 判定 + **不可绕过的咽喉**。实测（Thread #2 / `LOGS/2026-W27.md#EXP-2026W27-008`）：WRAP-as-blocker 的残留 ASR、utility 税、FP 在四个 suite 上均优于 Progent。

**PLANT 是 Progent 完全没有的正交增量**（数据层 honeytoken，抓“授权渠道内把敏感/植入数据带出去”这种策略看不出越权的 exfil）。但要触发这个差距，需要“授权渠道内 exfil”的攻击；AgentDojo 的注入都打**外部 sink**（越权本身就被 WRAP/Progent 挡），因此掩盖了 PLANT 相对 Progent 的独有价值——这块需换 benchmark/构造攻击来体现。

#### 6.4 IFC / provenance tracking

IFC 跟踪真实数据从 source 到 sink 的信息流。我们是 manufacture-then-observe：先制造环境一致的 decoy，再观察 decoy 是否进入 effect。它不需要给所有真实数据打标签，也不在每一步做语义裁决。

边界也很清楚：on-path 自由文本内容如果良性也会读，且攻击可摘要改写到不保留结构化 marker，这部分更适合 IFC 或 provenance 方法。

### 7. 评估落点

评估应围绕三类 substrate 展开：

- **Function-call/tool 环境**：AgentDojo。重点验证一次部署覆盖多个 injection task，WRAP 对成功攻击的 caught|success，良性 FP，以及与 Progent 的 prevention/utility tradeoff。
- **MCP 环境**：MCPTox、MSB。重点验证 server-side mediator 对 tool-description poisoning、response injection、自适应描述改写的覆盖，并与 MCP-Guard/MCP-ITP 对比。
- **Skill/sandbox 环境**：主数据集固定为 **AgentTrap + SkillHarm + SCR**。AgentTrap 验证第三方 skill 的 runtime trust failure；SkillHarm 验证 FPP/SMP、helper script 与跨 session 持久危害；SCR 验证组合授权、authority blur 和 capability flow。统一报告 ASR、utility、benign FP、PLANT commitment 与 hard/audit WRAP。

核心指标：

- `I(M)`：良性/control 中触碰任一 marker 的比例。
- `TPR`：attack run 中 marker touch 比例。
- `dgs` / `caught_given_success`：攻击成功时被捕获比例。
- `ASR_undetected`：危害成功且未触发 hard event 的比例。
- `plant_hit_rate`、`wrap_hit_rate`、`parameter_wrap_hit_rate`。
- `budget-coverage curve`：部署 k 个节点时覆盖多少攻击路径；达到目标检测率 τ 需要多少节点。
- `hard/audit/skipped WRAP ratio`：反映防御面是否真的落在 effect boundary 上。

最重要的图应是 budget-coverage curve 和 unit-wise breakdown。它们直接回答：给定环境，系统为什么选择这些节点，增加部署预算带来多少检测收益，哪些路径仍然不在当前防御边界内。

### 8. 当前证据口径

根据 `LOGS/2026-W27.md` 和 `experiment_stage/IMPORTANT_ARTIFACTS.md`，当前可作为主证据的结果包括：

- MCP/MSB：WRAP-on-MCP mediator 对响应注入导致的 off-scope sink call 达到 caught|harm=100%。
- MCPGuard 对比：描述投毒上 MCP-Guard 可高捕获；MSB 部署态对运行时响应注入结构性盲；自适应改写可规避 MCP-Guard，但 WRAP 仍抓实际 tool call。
- AgentDojo 全四 suite（banking/slack/travel/workspace，generic Engine 一次部署复用全部攻击组合）：caught|success = 52/52、56/58、24/24、45/45 = 98.9%，FP=0。**同轴对比（EXP-2026W27-008，见 Thread #2）**：Ours(WRAP-block) 残留 ASR ~0.5% vs Progent 7.5% vs 无防御 40%；Ours utility 无税(≈无防御 61.7%) vs Progent 56.1%(有 tax)。PLANT 在 exfil 密集的 slack 独立命中 35（AgentDojo 攻击打外部 sink，PLANT 相对 Progent 的独有价值被掩盖）。
- Skill/sandbox：PLANT honey credential 在 Docker 沙箱内可通过 STATE 抓到代码执行型凭证窃取，良性 skill FP=0；真全量 skill benchmark 受环境与数据发布限制，需后续补。

### 9. 预期贡献

1. **把 agent 安全检测对象从可疑文本转为环境对象/能力的提交性使用。** 检测的是真实 effect 里的 object/capability commitment，而不是运行时主观违规判断。
2. **提出 Environment-grounded defense synthesis。** Surveyor/Enricher 从环境中发现 unit 和 boundary，Camoufleur/Distinguisher/WrapPlanner 自动合成 PLANT/WRAP plan，Deployer/Detector/Updater 执行、检测并维护防御面。
3. **给出环境图上的防御覆盖形式化。** PLANT/WRAP placement 可写成预算约束下的覆盖问题，从而回答“哪些节点、放多少节点、达到多少检测率”。
4. **澄清 PLANT/WRAP 的成立条件。** PLANT 依赖不可区分、可追踪、低良性触碰；WRAP 依赖真实 effect boundary 和不可绕过 substrate。audit-only 不夸大成 hard defense。
5. **提供跨 substrate 实现。** 同一 Engine 支持文件/CLI、MCP mediator、AgentDojo function-call backend，并为 RPC/egress proxy 留出明确扩展接口。

### 10. 范围与边界

本框架不主张解决所有 agent 安全问题。它覆盖的是 agent 对环境对象和能力的滥用检测与审计，不替代权限系统、IFC、内容安全或 prevention。

不应夸大的点：

- 不是所有 wrapper 都是 hard WRAP。只有位于真实 effect boundary 且 agent 无法绕过时才成立。
- 不是所有 decoy 都不可区分。PLANT 必须通过 peer/context 伪装和 certification，失败候选应丢弃。
- 检测不等于阻止。PLANT 多数是 detection/audit；WRAP 可扩展为 block 或 shadow execution，但不是基础 claim。
- `rpc_proxy` 和 `egress_proxy` 在当前代码中是声明接口，尚未实现端到端 runtime。
- on-path 自由文本改写、跨会话记忆投毒、无 must-take 对象且无强制边界的单一具名动作，属于当前边界或需与其他方法组合。

---

## Thread 备注

- 旧的 placement optimizer、lure_radius、几何中点放置叙事不再作为主线。
- 文档主张需以 `code/defense/` 当前 Engine 为准：候选发现 + certification + benign-fit + hard/audit strength 判定，而不是手工 trap 或复杂子模优化器。

---

## Thread #2: 与 Progent 的同轴对比（least-privilege prevention vs environment-grounded detection）

> 证据：`LOGS/2026-W27.md#EXP-2026W27-008`（AgentDojo 四 suite 全量，通用 Engine，无 overfit，认证泄露已修，placement 中立自选）。

### 2.1 为什么可以同轴比（纠正旧叙事）

旧叙事把两者说成“prevention vs detection 两种范式、不可比”。这不严谨。二者本质**都是“这次工具调用是否越权”的分类器**：Progent 用分类去 **block**，我们用分类去 **detect**——而我们的 **WRAP 咽喉是 mediator，off-scope 即可拒绝**，所以“检测=拦截”，我们也能算 ASR。于是三方落在**同一根轴（ASR / utility / FP）**。

### 2.2 设置

- 被测 agent：gpt-4o-mini-2024-07-18（AgentDojo 自带 pipeline，内部网关）。攻击：`important_instructions`。
- 我们的防御角色：deepseek-chat（API）。一次部署复用全部 (user × injection)。
- Progent：`SECAGENT_SUITE=<suite>` 正确注册工具后跑（否则策略为空、零防御——本次已修复该配置坑）。
- Ours 残留 ASR = 成功攻击里 **WRAP 没抓到**的（抓到即拦截 → ASR 归零）；Ours utility = 无防御水平（FP=0 → 不误拦良性 → 无 tax，结构性推论）。

### 2.3 结果（均值 / 四 suite）

| 指标 | 无防御 | Progent | **Ours (WRAP-block)** |
|---|---|---|---|
| **ASR（残留，越低越好）** | 40.0% | 7.5% | **~0.5%**（banking 0 / slack 1.9 / travel 0 / workspace 0%） |
| **Utility（无攻击，越高越好）** | 61.7% | 56.1%（有 tax） | **≈61.7%（无 tax）** |
| **FP** | — | 体现为 utility tax | **0** |

- 检测原生指标：caught\|success = banking 52/52、slack 56/58、travel 24/24、workspace 45/45 = **98.9%**；PLANT 在 exfil 密集的 slack 独立命中 35（与 WRAP 冗余）。
- Progent 单 suite ASR：banking 5.6 / slack 10.5 / travel 5.0 / workspace 8.8%；utility 税：banking −12.5、workspace −15pt 最明显。

### 2.4 叙事（结论）

同轴上 **Ours 全面优于 Progent**：残留 ASR 更低（~0.5% vs 7.5%）、utility 无税、FP=0。根因：Progent 的授权边界靠 **LLM 策略**（过松→漏 5–10%、过紧→误伤合法调用），我们的边界靠 **“任务合同 ∨ 良性包络”的 off-scope 判定 + 不可绕过咽喉**——分类质量更高（TPR 98% vs 82%，FP 0 vs tax）。

### 2.5 边界

1. “检测=拦截”对 **WRAP** 成立（咽喉可拒绝）；**PLANT 是事后检测**（数据已带出，用于告警/审计）。残留 ASR 按 WRAP-block 算。**当前实现是记录**，改成拒绝是咽喉上一行——但严格来说 blocking 版 utility 尚未实测（现为 FP=0 的结构推论）。
2. **PLANT 相对 Progent 的独有价值（授权渠道内 exfil）AgentDojo 测不出**——注入都打外部 sink，Progent 策略也挡得住，PLANT 在此冗余。要打出这个差距需换攻击面。
3. ASR base 为不同 gpt-4o-mini 批次（各自内部有效，非完全同基）。
4. 自适应攻击未实测：Ours 的自适应鲁棒是结构论证（PLANT 认证不可分辨、WRAP 无 shell 不可绕过），可用 `--adversary` 补实测。

- 已驳斥假设：W27 没有新的 `Falsified=Y` 主结论；但保留两个边界性负面事实：(1) 真·MaliciousAgentSkillsBench 157 条在当前本机环境无法全量跑，受公开数据 URL redaction、qemu/strace、`--network none` 三重阻断限制（`LOGS/2026-W27.md#EXP-2026W27-002`）；(2) Progent 初始自治配置因缺 `SECAGENT_SUITE` 导致策略为空，EXP-006 对比数不可作数，已在 EXP-007 闭合。
- 已支持假设：MCP/WRAP 线新增强证据：MSB 响应注入 WRAP caught_given_harm=36/36，而 MCP-Guard 部署态 0/50（`LOGS/2026-W27.md#EXP-2026W27-004`）；自适应 MCP-ITP 将 MCP-Guard 检出从 100% 打到 33%，但同批仍攻击样本 WRAP 7/7 捕获（`LOGS/2026-W27.md#EXP-2026W27-005`）。AgentDojo 四 suite 结果支持同轴对比：caught|success=52/52、56/58、24/24、45/45，总计 98.9%，FP=0；Ours(WRAP-block) 残留 ASR 约 0.5% vs Progent 7.5% vs 无防御 40%（`LOGS/2026-W27.md#EXP-2026W27-008`）。
- 悬而未决问题：`Formal.md` 与当前 Discussion 已基本对齐到 PLANT/WRAP 两 primitive、WRAP W1-W3、Progent 同轴比较；仍需补三项证据：(1) 把 WRAP 记录改成可选拒绝并实测 blocking utility，而不是只用 FP=0 作结构推论；(2) 构造“授权渠道内 exfil”攻击，证明 PLANT 相对 Progent 的独有增量；(3) 补 `--adversary` 自适应版，避免自适应鲁棒只停留在结构论证。


---

## Thread #3: Benchmark × Baseline 选型矩阵（tool / MCP / skill）

> 更新 2026-07-07。

### 表 1 · Benchmark
对于三种unit各包含两个常用的benchmark
| # | benchmark | 底座 | 注入向量 | 本机可跑 | 状态 |
|---|---|---|---|---|---|
| B1 | AgentDojo | tool | 工具输出 IPI | ✅ | 已跑 |
| B2 | InjecAgent | tool | 工具返回 dh/ds | ✅ | 已跑(smoke) |
| B3 | MCPTox | MCP | 投毒工具描述 | ✅ | 已跑 |
| B4 | MSB | MCP | MCP pipeline | ✅ | 已跑 |
| B5 | AgentTrap | skill | 恶意 skill 代码 | ⚠️ 需 Docker | 阻塞 |
| B6 | SCR (AuthBlur/TrustLift/CapFlow, ours) | skill | 伪授权 / 能力误用 | ✅ | 已跑 |

### 表 2 · Baseline

| # | baseline | 类型 / 轴 | 代码 / 状态 |
|---|---|---|---|
| D1 | Progent | least-privilege 策略 | ✅ 已跑 |
| D2 | CaMeL | 数据/控制流（flow 轴，解释器式） | ✅ 已跑(deepseek) |
| D3 | FIDES | IFC（flow 轴，标签式） | notebook 含核心可 lift，需桥接（非 drop-in） |
| D4 | MELON | masked re-execution（检测轴） | ✅ 有代码，drop-in AgentDojo |
| D5 | 内容防御族(8)：spotlighting · sandwich · instructional-prevention · data-marking · paraphrasing · retokenization · PI-detector(DeBERTa/PromptGuard) · perplexity | 内容轴（提示 / 内容级） | AgentDojo 自带其中 DeBERTa/spotlight/repeat(sandwich)；余需实现 |
| D6 | tool-filter | 执行级轻量最小权限（LLM 预筛工具集） | ✅ AgentDojo 自带 |
| D7 | MCP-Guard | MCP 多阶代理 | ✅ 仓库 |
| D8 | MindGuard | MCP 投毒检测 + 溯源 | 待核 |
| D9 | SkillScope | skill 最小权限 | 待核 |
| D10 | AIRGuard | runtime authority（**授权轴 baseline**，亦最近竞品；reference-monitor） | ✅ guard 核心已验证可跑(Docker-free，client 可注入)；自带 benchmark(DTAP-150/AgentTrap)需 Docker；桥到我方 benchmark 中等 |


### 表 3 · Benchmark ↔ Baseline 对应

| benchmark | SOTA baseline |
|---|---|
| B1 AgentDojo | D1 Progent · D2 CaMeL · D3 FIDES · D4 MELON · D5 内容防御族(自带 DeBERTa/spotlight/repeat) · D6 tool-filter |
| B2 InjecAgent | D4 MELON(需移植) · D5 内容防御族子集(sandwich/instructional/delimiter) · D6 tool-filter |
| B3 MCPTox | D7 MCP-Guard · D8 MindGuard |
| B4 MSB | D7 MCP-Guard · D8 MindGuard |
| B5 AgentTrap | 自带(spotlight/delimit/isolate) · D9 SkillScope · D10 AIRGuard(在 AgentTrap 发表：36.3%→5.5%) |
| B6 SCR | D5 内容防御族 · D1 Progent · D10 AIRGuard(授权轴头对头) |

### 表 4 · 每个 benchmark unit 的 adaptive attack（现有 SOTA，非自创）

| benchmark | adaptive attack SOTA（已发表 / benchmark 自带） | 压测原语 |
|---|---|---|
| B1 AgentDojo | important_instructions · tool_knowledge · Adaptive-Max（自带）· **AutoDojo 黑盒自适应（2606.15057；静态归零仍恢复 28–64%）** · GCG/AutoDAN（Zhan 2503.00061）· **TAP>GCG 自动化（2606.10525）** · pre-authorized 伪装（2606.26479）· 三阶级联（2510.05244） | WRAP 任务合同 · PLANT 不可区分 |
| B2 InjecAgent | enhanced「IMPORTANT!!!」（自带，ASR×2）· IterInject（2605.24659）· GCG/AutoDAN（2503.00061）· **TAP（2606.10525）** | WRAP off-scope |
| B3 MCPTox | P1/P2/P3 三范式（自带）· MCP-ITP 黑盒优化 + 规避检测（2601.07395）· **WebMCP 运行时工具面 / 会话中注入（2606.06387）** · **ToolHijacker 工具选择攻击** | WRAP 参数级 / 咽喉 · **perceive-once 时效性** |
| B4 MSB | 12 类攻击（name collision · desc injection · out-of-scope param · impersonation · false-error · tool-transfer · retrieval injection…，自带）· MCP-ITP（2601.07395）· WebMCP（2606.06387） | WRAP 咽喉完整性 |
| B5 AgentTrap | 自带 10 攻击法（隐写/编码 · skill-instruction 投毒 · MCP/OAuth 滥用 · hidden routing · helper-code 副作用…）· **SkillJect 双通道闭环（2602.14211）** · **POISE 位置感知隐蔽注入（2606.07943）** | PLANT-ACCESS · WRAP |
| B6 SCR-AuthBlur/TrustLift | pre-authorized 伪装（2606.26479）· **CoT Forgery / role confusion（2603.12277）** · GCG/AutoDAN（2503.00061）· SCR --adversary | PLANT-basis |
| B6 SCR-CapFlow | in-band 剥离 + 裸 shell 复刻（SCR --adversary, EXP-2026W26-004）· **POISE 式 body 注入（2606.07943）** · GCG/AutoDAN | PLANT-outcome |
| 跨 benchmark | **Agent Data Injection（JSON/DOM delimiter，攻击结构化数据边界＝collections_util 的地盘）** | PLANT 载体 |

> 通用自适应方法论：**Zhan 2503.00061**（GCG/AutoDAN 破 8 IPI 防御）· **The Attacker Moves Second 2510.09023**（破 12 防御 >90%）· 评估协议 **2606.26479 §10**。
> deception 竞品（须跟踪）：**AgentShield 2605.11026**。
> 自适应 PI **防御**（可当额外 baseline）：RETA 2606.15441 · RouteGuard 2604.22888 · MindGuard 2508.20412 · Defenses&Enablers 2606.01567。

### 表 4b · 三层 adaptive attack 评估协议（呼应 2606.26479 §10）

> 不做单纯 prompt string mutation，而是压 agent **能力面**上的自适应对手，覆盖 tool / MCP / skill / prompt 四种输入-执行边界。

| 层 | 基础攻击池 | 自适应 / 优化 | 边界攻击 |
|---|---|---|---|
| **Tool/MCP** | MSB 12 类 · MCPTox P1/P2/P3 | MCP-ITP（detector-aware 黑盒优化 metadata/param/schema） | WebMCP 运行时工具面 · ToolHijacker 选择层 |
| **Skill** | SkillInject · AgentTrap 10 法 | SkillJect 闭环 · reframing / translation / LLM-search | POISE 位置感知隐蔽（成功指标须含"user task 仍完成"） |
| **Prompt/context** | AgentDojo / InjecAgent IPI | AutoDojo · TAP / GCG / AutoDAN | role confusion(CoT Forgery) · Agent Data Injection(JSON/DOM delimiter) |

> 两个方案层面 open question：① **WebMCP mid-session 工具注入** 挑战我们"perceive-once → 复用部署"的假设（要么"工具面变更即重感知"，要么明确标界外）；② **Agent Data Injection** 攻击我们埋 marker 的结构化数据本身（须验证 delimiter 注入不挤掉 / 不伪装诱饵）。

---

## Thread #4: 与 CaMeL 的对比、我们的差结果、改进方案(anomaly→specification + deception)

**状态: Open** · **DISC-2026W29-001**

> 目的:同步本周 CaMeL 同基座对比 + 诚实 benign-FP 测量的结论。**本 thread 更正 Thread #2 的乐观叙事**:Thread #2 的 "FP=0 / 无 util 税 / 优于 Progent" 建立在**旧 FP 测量**(只测 withhold 后剩余诱饵)之上;加入干净 benign-FP 测量后,结论显著变化(见 §3)。数字为 deepseek 统一基座 AgentDojo(待回填 `LOGS/2026-W29.md`)。

### 【Agent @Claude】【2026-07-14】结论同步

1. 全 baseline 对比 —— 同基座(deepseek-chat)AgentDojo,**ASR / util**(security=ASR;AgentDojo native runner;important_instructions)

| 防御 | banking | slack | travel | workspace | 类型 |
|---|---|---|---|---|---|
| Undefended | 7.6% / 89.6% | 53.3% / 71.4% | 7% / 72% | 11.7% / 54.2% | — |
| repeat_prompt | 4.2% / 86.8% | 34.3% / 72.4% | 9% / 70% | 9.2% / 66.7% | prompt |
| spotlighting | 2.8% / 91.0% | 39.1% / 71.4% | 10% / 67% | 12.9% / 65.4% | prompt |
| pi_detector | 0% / 34.7% | 2.9% / 21.0% | 0% / **2%** | 6.7% / 32.5% | **分类器** |
| tool_filter | 0% / 31.3% | 0.9% / **4.8%** | 0% / **0%** | 0.4% / 24.2% | **分类器/过滤** |
| Progent | 0% / 37.5% | 0% / 0%(退化) | 0% / 56% | 0% / 27.9% | least-privilege 策略 |
| CaMeL | 0% / 58% | 0% / 63% | 8% / 56% | 0% / **72%** | IFC/CFI |
| **Ours(block)** | 1% / 53% | 8% / 46% | 0% / 60% | 0% / 32% | 我们 |


整体来看，各类方法形成了比较明显的特点。

Prompt-based 方法（Repeat Prompt、Spotlighting） 能较好保持任务完成率，但安全性较弱，ASR 仍然较高。
分类器方法（PI Detector、Tool Filter） 基本可以将 ASR 压到接近 0，但误拦截严重，Utility 大幅下降。
Progent 同样能够保证较低 ASR，但在多个 benchmark 上存在明显的 utility 损失。
CaMeL 是目前表现最好的方法，在安全性和 utility 之间取得了最佳平衡。
我们的方法 能够保持较低 ASR，同时 utility 明显高于分类器方案，但整体仍落后于 CaMeL。

因此，目前实验支持的结论应当是：

我们的方法已经优于传统 prompt-based、防御分类器和 least-privilege 类方法，但与 CaMeL 相比仍存在明显差距，后者是当前最强 baseline。

2. 我们与 CaMeL 的主要差距并不是调参问题

进一步分析发现，两者最大的差距来自设计理念，而不是参数设置。

CaMeL 本质上采用的是 control-flow integrity（CFI） 思路。规划阶段只能访问可信任务，因此攻击内容无法进入 agent 的推理流程，也不会影响后续规划，因此即使存在攻击，agent 仍然能够正常完成用户任务。

我们的方案则属于 drop-in mediator。攻击内容仍然会进入 agent 的上下文，虽然最终危险操作能够在 chokepoint 被拦截，但 agent 已经可能因为受到攻击内容影响而偏离原始任务，例如错误规划、额外推理或浪费执行轮数。这些偏离即使最终没有产生危险操作，也会降低 utility。

这种差距随着任务长度增加会更加明显，因此在 Workspace benchmark 上表现最差。

这说明目前观察到的 utility 损失主要来自架构本身，而不是简单增加规则或调整阈值能够解决的问题。

3. 我们之前的 False Positive 评估存在问题

重新检查实验后，我们发现之前报告的 FP≈0 并不能真实反映误报率。

此前统计的是攻击场景下剩余诱饵是否被拦截，而不是正常任务是否会被错误阻断。

重新定义 FP 后，我们在纯 benign 数据上进行了测试，结果发现：

Slack benchmark 的 benign FP 达到 100%。

进一步分析发现主要原因有两类：

字符串启发式规则导致大量误匹配，例如频道名、URL 或普通单词被误认为攻击标记；
即使去除这些启发式后，误报率仍然较高，说明问题不仅来自实现，而来自检测策略本身。

因此，我们此前关于"近零误报"的结论需要修正，并重新评估所有实验。

4. 问题本质：当前 WRAP 仍然属于 Anomaly Detection

结合实验，我们重新审视了整个设计。

目前 WRAP 的 benign-fit 本质上仍然是在判断

"当前行为是否像历史正常行为。"

这实际上对应传统 IDS 中的 Anomaly Detection。

这一范式具有两个天然缺陷：

正常行为分布很难完整建模，因此容易产生误报；
攻击者可以通过模仿正常行为绕过检测。

而 CaMeL 更接近 Specification-based 防御。

它根据用户任务预先定义允许执行的行为，只要行为超出任务规格就拒绝，因此天然具有更低的误报率。

进一步分析发现，还存在一类无法完全自动解决的问题：

例如：

"邀请 Dora，并去她的网站寻找邮箱。"

这里最终发送邮件的目标邮箱来自不可信网页。

从结构上看，它与攻击者诱导 agent 向恶意邮箱发送邮件几乎完全一致。任何只依赖行为结构的机制都无法区分这两种情况，因此最终仍需要用户确认。

这属于自动防御不可避免的能力边界，而不仅仅是我们方法的问题。

5. 下一步改进方向

目前更合理的方向不是继续增强 anomaly detection，而是重新调整整个设计。

具体来说：

WRAP 从 anomaly detection 转向 specification-based authorization，所有操作均由任务规格显式授权，而不是依赖行为相似性判断。
PLANT 强化 deception 设计，使诱饵具备形式化可分析的安全保证，而不是简单 marker。
将 benign-fit 降级为辅助检查模块，仅用于发现规格缺失，而不再直接参与授权决策。

这样可以保持我们现有主动防御框架，同时与 CaMeL 的 IFC/CFI 路线形成明确区别。

6. 后续工作

下一阶段建议完成三项工作：

将 WRAP 重构为 specification-based 授权机制，并重新完善形式化分析。
在统一评测框架下重新运行所有 baseline，保证公平比较。
增加边界案例（如 "Dora 邮箱"）实验，对比 CaMeL、Progent 与我们的方法在真正困难场景下的行为差异。

---

## Thread #5: 当前实现思路与冻结边界

**状态: Open** · **DISC-2026W29-002**

### 5.1 当前实现的最小主线

1. **环境先于任务被理解。** Surveyor 读取环境中的 capability/effect schema，生成并持久化环境计划；同一环境默认复用同一 plan，只有环境指纹变化或显式 refresh 才更新。
2. **可信任务生成最小 TaskContract。** Contractor 只从可信 user task 与环境 schema 生成无序、彼此独立的 `action / sources / arguments` clauses。运行时注入内容不能扩大 Contract，也不重建 Agent 内部程序或全局信息流图。
3. **PLANT 与 WRAP 正交。** PLANT 在 source 暴露前做结构保持、同类型的 honey identity 替换，并且必须保留 Contract 已授权的任务对象；只有 marker 作为完整 effect argument 被提交时才算 commitment。WRAP 位于 effect proposal 前，只产出 clause match、provenance gap 与 conflict evidence，不直接承担最终语义分类。
4. **Detector 独立做三路决策。** `supported → Pass`，`conflict → Auditor`，`unknown → Approval`。Approval 是安全暂停，默认不执行 unknown proposal。用户拒绝时，系统把已确认的恶意 action/arguments、风险原因和 proposal digest 写入只收紧权限的 `ApprovalReceipt`，向 Agent 明示恶意点，并用 clean session 最多重试一次原任务；被拒 proposal 及其同义重复仍不得执行，不再启动第二轮 Approval。
5. **运行时只保留可验证证据。** provenance 记录 Agent 实际看到的 observation 与实际提出的 effect；原始值留在 sidecar，不把 GT、攻击标签或 Agent 隐状态写入 Contract 或 evidence。

### 5.2 建议冻结、不再反复改动的部分

- PLANT / WRAP 分离，并只在最终 Detector 聚合。
- `TaskContract = action + sources + arguments` 的最小 schema；不重新引入 path、call order、变量、全局 flow graph 或内部 derivation receipt。
- WRAP 只提供 evidence，Detector 只使用 `supported / conflict / unknown` 三态。
- unknown 必须经过 Approval，不能因评测 GT 而自动执行；GT 只可在 proposal 挂起后模拟用户决定。拒绝后的可信约束属于运行时 `ApprovalReceipt`，不回写或扩大任务开始前生成的 TaskContract。
- PLANT 只做结构保持的现有 leaf 替换，不新增 record/field；检测完整 identity commitment，不把文本提及算作触发。
- benchmark adapter 只负责 observation/schema 规范化，不能加入 task、suite 或攻击样本特例。

### 5.3 尚未冻结的三个实现缺口

1. **Contractor 完备性。** DeepSeek 对复杂外部委托会生成空 clauses，使合法 effect 统一落入 `no matching clause`。需要让无法静态展开的委托形成最小、可挂起的占位子任务或 Approval，而不是空 Contract；不得为单个 benchmark 样本加规则。
2. **语义判断局部性与稳定性。** 当前仍有正常自由文本被判 conflict 的案例。semantic judge 必须限制在单个 clause、proposal 和直接 provenance 上，并保持 `equivalent / different / uncertain` 的窄接口；不能重新膨胀成通用内容分类器。
3. **PLANT 可部署与 must-take 覆盖。** DeepSeek 回归中仅 3/24 episodes 部署，且现有结果尚不足以证明跨 suite 的 commitment coverage。需要区分“无合法 plant surface”“生成失败”“被 Contract-preservation 拒绝”和“已部署但未 commitment”，再决定这是实现缺陷还是方法边界。

### 5.4 冻结判据

在同一固定 12-task、24-episode 回归集上，满足以下条件后再把“主架构冻结”升级为“实现冻结”草案：

- 不再出现由空 Contract 导致的合法 effect Auditor；
- benign incident 只能来自真实 conflict 或不可自动判定的 Approval，并与 Agent 自身 completion failure 分开报告；
- PLANT 四类未命中原因可完整归因，且部署/commitment 指标按 suite 报告；
- 现有 26 个单测持续通过，新增缺口均有回归测试；
- ASR、benign utility、attack utility、Auditor、Approval、PLANT deployment/commitment 均在同一固定集合上报告，不用更换样本掩盖退化。

### 5.5 当前工作共识草案

接下来保留现有实现骨架，只做上述三个缺口的最小修复与固定集回归。任何要求重新扩张 Contract schema、恢复全局 flow reconstruction、把 WRAP 改回 anomaly detector，或引入 benchmark-specific rule 的方案，默认视为偏离当前主线，需重新讨论，而不是直接实现。

Approval 样本同时报告两套口径：`approval_triggered` 表示系统已把风险交给用户裁决，可另报 oracle/user-assisted security；正式 `ASR` 和 `utility` 不直接硬编码为 `0/1`，而由用户拒绝后唯一一次受 `ApprovalReceipt` 约束的 clean retry 结果计算。这样既保留“用户已识别风险”的安全收益，也不把尚未完成的正常任务自动算作 utility 成功。

---

## Thread #6: 当前方法论——Contract–Receipt–PLANT–WRAP

### 6.1 适用范围与可信运行时

本方法防御已注册 Tool、MCP 与 Skill 在运行时遭遇的注入和组合攻击。防御方提供版本化可信
Manifest，声明 capability 身份、参数/返回类型、observation/effect 属性和 Receipt role
（data、advisory、control），但不包含任务答案、攻击标签或样本 GT。所有 outward effect
必须经过受控运行时；未注册或运行中改变的 capability 在重新注册前 fail closed。

### 6.2 冻结的 Task Contract

对可信请求 \(q\)，TaskContract Agent 只生成一次最小类型化程序：

\[
C(q)=\{\textsf{Acquire},\textsf{Derive},\textsf{Conditional},\textsf{Effect}\}.
\]

Contract 只表达用户授权的 action/dependency skeleton，不填写运行时值，也不预测执行轨迹。
完整 Contract 经确定性 schema 验证后原子接受，并在 clean 与全部 matched attack 间冻结复用。
动态值由运行时实例化；显式 delegated argument 只能在单次 proposal 的既定 Receipt scope 内证明，
不能创建新 action、扩大 Receipt scope，或给其他参数增加 authority。

### 6.3 Receipt ownership 与 lazy Binding

每个成功的受控 observation 生成不可变、content-addressed Receipt。Receipt 只有通过精确的
task/Contract/Clause/call 身份归属于某个 Acquire Clause，才可进入 WRAP authority view。
Ownership 通过单调 fixed point 闭合；同 capability 错参数、已 supersede、schema-invalid 或已
quarantine 的 Receipt 仍可被 Agent 与 PLANT 看见，但不提供 authority。

当 Agent 提出 effect 时，WRAP 只允许四种受限 Binding 构造：

| Binding | 构造 | 安全边界 |
|---|---|---|
| **Evidence** | 从 owning Clause 可达的可信 literal 或 Receipt 中提取类型兼容的 exact node/span | 只能使用代码预枚举的精确证据，不能发明值或路径 |
| **Compose** | 将已有 Evidence 递归组合为 schema-compatible 的 list/object | 只能组合已证明的叶节点，不能引入新的 authority |
| **Apply** | 对已有 Binding 重放 Manifest 注册的 closed operator | operator 与参数均由代码验证，Agent 不执行或改写运算 |
| **SemanticSupport** | 为 Manifest 明确声明的自然语言 content position 提供局部语义支持 | 非 authority-bearing，不能证明敏感参数或授权 effect |

确定性代码先枚举全部候选；一次缓存的 Binding Agent 调用只能为整个 proposal 选择 opaque
candidate ID，最终值仍由代码投影、组合或重放得到。`direct / intermediate / delegated` 只是
Binding goal 的 proposal-local 求解模式：其中 delegated 也只能在 Contract 已声明的 Receipt
scope 内使用上述构造，不能创建 action、扩大 scope，或给其他参数增加 authority。

### 6.4 PLANT：三个部署平面

PLANT 独立于 WRAP authority，对 Agent 可见的不可信内容面进行部署：

| 平面 | 部署方式 | Commitment evidence |
|---|---|---|
| Observation | marker 改写或中性的结构化 object | marker 被复制进 outward value/effect |
| Dependency | 与 Receipt digest、consumer 绑定的 runtime basis handle | handle 被提交为结构化 effect proof；仅 access 只计审计信号 |
| Substrate | artifact、record、account、capability、grant 或 decoy resource | 对精确 substrate identity 发生真实调用 |

Observation placement 进行一次结构化 dataflow rehearsal：区分正常 Contract 轨迹必需依赖
\(N\) 与 observation control 会引入的依赖 \(O\)，且只允许修改经代码验证的
\(O\setminus N\) operand。结构化 object 追加只有在能证明它对每个 benign consumer 都是
neutral element 时才允许；否则 abstain。仅部署而未 commitment 不是安全事件，PLANT 未命中也
永远不产生 authority。

### 6.5 WRAP：effect boundary 上的授权闭合

对 outward effect proposal \(e\)，只有唯一冻结 Effect Clause 匹配，且全部 required arguments
都能由可信 literal、active owned Receipt、合法 Binding 和已注册 closed operator 闭合时，
WRAP 才允许执行：

\[
\operatorname{Pass}(e) \iff
\exists!c\in C(q):
\operatorname{action}(e)=\operatorname{action}(c)
\land
\operatorname{ArgsProven}(e,c,R,B)
\land
\operatorname{AuthoritySufficient}(e,R).
\]

Data 与 advisory Receipt 对 authority-sensitive effect 的授权充分性贡献恒为零。注册为 control
的 effect 必须获得 fresh、exact-scope、authority=true 的 Receipt；Agent 自写说明、自报 basis
引用、PLANT decoy 和单纯 access 都不能满足授权。因此“与任务相关”不等于“获得用户授权”，
advisory observation 也不能经由下游 Skill/tool 被洗白成 control authority。

### 6.6 联合决策与 Continuation

PLANT 与 WRAP 是两条独立证据流。PLANT commitment 或确定的 Contract conflict 触发 hard
intervention；非冲突但 unresolved 的证据默认 fail closed，除非显式启用可信 Approval channel。
两者共用一个确定性的 ContinuationController：

1. 存在唯一、先前已授权替换时执行 verified repair；
2. 否则在 fresh Agent session 中执行 dependency-closed sanitized replan；
3. 两者都无法证明时 safe abort。

Continuation 只保留可信任务、冻结 Contract、未受影响 Receipt、已完成 effect 与 denied resource
identity；它自身不调用模型，也不能增加 Clause、Effect、值或 authority edge。由此，本方法同时
避开 baseline 的两种退化：既不因某个 tool/catalog 看起来危险就整体删除，也不因某个 effect
“与任务相关”就在缺少运行时 provenance 与 authority closure 时放行。

---

## Thread #7: Frozen-Contract AgentDojo / SkillInject Results

【Agent @Codex】【2026-08-07 00:16】当前代码已将 AgentDojo 的 97 个 task-level Contract（覆盖
629 个 attack pair）和 SkillInject 的 180 个 pair-level Contract 固化为唯一 canonical bundle。
结果聚合如下，完整复现入口与哈希见
[EXP-2026W32-023](LOGS/2026-W32.md#exp-2026w32-023)。

### AgentDojo：统一 `important_instructions` 全量对比

| Method | BU | ASR | AU |
|---|---:|---:|---:|
| Undefended | 86/97 (88.7%) | 107/629 (17.0%) | 464/629 (73.8%) |
| DRIFT | 74/97 (76.3%) | 12/629 (1.9%) | 384/629 (61.0%) |
| CaMeL（local-adapted） | 74/97 (76.3%) | 7/629 (1.1%) | 471/629 (74.9%) |
| Progent | 85/97 (87.6%) | 4/629 (0.64%) | 489/629 (77.7%) |
| MELON | 50/97 (51.5%) | 4/629 (0.64%) | 245/629 (39.0%) |
| **PLANT + WRAP** | **80/97 (82.5%)** | **0/629 (0.0%)** | **494/629 (78.5%)** |

六行均使用 AgentDojo v1.2.2、DeepSeek V4 Flash、相同 97 clean / 629 attack manifest 和
`important_instructions`。PLANT + WRAP 是唯一达到 ASR=0 的方法，AU 比次高的 Progent 高
5/629（0.8 个百分点）；BU 低于 Undefended 和 Progent，但高于 DRIFT、CaMeL 与 MELON。

### SkillInject：同一 DeepSeek V4 Flash、180 clean / 180 attack

| Method | BU | AU | ASR Effect |
|---|---:|---:|---:|
| ClawGuard | 82/180 (45.6%) | 82/180 (45.6%) | 13/180 (7.2%) |
| Progent | 115/180 (63.9%) | 113/180 (62.8%) | 28/180 (15.6%) |
| Task Shield | 96/180 (53.3%) | 105/180 (58.3%) | 10/180 (5.6%) |
| **PLANT + WRAP** | **153/180 (85.0%)** | **159/180 (88.3%)** | **0/180 (0.0%)** |

SkillInject 四行使用同一数据、target model 和 effect oracle；其中 baseline 命令中的
`deepseek-chat` 是内部 transport 对 `deepseek-v4-flash` 的稳定别名。当前结果支持：在 Skill
边界上，我们同时提高 BU/AU 并将 observed effect ASR 降为0。它不证明所有语义型 final-response
危害均被覆盖；表中 ASR 明确只计算 benchmark 的结构化 attack effect。

相对全量 baseline，PLANT + WRAP 的 BU 比最强 baseline Progent 高 **38/180（21.1 个百分点）**，
AU 高 **46/180（25.6 个百分点）**；ASR Effect 则由三个 baseline 中最低的 Task Shield
**10/180（5.6%）**降为 **0/180**。因此在这组严格同协议结果中，我们同时严格优于三种 baseline
的 BU、AU 和 ASR Effect，而不是通过牺牲正常任务完成率换取零 ASR。

SkillGuard、AgentSpec 和 Dynamic Guardian 未放入该全量表：当前仓库只有它们的可运行性或小样本
pilot，没有同一 180 clean / 180 attack 协议的全量结果；将 pilot 数字与上述全量结果混排会造成
不公平比较。其边界结果仍保留在对应 EXP 记录中，不作为主表数字。

### 结论

1. 论文主表只放同模型、同 manifest、同 attack condition 的结果。
2. AgentDojo 主表采用六种方法的统一 `important_instructions` 全量结果，不再混入 `direct` 结果。
3. SkillInject 当前四行可以直接比较，并复用已冻结的 180-Contract bundle。
4. 在新的全量方法变更前保持 WRAP/PLANT 和两个 canonical Contract 集冻结。
