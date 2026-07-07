# Discussion

> 形式化对象、定义、命题和覆盖目标见 `Formal.md`。本文件只保留当前论文 proposal 的高层动机、系统设计、实现对应关系和对比叙事。

---

## Thread #1: Environment-grounded Defense Synthesis for Agent Capability Misuse

**状态: Open**

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
- **Skill/sandbox 环境**：SkillInject、MaliciousAgentSkillsBench 风格环境。重点验证 skill-as-shell 分流、PLANT 对凭证/文件/授权对象的捕获，以及 sandbox FS/network 边界能否升级为 hard WRAP。

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

淘汰（不合威胁模型）：ASB（仅 OPI 合，余 DPI/后门/记忆）· tau-bench / ToolEmu（reliability / 欠约束，无注入物）· AgentHarm（用户直接求害）· TaintBench（安卓恶意软件 taint，非 agent）。

### 表 2 · Baseline

| # | baseline | 类型 / 轴 | 代码 |
|---|---|---|---|
| D1 | Progent | least-privilege 策略 | ✅ |
| D2 | CaMeL | 数据/控制流（flow 轴） | ✅ |
| D3 | MELON | masked re-execution | ✅ |
| D4 | 4 轻量（DeBERTa / repeat / spotlight / tool-filter） | 检测 / 提示加固 | ✅ 自带 |
| D5 | MCP-Guard | MCP 多阶代理 | ✅ 仓库 |
| D6 | MindGuard | MCP 投毒检测 + 溯源 | 待核 |
| D7 | SkillScope | skill 最小权限 | 待核 |
| D8 | 内容防御族(8) | 内容过滤 | 部分 |
| D9 | FIDES（可选） | IFC 轴 | 待核 |
| D10 | AIRGuard（竞品/可选） | runtime authority | 待核 |

### 表 3 · Benchmark ↔ Baseline 对应

| benchmark | SOTA baseline |
|---|---|
| B1 AgentDojo | D1 Progent · D2 CaMeL · D3 MELON · D4 4 轻量（· D9 FIDES） |
| B2 InjecAgent | D3 MELON(需移植) · sandwich · instructional-prevention · delimiter · tool-filter |
| B3 MCPTox | D5 MCP-Guard · D6 MindGuard |
| B4 MSB | D5 MCP-Guard · D6 MindGuard |
| B5 AgentTrap | 自带(spotlight/delimit/isolate) · D7 SkillScope |
| B6 SCR | D8 内容防御族 · D1 Progent |

### 表 4 · 每个 benchmark unit 的 adaptive attack（现有 SOTA，非自创）

| benchmark | adaptive attack SOTA（已发表 / benchmark 自带） | 压测原语 |
|---|---|---|
| B1 AgentDojo | important_instructions · tool_knowledge · Adaptive-Max（自带，+10%）· GCG/AutoDAN （Zhan 2503.00061）· pre-authorized 伪装（2606.26479）· 三阶级联（2510.05244） | WRAP 任务合同 · PLANT 不可区分 |
| B2 InjecAgent | enhanced「hacking prompt IMPORTANT!!!」（自带，ASR×2）· IterInject 反馈迭代优化（2605.24659）· GCG/AutoDAN（2503.00061） | WRAP off-scope |
| B3 MCPTox | MCP-ITP 自适应隐式投毒（黑盒优化 + 规避检测，2601.07395） | WRAP 参数级 / 咽喉 |
| B4 MSB | MCP-ITP | WRAP 咽喉完整性 |
| B5 AgentTrap | 自带 10 攻击法：隐写/编码 · skill-instruction 投毒 · MCP/OAuth 滥用 · hidden routing · helper-code 副作用 · persistence… | PLANT-ACCESS · WRAP |
| B6 SCR-AuthBlur/TrustLift | pre-authorized 伪装（2606.26479）· GCG/AutoDAN（2503.00061）· SCR --adversary | PLANT-basis |
| B6 SCR-CapFlow | in-band 剥离 + 裸 shell 复刻（SCR --adversary, EXP-2026W26-004）· GCG/AutoDAN（2503.00061） | PLANT-outcome |

> 跨 benchmark 的通用自适应破防方法论：**Zhan et al. 2503.00061**（NAACL'25，GCG/AutoDAN 破 8 个 IPI 防御）· **The Attacker Moves Second 2510.09023**（梯度/RL/随机搜索破 12 防御 >90%）· 评估协议 2606.26479 §10。
> 相关竞品（deception 路线，须跟踪）：**AgentShield 2605.11026**（Deception-based Compromise Detection）。
