# Discussion · 当前 Active 议题

## Thread #1：现有 agent 防御几乎都是“观察”，即给已有行为打标签来判断危害，而不是“主动”防御

在我们的方案中，defender 主动在 agent 的能力空间中注入标记物。标记物被触碰或传播本身就是一个接近零误报的信号，因为 agent 的正常行为不应触碰这些标记；同时，标记被触发后也天然带有溯源信息。

这里对该方案进行形式化。在这个 idea 中，我们需要解决的问题是：“标记该往哪种、种多少、能不能被攻击者绕过”。因此，这里定义三个量：

* 良性干扰 $I(M)$：正常任务执行触碰到任意标记 $m\in M$ 的概率，目标是 $\approx 0$。这是 defender 的期望，即正常流程不应触碰标记物。
* 检测覆盖 $D(M)$：被劫持、被组合带偏或发生 spec-violation 的 agent 执行触碰到任一标记的概率。
* 规避成本 $E(M)$：一个知道有标记、但不知道具体标记在哪里或是什么的攻击者，在不碰任何标记的前提下达成目标所必须付出的额外代价。

因此，主动防御的目标是：给定 agent 的能力空间和攻击目标分布，求 $M$ 以最大化 $D(M)$，同时满足 $I(M)\le \varepsilon$，并刻画 $E(M)$ 随放置密度和结构变化的下界。

---

## 对象与记号

**Affordance 空间。** Affordance 指环境提供给一个主体的“可做的动作可能性”，比如门把手 afford “拉/推”动作。

设 $\mathcal{U}$ 为一次部署中真实的 affordance 全集，包括工具、凭证句柄、memory 条目、RAG 文档、MCP capability、文件路径、动作目标、参数等。一个标记物 marker $m$ 是注入的人工 affordance，满足：

* 在形式上与真实 affordance 不可区分，即同类型、同 schema、同表层描述；
* 无真实副作用；
* 被插桩，即触发标记物会被观测。

设 $\mathcal{M}$ 为候选标记全集。标记物放置动作是 defender 为 agent 注入的有限子集 $M\subseteq\mathcal{M}$。agent 看到的 affordance 空间是：

$$\mathcal{A}_M=\mathcal{U}\cup M.$$

一次执行 $\rho$ 是 agent 在某任务上的一次运行，它诱导一个触碰集：

$$\mathrm{touch}(\rho)\subseteq\mathcal{A}_M.$$

其中，触碰动作包括 invoke、read、write 或绑定为动作目标的 affordance。那么 agent 的执行被分为两种分布：

* 良性分布 $\mathcal{B}$：正常使用下的执行，即良性任务、守 scope 的行为；按任务记为 $\mathcal{B}_t$。
* 受陷分布 $\mathcal{C}$：被劫持、被组合带偏或发生 spec-violation 的执行。

检测器定义为：执行 $\rho$ 触发检测当且仅当：

$$\mathrm{touch}(\rho)\cap M\neq\varnothing.$$

---

## 干扰与覆盖

**定义 1：干扰与覆盖。**

良性干扰，也就是误报率 FPR，定义为：

$$I(M)=\Pr_{\rho\sim\mathcal{B}}\left[\mathrm{touch}(\rho)\cap M\neq\varnothing\right].$$

检测覆盖，也就是检测率 TPR，定义为：

$$D(M)=\Pr_{\rho\sim\mathcal{C}}\left[\mathrm{touch}(\rho)\cap M\neq\varnothing\right].$$

防御的目标为：

$$I(M)\approx 0,\qquad D(M)\to 1.$$

**定义 2：$\delta$-separation。**

当一个守规矩的 agent 正常做任务 $t$ 时，即 $\rho\sim\mathcal{B}_t$，它触碰到标记 $m$ 的概率不超过 $\delta$，形式化为：

$$\Pr_{\rho\sim\mathcal{B}_t}\left[m\in\mathrm{touch}(\rho)\right]\le \delta.$$

**命题 1（近零误报）。** 设放置 $M$ 关于良性分布 $\mathcal{B}$ 是 $\delta$-separation，即对任意 $m\in M$，都有：

$$\Pr_{\rho\sim\mathcal{B}}\left[m\in\mathrm{touch}(\rho)\right]\le \delta.$$

则该标记检测器的误报率满足：

$$I(M)=\Pr_{\rho\sim\mathcal{B}}\left[\mathrm{touch}(\rho)\cap M\neq\varnothing\right]\le |M|\delta.$$

因此，当 $|M|\delta\ll 1$ 时，误报率近零。

**Proof.** 对每个 $m\in M$，令：

$$A_m=\left{\rho:\ m\in\mathrm{touch}(\rho)\right}.$$

也就是说，$A_m$ 表示良性执行 $\rho$ 触碰到标记 $m$ 的事件。良性执行触发误报当且仅当它触碰到至少一个标记，因此有：

$$\left{\rho:\ \mathrm{touch}(\rho)\cap M\neq\varnothing\right}=\bigcup_{m\in M}A_m.$$

于是，根据 $I(M)$ 的定义：

$$I(M)=\Pr_{\rho\sim\mathcal{B}}\left[\mathrm{touch}(\rho)\cap M\neq\varnothing\right]=\Pr_{\rho\sim\mathcal{B}}\left[\bigcup_{m\in M}A_m\right].$$

由并集界 union bound 可得：

$$\Pr_{\rho\sim\mathcal{B}}\left[\bigcup_{m\in M}A_m\right]\le \sum_{m\in M}\Pr_{\rho\sim\mathcal{B}}\left[A_m\right].$$

又因为 $M$ 关于良性分布 $\mathcal{B}$ 是 $\delta$-separation，所以对任意 $m\in M$，都有：

$$\Pr_{\rho\sim\mathcal{B}}\left[A_m\right]=\Pr_{\rho\sim\mathcal{B}}\left[m\in\mathrm{touch}(\rho)\right]\le \delta.$$

因此：

$$I(M)\le \sum_{m\in M}\Pr_{\rho\sim\mathcal{B}}\left[A_m\right]\le \sum_{m\in M}\delta=|M|\delta.$$

当 $|M|\delta\ll 1$ 时，$I(M)$ 也很小，因此该检测器在良性分布上的误报率近零。

这个命题的成立是有条件的，即放置 $M$ 是 off-task 的，在理论上 agent 触碰这一 task 无关标记的概率非常小。因此，误报由两个因素控制：第一，marker 放得越多，正常 agent 误碰任意一个 marker 的机会越大；第二，$\delta$ 越小，正常 agent 越不可能碰它。因此，这种主动防御方案具有理论上的 near-zero false positive。

---

## 放置问题

为了将检测覆盖 $D(M)$ 写成一个可优化的结构，我们引入一个轻量的“位置-吸引力”假设。对攻击目标 $g$，受陷执行并不是任意触碰 affordance，而是会被 $g$ 所需的某些位置、类型或能力吸引，例如凭证句柄、敏感 memory、私有文档、高权限动作或外部输出通道。受陷执行是指在攻击、诱导或组合性失效影响下，agent 产生了违反原始任务意图、安全策略或授权边界的执行轨迹。

记这些可能被触碰的候选位置集合为随机变量 $T_g$。这里 $T_g$ 由攻击目标 $g$ 及执行上下文决定，而 defender 的放置 $M\subseteq\mathcal{M}$ 只决定哪些候选位置被注入为可观测的标记。

因此，当且仅当放置 $M$ 覆盖了受陷执行会触碰的候选集合 $T_g$，即 $M\cap T_g\neq\varnothing$，该执行被检测到。于是检测覆盖可以写为：

$$D(M)=\mathbb{E}*{g\sim\mathcal{G}}\mathbb{E}*{T_g}\left[\mathbb{1}\left{M\cap T_g\neq\varnothing\right}\right].$$

其中，$\mathcal{G}$ 是攻击目标分布，$\mathbb{1}{\cdot}$ 是指示函数。这个形式化将 marker placement 看成一个覆盖问题：选择有限的标记集合 $M$，使其尽可能覆盖受陷执行可能触碰的位置集合 $T_g$。

**命题 2（子模性与贪心保证）。** 在上述位置-吸引力假设下，$D(M)$ 是关于放置集合 $M$ 的单调子模函数。若每个标记关于良性分布都是 $\delta$-separation，并且放置预算 $k$ 满足：

$$k\le \frac{\varepsilon}{\delta},$$

则任意满足 $|M|\le k$ 的放置都有：

$$I(M)\le \varepsilon.$$

因此，预算约束下的最优放置：

$$M^\star=\arg\max_{M\subseteq\mathcal{M},\ |M|\le k}D(M)$$

满足：

$$I(M^\star)\le \varepsilon.$$

同时，由于 $D(M)$ 是单调子模函数，在基数约束 $|M|\le k$ 下，标准贪心算法可以达到 $(1-1/e)$ 的近似最优覆盖，即：

$$D(M_{\mathrm{greedy}})\ge \left(1-\frac{1}{e}\right)D(M^\star).$$

**Proof.** 对固定的 $g$ 和 $T_g$，定义覆盖函数：

$$f_{T_g}(M)=\mathbb{1}\left{M\cap T_g\neq\varnothing\right}.$$

该函数是单调的：如果 $A\subseteq B$，那么 $A$ 能覆盖的 $T_g$，$B$ 也一定能覆盖，因此：

$$f_{T_g}(A)\le f_{T_g}(B).$$

该函数也是子模的：当已有放置集合更大时，新增一个标记带来的边际覆盖不会更高。形式化地，对任意 $A\subseteq B\subseteq\mathcal{M}$ 和 $m\notin B$，都有：

$$f_{T_g}(A\cup{m})-f_{T_g}(A)\ge f_{T_g}(B\cup{m})-f_{T_g}(B).$$

因此，$f_{T_g}(M)$ 是单调子模函数。又因为 $D(M)$ 是对 $g\sim\mathcal{G}$ 和 $T_g$ 的期望，即多个覆盖函数的非负线性组合，而单调子模函数的非负线性组合仍然是单调子模函数，所以 $D(M)$ 也是单调子模函数。

在基数约束 $|M|\le k$ 下，单调子模函数最大化的标准贪心算法具有 $(1-1/e)$ 近似保证，因此：

$$D(M_{\mathrm{greedy}})\ge \left(1-\frac{1}{e}\right)D(M^\star).$$

另一方面，由命题 1 可知，如果每个标记都是 $\delta$-separation，则：

$$I(M)\le |M|\delta.$$

当 $|M|\le k$ 且 $k\le \varepsilon/\delta$ 时：

$$I(M)\le |M|\delta\le k\delta\le \varepsilon.$$

因此，预算内的最优放置 $M^\star$ 也满足 $I(M^\star)\le \varepsilon$。证毕。

---

## 规避成本

我们进一步分析 adaptive attacker 的规避成本。这里采用 Kerckhoffs 式对手模型：对手知道系统会主动注入标记，也知道标记的类型分布、生成策略和放置算法，但不知道本次部署中哪些具体 affordance 是标记。对手的目标是在达成攻击目标 $g$ 的同时，避免触碰任何标记。

在这个对手知识模型下，我们引入 $S(g)$ 来刻画攻击者视角下的不可区分候选集合。对攻击目标 $g$，设 $S(g)\subseteq\mathcal{A}_M$ 为一组对手不可区分的候选 affordance，其中既包含真实 affordance，也可能包含 defender 注入的标记 affordance。直观上，$S(g)$ 表示达成目标 $g$ 所需的一类能力集合。例如，若 $g$ 是读取凭证，则 $S(g)$ 可以是一组 credential-like handles；若 $g$ 是外发敏感信息，则 $S(g)$ 可以是一组 external-output channels。

攻击者要达成 $g$，必须至少触碰 $S(g)$ 中的一个 affordance；但由于真实 affordance 与标记 affordance 在类型、schema 和表层描述上不可区分，攻击者无法在触碰前可靠地区分它们。记 $S(g)$ 中标记的密度为：

$$r(g)=\frac{|M\cap S(g)|}{|S(g)|}.$$

**建模假设 B（能力必需与交换不可区分）。** 对每个攻击目标 $g$，存在一个候选集合 $S(g)$，满足以下两个条件。第一，能力必需性：任何成功达成 $g$ 的执行都必须对 $S(g)$ 中至少一个 affordance 做出提交性触碰。第二，交换不可区分性：在 Kerckhoffs 式对手可见的信息下，$S(g)$ 内真实 affordance 与标记 affordance 没有可利用的可区分特征；因此，对手选择 $S(g)$ 中任意 affordance 时，该 affordance 是标记的概率等于 $r(g)$。

**命题 3（单目标规避下界）。** 在假设 B 下，任何成功达成目标 $g$ 的对手策略被检测的概率至少为 $r(g)$。等价地，单目标规避成功率满足：

$$\Pr[\mathrm{evade}\mid g]\le 1-r(g).$$

**Proof.** 由于 $S(g)$ 对目标 $g$ 是能力必需的，任何成功达成 $g$ 的对手执行都必须对 $S(g)$ 中某个 affordance 做出第一次提交性触碰。由交换不可区分性，该触碰落在标记 affordance 上的概率为 $r(g)$。一旦触碰标记，检测器即被触发。因此，对手被检测的概率至少为 $r(g)$，规避成功率至多为 $1-r(g)$。

若目标 $g$ 需要依次触碰 $\ell$ 类能力集合 $S_1(g),\dots,S_\ell(g)$，并且每一步在条件于此前未触发的情况下仍满足交换不可区分性，记第 $i$ 个集合中的标记密度为 $r_i$，则每一步规避检测的概率至多为 $1-r_i$。因此，完成所有步骤且不触碰任何标记的概率满足：

$$\Pr[\mathrm{evade}\mid g]\le \prod_{i=1}^{\ell}(1-r_i).$$

这说明，攻击目标越依赖多步能力获取或权限扩展，攻击者需要穿过的不可区分能力集合越多，其规避成功率越低。相反，如果标记可被指纹识别，或对手能够将 $S(g)$ 缩小到只包含真实 affordance，则 $r(g)$ 不再有效，上述规避界也不再成立。因此，标记合成质量，即与真实 affordance 的同形性和不可区分性，是该下界成立的关键前提。

**三个命题连起来实际上在证明：主动注入标记是一种合理的防御机制。它可以低误报 P1、可优化 P2，且具有可量化的规避成本 P3。**

---

## 系统框架

该系统不是零散放假工具，而是一个跨载体的注入-标记层，把 honeypot、canary-id 和 watermark 统一成“注入标记物”：

* honey-affordance：假工具、假凭证、假高权动作；碰到即为信号。
* canary / id 标记：给敏感数据、memory 条目、RAG 文档打不可见标记；它出现在下游 action 或 exfil 中即为信号，并支持溯源。

因此，我们需要两个组件：

* placement 合成器：按任务上下文和风险面，导出“最小干扰、最大覆盖”的标记集，对应形式化里的优化。
* 触发-溯源引擎：标记点亮即高置信信号，并顺着标记关系恢复意图链。

---

## 实验设计

### 实验环境

1. Single compromise：IPI 环境，用于正面和 AgentShield 对齐。
2. Composition compromise：SCR-Bench，代表能力流动、信任转移和授权混淆的组合攻击。

### 实验设置

* RQ1：近零误报是否成立？
  对应命题 1。我们测量良性执行触碰任意 marker 的概率 $I(M)$，验证 off-task marker 是否带来近零误报，并观察 $I(M)$ 是否受 $|M|\delta$ 控制。

* RQ2：placement 是否比 random / fixed trap 更好？
  对应命题 2。我们在相同 marker 预算 $k$ 下比较 greedy placement、random placement 和 AgentShield-style fixed traps，验证覆盖优化是否能带来更高的成功攻击检测率。

* RQ3：能否覆盖组合风险？
  对应命题 2 的泛化覆盖。我们在 IPI 之外进一步测试 SCR-CapFlow、SCR-TrustLift 和 SCR-AuthBlur，验证 $D(M)$ 所刻画的 marker 覆盖是否能检测组合路径中出现的受陷执行，而不是只适用于直接 prompt injection。

* RQ4：adaptive attacker 是否更难绕过？
  对应命题 3。我们构造知道防御策略但不知道具体 marker 位置的 adaptive attacker，改变不可区分集合 $S(g)$ 中的 marker 密度 $r(g)$，测量攻击者在达成目标 $g$ 且不触碰 marker 的规避成功率。若 $r(g)$ 或能力链长度增加时规避成功率下降，则说明 marker placement 对 adaptive attacker 施加了可量化的规避成本。

### 指标

* 良性误报率 $I(M)$：

$$I(M)=\frac{#{\text{benign runs that touch any marker}}}{#{\text{total benign runs}}}.$$

* 攻击检测率 TPR：

$$\mathrm{TPR}=\frac{#{\text{attacker runs that touch any marker}}}{#{\text{total attacker runs}}}.$$

* 未检测攻击成功率 ASR：

$$\mathrm{ASR}_{\mathrm{undetected}}=\frac{#{\text{attack runs that reach harmful outcome without marker trigger}}}{#{\text{total attacker runs}}}.$$

* Adaptive attack evasion，即 Evasion Successful Rate ESR：

$$\mathrm{ESR}(g)=\frac{#{\text{adaptive attacks that achieve attack goal }g\text{ without touching markers}}}{#{\text{total adaptive attacks targeting }g}}.$$

### ASR 和 ESR 的区别

* ASR 是所有攻击尝试里，有多少最终造成了 harmful outcome，而且没有触发 marker。
* ESR 是在攻击目标 $g$ 下的规避成功率，检测的是 attacker 想达成某个具体攻击目标 $g$，同时避免碰 marker 的比例。例如，$g=\text{读取 credential}$。
