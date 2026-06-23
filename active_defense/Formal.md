# Formal · 主动防御的形式化背景

> 本文件是 **形式化 single source of truth**:记录对象、定义、命题、证明与评测指标。
> `Discussion.md` 负责 idea 与方案设计,涉及数学时引用本文件编号。

---

## 1. 对象与记号

**Affordance。** affordance 指环境提供给主体的"可做动作的可能性"。设 $\mathcal{U}$ 为一次部署中
真实的 affordance 全集(工具、凭证句柄、memory、RAG 文档、MCP capability、文件、动作目标、参数等)。
标记物 marker $m$ 是注入的人工 affordance,满足:

* 与真实 affordance 表层不可区分(同类型、同 schema、同描述);
* 无真实副作用;
* 被插桩,触发即被观测。

设 $\mathcal{M}$ 为候选标记全集,放置 $M\subseteq\mathcal{M}$。agent 看到 $\mathcal{A}_M=\mathcal{U}\cup M$。
执行分两种分布:良性 $\mathcal{B}$(守 scope,按任务记 $\mathcal{B}_t$)与受陷 $\mathcal{C}$(被劫持/组合带偏/spec-violation)。

**commitment-touch(全局统一触碰语义)。** 全文"触碰"统一指**提交性触碰**:把 marker(或带 marker
的载体)**绑入一个会产生效果的动作**——invoke 一个动作、把 marker 绑入外发/特权动作的目标或参数。
**单纯 read / list / 浏览不算触碰。** 记一次执行的提交性触碰集为 $\mathrm{touch}(\rho)\subseteq\mathcal{A}_M$。

**检测器(policy-free)。** 执行 $\rho$ 触发检测当且仅当 $\mathrm{touch}(\rho)\cap M\neq\varnothing$。
检测端不传播标签、不跑违规策略——只判一个触碰集合的交集是否非空。

### 1.1 核心贡献:一条 objective→boundary 连续谱上的统一放置-检测框架

本工作的核心**不是"又一种诱饵"**,而是**第一个统一的诱饵放置形式化**:同一个 policy-free 的
commitment-touch 检测器,作用在一条从 **objective**(攻击者想拿走/外发/选用的对象)到 **boundary**
(攻击者想跨越的授权)的连续谱上。谱上的标记共用同一套 $\delta$-separation(命题 1)、子模覆盖放置
(命题 2)、规避成本下界(命题 3);两端只是命题 3 中不可区分候选集 $S(g)$ 的**论域不同**(见推论 3.1 与 §7),
是**同一命题的两个实例**,而非两种拼接的机制。

> **为什么"合起来"才是贡献。** 拆开看,每一端都能被指认为既有工作的某一层(objective 端 ≈ AgentShield 的
> honeytoken,boundary 端 ≈ honeytool / honey-permissions)。AgentShield 把 honeytool / honeytoken / 参数校验
> 三层**经验性拼接**,没有把它们统一起来的理论。本工作的增量是给出那条统一轴 + 三条共用命题:
> **统一形式化(合起来才有)、boundary 端的理论护城河、跨威胁模型评估**。

谱的两个端点:

* **族 1 · objective-level honeypot $M_{\text{obj}}$(谱的对象端)。** 诱饵放在**攻击目标对象**上:注入本任务
  用不到的假对象/假数据(假凭证、假记录、假目标资源)。提交性触碰 = 该诱饵对象被绑入外发/写外部/授权/删除
  等效果动作的目标或参数。**真实敏感数据从不进入 agent**;触发的永远是"假值被提交使用",不跟踪任何真实源
  (这是它与 IFC 的根本分界,见 §6)。

* **族 2 · boundary-level honeypot $M_{\text{bdry}}$(谱的边界端)。** 诱饵放在**affordance 的角色/授权边界外侧**:
  在 skill / tool / MCP capability 的正常职责边界外注入一个无副作用的诱饵边界动作(假提权、假批准、假执行交接)。
  提交性触碰 = invoke / bind 该未授权诱饵动作。详见 §7。

> **两端分工(基于这条轴重新定性)。**
> * **族 1 = 覆盖完整性的"地板",不是卖点。** 作用有二:(i) 证明统一框架在谱的 objective 端也成立(命题 1
>   近零误报 + 推论 3.1 外发型下界);(ii) 提供与 AgentShield 直接对齐的对照点。只保留**原子 honeytoken**
>   (假 IBAN/email/ID,逐字搬运,TPR≈0.67),**不含任何 source→sink 内容流溯源**(那是 IFC,见 §6)。
> * **族 2 = 全部重量所在(承重墙)。** 卖点收窄到三件 AgentShield / honey-permissions 都没有的东西:
>   ① **几何中点放置**——scope→危险轴上的中点 + 命题 2 子模/贪心;② **规避成本下界**——命题 3 在 boundary
>   action 上的 $\prod_i(1-r_i)$;③ **MCP capability 边界实例化**——把诱饵能力放在 MCP 声明 scope 之外
>   (目前空白领域)。
>
> **统一轴的代价(必须正视)。** 两端的 $\delta$ 性质并不相同:objective 端 $\delta_{\text{obj}}\approx0$ 是
> **by construction**(假 IBAN 良性流程根本不会外发);boundary 端 $\delta_{\text{bdry}}$ 是**待实测的经验量**,
> 很可能非平凡(命题 1')。因此"两族共用命题 1"必须配一句:RQ1 **分两族分别实测 $\delta$**,诚实写出
> "objective 端构造保证、boundary 端实测经验量"。

---

## 2. 近零误报(命题 1)

**定义 1(干扰与覆盖)。**
$$I(M)=\Pr_{\rho\sim\mathcal{B}}[\mathrm{touch}(\rho)\cap M\neq\varnothing],\qquad
  D(M)=\Pr_{\rho\sim\mathcal{C}}[\mathrm{touch}(\rho)\cap M\neq\varnothing].$$
防御目标:$I(M)\approx 0,\ D(M)\to 1$。

**定义 2($\delta$-separation)。** 称放置 $M$ 关于良性分布是 $\delta$-separation,若对任意 $m\in M$,
$\Pr_{\rho\sim\mathcal{B}}[m\in\mathrm{touch}(\rho)]\le\delta$。

**命题 1(近零误报)。** 若 $M$ 是 $\delta$-separation,则 $I(M)\le|M|\delta$。当 $|M|\delta\ll1$ 时误报近零。

**证明。** 令 $A_m=\{\rho:m\in\mathrm{touch}(\rho)\}$,则误报事件 $=\bigcup_{m\in M}A_m$。由并集界与
$\delta$-separation,$I(M)\le\sum_{m\in M}\Pr_{\mathcal{B}}[A_m]\le|M|\delta$。$\blacksquare$

**前提。** 命题 1 成立**当且仅当** $\delta$ 确实小,即放置真的 off-benign-path。$\delta$ 不是天然成立的,
而是放置质量的函数:

* **族 1** 的 $\delta_{\text{obj}}$:良性 agent 不会把一个"任务用不到的假对象"绑进效果动作——这通常容易成立
  (假对象与任务无关)。
* **族 2** 的 $\delta_{\text{bdry}}$:**这是本方法最需实测的量,不可在定义里假设其近零**(见 §7 与命题 1')。

**命题 1'(族 2 的误报不是自动近零)。** 族 2 的近零误报依赖一个**经验前提**:守授权的良性 agent 正常
执行 $\mathcal{B}_t$ 不对授权边界外动作做提交性触碰。但良性 agent 本身存在**无攻击的 spec-violation**
(良性输入下自发越界);设该越界率为 $\beta$,则 $\delta_{\text{bdry}}\gtrsim$(越界且触到诱饵边界动作的比例),
**可能非平凡**。故族 2 的 $\delta_{\text{bdry}}$ 必须由 RQ1 **单独实测**,并允许它 $>0$;若非零则进入 limitation,
而非当作命题 1 的显然推论。(经验背景:已有审计观察到约三成 skill 在良性输入下即违反自身 guardrail。)

**为何 $\delta_{\text{bdry}}$ 大概率远低于该 $\beta$(但非构造性 0)。** 审计观测到的 $\beta\approx29.9\%$ 是 agent
用**真实 affordance** 越自己的 guardrail;而族 2 的诱饵是**预埋、无副作用、本任务根本用不到的假边界动作**,
再叠加 P2 **只认 commitment-touch、不认 read/list**。三重过滤(假动作 vs 真动作、off-path vs 任务内、提交 vs 浏览)
使 $\delta_{\text{bdry}}\ll\beta$,但它仍是经验量、不是构造性的 0。这正是合并框架逼出的更严谨实验设计:
RQ1 须给出 objective 端(构造保证)与 boundary 端(实测)两条独立的 $\delta$ 报告。

---

## 3. 覆盖与放置优化(命题 2)

对攻击目标 $g$,受陷执行会被 $g$ 所需的某些位置吸引(凭证、敏感对象、未授权高权限动作、外发通道)。
记这些候选位置为随机集合 $T_g$(由 $g$ 与上下文决定);放置 $M$ 决定哪些候选被注入为可观测标记。
当且仅当 $M\cap T_g\neq\varnothing$ 时该执行被检测。于是
$$D(M)=\mathbb{E}_{g\sim\mathcal{G}}\,\mathbb{E}_{T_g}[\mathbb{1}\{M\cap T_g\neq\varnothing\}].$$

**命题 2(子模性与贪心保证)。** $D(M)$ 单调子模;在预算 $k\le\varepsilon/\delta$ 下任意 $|M|\le k$ 满足
$I(M)\le\varepsilon$,且贪心达到 $(1-1/e)$ 近似:$D(M_{\mathrm{greedy}})\ge(1-1/e)\,D(M^\star)$。

**证明。** 固定 $g,T_g$,覆盖函数 $f_{T_g}(M)=\mathbb{1}\{M\cap T_g\neq\varnothing\}$ 单调子模(集合覆盖)。
$D(M)$ 是其在 $g\sim\mathcal{G},T_g$ 上的非负线性组合(期望),仍单调子模,标准贪心有 $(1-1/e)$ 保证。
误报由命题 1:$|M|\le k\le\varepsilon/\delta\Rightarrow I(M)\le k\delta\le\varepsilon$。$\blacksquare$

> 两族都套用命题 2,只是 $T_g$ 论域不同:族 1 的 $T_g$ 在外发槽位/目标对象上,族 2 的 $T_g$ 在
> affordance 边界动作上(§7)。

---

## 4. 规避成本(命题 3)

Kerckhoffs 对手:知道系统会注入标记、知道类型分布与放置算法,但**不知道本次部署哪些具体 affordance
是标记**;目标是达成 $g$ 且不触碰任何标记。引入对手不可区分的候选集合 $S(g)\subseteq\mathcal{A}_M$(含真实
与标记),标记密度 $r(g)=|M\cap S(g)|/|S(g)|$。

**假设 B(能力必需 + 交换不可区分)。** 对每个 $g$ 存在 $S(g)$ 满足:(i) 任何成功达成 $g$ 的执行必须对
$S(g)$ 中至少一个 affordance 做提交性触碰;(ii) 在对手可见信息下 $S(g)$ 内真实与标记无可利用区分特征,
故任选其一是标记的概率为 $r(g)$。

**命题 3(单目标规避下界)。** 在假设 B 下,任何成功达成 $g$ 的对手被检测概率 $\ge r(g)$,即
$\Pr[\mathrm{evade}\mid g]\le 1-r(g)$。多步($\ell$ 类能力)下 $\Pr[\mathrm{evade}\mid g]\le\prod_{i=1}^{\ell}(1-r_i)$。

**证明。** 由能力必需性,成功执行必对 $S(g)$ 做第一次提交性触碰;由交换不可区分性,该触碰落在标记上的
概率 $r(g)$,触碰即检测。多步时每步条件于此前未触发仍交换不可区分,概率连乘。$\blacksquare$

**失效条件。** 若标记可被指纹识别,或对手能把 $S(g)$ 缩小到只含真实 affordance,则 $r(g)$ 失效。
**标记合成质量(与真实 affordance 的行为级不可区分)是下界成立的关键前提**(见 §6 的 O3)。

**推论 3.1(族 1 在外发型目标上的下界)。** 设 $g=$"外发某敏感数据"。令 $\mathcal{O}$ 为所有外发动作
目标/参数槽位构成的不可区分候选集合,objective 诱饵密度 $r_{\text{obj}}(g)=|M_{\text{obj}}\cap\mathcal{O}|/|\mathcal{O}|$。
外发必须把内容提交到某槽位(能力必需),且族 1 把诱饵假值混入候选(交换不可区分),故
$\Pr[\mathrm{evade}\mid g]\le 1-r_{\text{obj}}(g)$。

**三命题整体含义:主动注入标记是合理防御——低误报(P1,但族 2 需实测)、可优化(P2)、有可量化规避成本(P3)。**

---

## 5. 评测指标

* 误报率 $I(M)=N(\text{benign runs touching any marker})/N(\text{benign runs})$。
* 检测率 $\mathrm{TPR}=N(\text{attack runs touching any marker})/N(\text{attack runs})$。
* 未检测攻击成功率 $\mathrm{ASR}_{\text{undetected}}=N(\text{harmful outcome without marker trigger})/N(\text{attack runs})$。
* 攻击成功条件下的检测 $\mathrm{dgs}=N(\text{success}\wedge\text{trigger})/N(\text{success})$
  ——优化目标用这个,避免把"被诱饵扰乱致攻击失败"误算成检测。
* Adaptive 规避成功率 $\mathrm{ESR}(g)$:达成 $g$ 且规避所有标记的比例。

---

## 6. 边界:为什么不把 IFC 塞进方法

**主动 thesis。** 本方法是 manufacture-then-observe:埋假物、看假物是否被提交触碰;**运行时不跟踪任何
真实数据/不跑 source→sink 内容流策略**。这是它区别于被动 IFC 的本质。

**据此排除的设计(重要,避免自相矛盾)。** 一种"声明真实敏感源 → 观测其进入上下文 → 当外发参数与已读源
内容覆盖超阈值时触发"的数据流溯源做法,**本质就是 confidentiality taint tracking**:打标真实源、跟踪到 sink、
用一个覆盖阈值作违规策略。它与本方法在族 2 拒绝"标签传播 + 判流"的理由直接冲突——同一个机制不能在一处
当违背 thesis 删掉、在另一处当"补充"留着。

**更硬的理由:它会让族 1 掉进必比 baseline 的同类。** 这种 source→sink 内容流溯源在机制上**就是 Fides /
AgentArmor 那条 IFC 路线**(声明源、跟踪进入上下文、sink 处判覆盖)。而本工作整篇卖点是"policy-free、不传
标签、与 IFC 对立"。留着它不只是族内自相矛盾,更会让 reviewer 直接问"那族 1 跟 Fides 的区别到底是什么"。
**因此族 1 数据载体只保留原子 honeytoken**(假 IBAN / 假 email / 假 ID:逐字搬运、假值出现在外发即触碰、
不跟踪真实源、无阈值策略)。想要改写式外泄的覆盖,就把 IFC(Fides / AgentArmor)摆成**被动 baseline 去对比**,
绝不塞进主动框架。

**对改写式外泄的诚实态度。** "散文式摘要/改写后外发"使诱饵假值不再原样出现,taint 也穿不过 LLM 语义改写
——这是**所有方法共有的威胁上限**,留作 open problem。删掉上述 IFC 式补充与这条 limitation 完全一致:
族 1 只对**原子秘密/对象的提交性外发或选用**给近零误报保证。

### 6.1 开放问题
* **O2(Selector 的循环论证)。** $\delta$ 小依赖准确识别良性授权路径;需论证 marker 相对 allowlist 的
  增量价值(只需粗粒度边界、提供主动信号与溯源、把"是否越权"转成"是否触碰")。
* **O3(指纹抗性 / 伪装保真)。** marker 无副作用 → 行为级可被探测;需把 $\delta$、$r(g)$ 写成合成质量的
  函数,并实测无害探测后 $r(g)$ 的衰减。
* **O-FP(族 2 误报)。** 命题 1' 指出 $\delta_{\text{bdry}}$ 可能非平凡;RQ1 必须单独实测,非零则写入 limitation。

### 6.2 已吸收的实证约束(载体选择)
* **族 1 载体保真度**:不可见 Unicode 标记 / 可见哨兵串因 LLM 转发**不保真复制**而失效(canary TPR=0,
  EXP-2026W25-002)。可行载体是**结构化假标识符**(假 IBAN / email / ID):模型无语义先验可纠正不透明 ID,
  逐字搬运,实测 TPR=0.67 / I(M)=0(EXP-008)。自然语言品牌词扰动会被纠错(EXP-007),不可用。
* **族 2 placement**:per-affordance 边界半径(靠外保守↔靠内激进)需优化:太靠外漏报、太靠内反而扰乱
  攻击链(ASR 崩)。MCTS 搜索 + disruption-aware reward 在 SCR-AuthBlur 上把 dgs 从单点 0.33 提到 0.75、
  I(M)=0(EXP-021/022)。

---

## 7. 族 2:boundary-level honeypot 的形式化

**动机。** 组合攻击(TrustLift / AuthBlur)每步单看都被授权,危害是跨步涌现的,且常常**不是泄露某条数据,
而是授权边界被洗糊**。族 1 的 objective 诱饵不直接覆盖"授权被非法扩张"。

**定义 7.1(授权域与 boundary action)。** 部署的 affordance 可按粒度 $\ell\in\{\text{skill},\text{tool},\text{MCP}\}$
划分。对被包装 affordance $a$,其正常职责范围记 $\mathcal{P}_{\text{auth}}(a)$,边界外但对攻击有吸引力的下游
执行/授权范围记 $\mathcal{P}_{\text{bdry}}(a)$。boundary-level honeypot $m_{\text{bdry}}(a)$ 是注入 $\mathcal{P}_{\text{bdry}}(a)$
一侧的无副作用诱饵动作:形如一次真实的准备/批准/提权/执行交接,但**本任务对 $a$ 的授权并不覆盖它**,且被插桩。

**定义 7.2(检测,policy-free)。** 触发当且仅当 $\mathrm{touch}(\rho)\cap M_{\text{bdry}}\neq\varnothing$,触碰 = 对诱饵
边界动作的**提交性触碰**(invoke / 绑为目标)。检测端不传播信任标签、不跑授权策略;被洗白授权的 agent
"以为自己被授权"而执行 $m_{\text{bdry}}$,从而触发。

**误报(关键,不当显然)。** off-path 直觉是:守授权的良性 agent 知道职责边界,正常执行不触碰
$\mathcal{P}_{\text{bdry}}(a)$。但由命题 1',这只是**经验前提**:良性 agent 存在自发越界,故
$\delta_{\text{bdry}}$ 可能非零。**结论:族 2 的近零误报不是定义推论,而是待 RQ1 实测的命题。**

**放置端 vs 检测端分离。** 授权域划分(决定每个 $a$ 的 $\mathcal{P}_{\text{bdry}}(a)$、往哪个粒度埋诱饵)
**只在离线放置端用一次**(粗粒度、便宜);运行时只判触碰。即:授权分析(若用)只活在放置端,绝不进入
运行时检测。

**覆盖与规避。** 套用命题 2/3,$T_g$ = "达成越权目标必须跨越的边界动作集合";$D(\cdot)$ 单调子模($(1-1/e)$),
规避下界 $\Pr[\mathrm{evade}\mid g]\le 1-r_{\text{bdry}}(g)$,多步 $\le\prod_i(1-r_{\text{bdry},i})$。族 2 与族 1
同构为 manufacture-then-observe,只是诱饵从 objective 换成 affordance boundary action。

**族 2 的三条护城河(卖点收窄)。** boundary action 这一机制本身(假提权/假批准)与 honeytool / honey-permissions
重叠,故族 2 能 claim 的不是"有边界诱饵",而是以下三件既有工作都没有的东西:

1. **几何中点放置。** scope→危险轴上存在一个最优"中点":太靠外(保守措辞)漏报、太靠内(激进措辞)反而
   扰乱攻击链。把每个 affordance 的放置参数化为边界半径,用命题 2 的子模/贪心(+ 黑盒搜索)求解。
   honey-permissions 用风险阈值启发式,无此几何放置理论。
2. **规避成本下界。** 命题 3 给出 $\prod_i(1-r_{\text{bdry},i})$ 的可证下界;AgentShield 纯经验、honey-permissions
   启发式,都无规避成本保证。
3. **MCP capability 边界实例化。** 把诱饵能力放在 **MCP 声明 scope 之外**——据调研目前是空白领域,
   是统一框架在 boundary 端的一个新实例。

**SCR 映射 + 可落地性。**
* CapFlow → 族 1(honey-target / honey-credential 注入 inventory)。
* TrustLift / AuthBlur → 族 2 boundary action。已核实两者 harness 都能注入诱饵边界动作并观测其是否被
  invoke:**AuthBlur** 经 SKILL.md 注入 per-affordance 边界动作 + sandbox 触碰日志(EXP-022 跑通);
  **TrustLift** 把 honey skill 绑定 scan→install 提权边界,仅当 agent 真执行 installer 才装上,检测信号是
  文件系统副作用。族 2 主实验可落地。

**与 IFC 的区别。** 不在运行时传标签/判违规流;授权域划分只离线用一次。相对 AgentArmor(完整 DFG/PDG +
类型系统 + 策略拦截)的根本差异:稀疏、policy-free、主动、有规避下界。
