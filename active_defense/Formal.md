# Formal · 主动防御的形式化背景

> 本文件是 **形式化 single source of truth**:记录主动防御方案的对象、定义、命题、
> 证明与评测指标。`Discussion.md` 负责 idea 与方案设计,涉及数学时引用本文件的编号。

---

## 1. 对象与记号

**Affordance 空间。** Affordance 指环境提供给一个主体的"可做的动作可能性"(如门把手 afford "拉/推")。

设 $\mathcal{U}$ 为一次部署中真实的 affordance 全集,包括工具、凭证句柄、memory 条目、
RAG 文档、MCP capability、文件路径、动作目标、参数等。一个标记物 marker $m$ 是注入的
人工 affordance,满足:

* 形式上与真实 affordance 不可区分(同类型、同 schema、同表层描述);
* 无真实副作用;
* 被插桩,即触发标记物会被观测。

设 $\mathcal{M}$ 为候选标记全集。放置动作是 defender 注入的有限子集 $M\subseteq\mathcal{M}$。
agent 看到的 affordance 空间为:

$$\mathcal{A}_M=\mathcal{U}\cup M.$$

一次执行 $\rho$ 诱导一个触碰集 $\mathrm{touch}(\rho)\subseteq\mathcal{A}_M$。触碰动作包括
invoke、read、write 或绑定为动作目标。执行分为两种分布:

* 良性分布 $\mathcal{B}$:正常使用、守 scope 的执行;按任务记为 $\mathcal{B}_t$。
* 受陷分布 $\mathcal{C}$:被劫持、被组合带偏或发生 spec-violation 的执行。

**检测器。** 执行 $\rho$ 触发检测当且仅当:

$$\mathrm{touch}(\rho)\cap M\neq\varnothing.$$

> **触发语义说明(讨论修订,见 §6 开放问题 O4):** 命题 3 实际依赖的是"第一次
> *提交性*触碰(committing touch)",即把 marker 绑入外发动作目标/参数,而非单纯 read/list。
> 命题 1 的 $I(M)$ 与运行时 trigger 应统一到 commitment-touch 语义,以避免 read 触发误报。

---

## 2. 干扰与覆盖

**定义 1（干扰与覆盖）。**

良性干扰(误报率 FPR):

$$I(M)=\Pr_{\rho\sim\mathcal{B}}\left[\mathrm{touch}(\rho)\cap M\neq\varnothing\right].$$

检测覆盖(检测率 TPR):

$$D(M)=\Pr_{\rho\sim\mathcal{C}}\left[\mathrm{touch}(\rho)\cap M\neq\varnothing\right].$$

防御目标:$I(M)\approx 0,\ D(M)\to 1$。

**定义 2（$\delta$-separation）。** 守规矩的 agent 正常做任务 $t$（$\rho\sim\mathcal{B}_t$）时,
触碰到标记 $m$ 的概率不超过 $\delta$:

$$\Pr_{\rho\sim\mathcal{B}_t}\left[m\in\mathrm{touch}(\rho)\right]\le \delta.$$

**命题 1（近零误报）。** 设放置 $M$ 关于良性分布 $\mathcal{B}$ 是 $\delta$-separation,即对任意
$m\in M$:

$$\Pr_{\rho\sim\mathcal{B}}\left[m\in\mathrm{touch}(\rho)\right]\le \delta.$$

则误报率满足 $I(M)\le |M|\delta$。当 $|M|\delta\ll 1$ 时误报近零。

**证明。** 对每个 $m\in M$ 令 $A_m=\{\rho:\ m\in\mathrm{touch}(\rho)\}$。良性执行触发误报当且仅当
触碰至少一个标记,故

$$\{\rho:\ \mathrm{touch}(\rho)\cap M\neq\varnothing\}=\bigcup_{m\in M}A_m.$$

由 $I(M)$ 定义与并集界(union bound):

$$I(M)=\Pr_{\rho\sim\mathcal{B}}\left[\bigcup_{m\in M}A_m\right]\le \sum_{m\in M}\Pr_{\rho\sim\mathcal{B}}[A_m].$$

由 $\delta$-separation,$\Pr_{\rho\sim\mathcal{B}}[A_m]\le\delta$,故 $I(M)\le|M|\delta$。$\blacksquare$

**说明。** 该命题成立的前提是放置 $M$ 是 off-benign-path 的(理论上 agent 触碰任务无关
标记的概率很小)。误报由两因素控制:marker 越多、误碰任意一个的机会越大;$\delta$ 越小、
越不可能碰它。$\delta$ 的大小取决于 Selector 能否准确把 marker 放到良性授权路径之外
(见 §6 开放问题 O2)。

---

## 3. 放置问题

为把 $D(M)$ 写成可优化结构,引入"位置-吸引力"假设。对攻击目标 $g$,受陷执行会被 $g$ 所需的
某些位置/类型/能力吸引(凭证句柄、敏感 memory、私有文档、高权限动作、外发通道)。记这些
候选位置集合为随机变量 $T_g$,由 $g$ 与执行上下文决定;defender 的放置 $M$ 决定哪些候选位置被
注入为可观测标记。当且仅当 $M\cap T_g\neq\varnothing$ 时该执行被检测。于是:

$$D(M)=\mathbb{E}_{g\sim\mathcal{G}}\,\mathbb{E}_{T_g}\left[\mathbb{1}\{M\cap T_g\neq\varnothing\}\right],$$

其中 $\mathcal{G}$ 是攻击目标分布。这把 marker placement 看成覆盖问题。

**命题 2（子模性与贪心保证）。** 在位置-吸引力假设下,$D(M)$ 是关于 $M$ 的单调子模函数。
若每个标记关于良性分布是 $\delta$-separation,且预算 $k\le \varepsilon/\delta$,则任意 $|M|\le k$ 的放置满足
$I(M)\le\varepsilon$;且预算约束下的最优放置 $M^\star=\arg\max_{|M|\le k}D(M)$ 满足 $I(M^\star)\le\varepsilon$。
同时标准贪心算法达到 $(1-1/e)$ 近似:

$$D(M_{\mathrm{greedy}})\ge \left(1-\tfrac{1}{e}\right)D(M^\star).$$

**证明。** 对固定的 $g,T_g$ 定义覆盖函数 $f_{T_g}(M)=\mathbb{1}\{M\cap T_g\neq\varnothing\}$。

*单调性*:$A\subseteq B\Rightarrow f_{T_g}(A)\le f_{T_g}(B)$。

*子模性*:对 $A\subseteq B\subseteq\mathcal{M}$ 与 $m\notin B$,

$$f_{T_g}(A\cup\{m\})-f_{T_g}(A)\ge f_{T_g}(B\cup\{m\})-f_{T_g}(B).$$

故 $f_{T_g}$ 单调子模。$D(M)$ 是 $f_{T_g}$ 对 $g\sim\mathcal{G}$ 和 $T_g$ 的期望(非负线性组合),
单调子模函数的非负线性组合仍单调子模,故 $D(M)$ 单调子模。基数约束下标准贪心有 $(1-1/e)$
保证。又由命题 1,$|M|\le k\le\varepsilon/\delta$ 时 $I(M)\le k\delta\le\varepsilon$。$\blacksquare$

> **覆盖盲区(讨论修订,见 §6 开放问题 O5):** 组合攻击(capability flow / trust lift /
> authority blur)的有害路径是良性步骤的链式涌现,$T_g$ 定义在**轨迹的信任/授权转移边**上,
> 而非单个 affordance。组合场景下 marker 与 $D(M)$ 应在边集上重定义。

---

## 4. 规避成本

采用 Kerckhoffs 式对手模型:对手知道系统会注入标记,也知道标记的类型分布、生成策略和放置
算法,但不知道本次部署中哪些具体 affordance 是标记。对手目标是在达成 $g$ 的同时不触碰任何标记。

引入 $S(g)\subseteq\mathcal{A}_M$ 为一组对手不可区分的候选 affordance(既含真实也含标记),
表示达成 $g$ 所需的一类能力集合。记 $S(g)$ 中标记密度:

$$r(g)=\frac{|M\cap S(g)|}{|S(g)|}.$$

**假设 B（能力必需与交换不可区分）。** 对每个 $g$ 存在 $S(g)$ 满足:(i) *能力必需性*:任何成功
达成 $g$ 的执行都必须对 $S(g)$ 中至少一个 affordance 做出提交性触碰;(ii) *交换不可区分性*:在
Kerckhoffs 对手可见信息下,$S(g)$ 内真实与标记 affordance 无可利用区分特征,故对手任选其一时
该 affordance 是标记的概率等于 $r(g)$。

**命题 3（单目标规避下界）。** 在假设 B 下,任何成功达成 $g$ 的对手被检测的概率至少为 $r(g)$,
即单目标规避成功率 $\Pr[\mathrm{evade}\mid g]\le 1-r(g)$。

**证明。** 由能力必需性,任何成功执行都必须对 $S(g)$ 中某 affordance 做出第一次提交性触碰。
由交换不可区分性,该触碰落在标记上的概率为 $r(g)$;一旦触碰标记即触发检测。故被检测概率
$\ge r(g)$,规避成功率 $\le 1-r(g)$。

若 $g$ 需依次触碰 $\ell$ 类能力集合 $S_1(g),\dots,S_\ell(g)$,每步条件于此前未触发仍满足交换不可
区分性,记第 $i$ 步标记密度 $r_i$,则

$$\Pr[\mathrm{evade}\mid g]\le \prod_{i=1}^{\ell}(1-r_i).$$

攻击越依赖多步能力获取/权限扩展,需穿过的不可区分集合越多,规避成功率越低。$\blacksquare$

**前提与失效条件。** 若标记可被指纹识别,或对手能把 $S(g)$ 缩小到只含真实 affordance,
则 $r(g)$ 失效、下界不成立。因此**标记合成质量(与真实 affordance 的同形性、行为级不可区分性)
是该下界成立的关键前提**(见 §6 开放问题 O3)。

**三命题的整体含义:主动注入标记是一种合理防御机制——低误报(P1)、可优化(P2)、
具可量化规避成本(P3)。**

---

## 5. 评测指标

* 良性误报率:
$$I(M)=\frac{N(\text{benign runs that touch any marker})}{N(\text{total benign runs})}.$$

* 攻击检测率 TPR:
$$\mathrm{TPR}=\frac{N(\text{attacker runs that touch any marker})}{N(\text{total attacker runs})}.$$

* 未检测攻击成功率 ASR:
$$\mathrm{ASR}_{\mathrm{undetected}}=\frac{N(\text{attack runs reaching harmful outcome without marker trigger})}{N(\text{total attacker runs})}.$$

* Adaptive 规避成功率 ESR:
$$\mathrm{ESR}(g)=\frac{N(\text{adaptive attacks achieving } g \text{ without touching markers})}{N(\text{total adaptive attacks targeting } g)}.$$

**ASR 与 ESR 的区别。** ASR 是所有攻击尝试里"造成 harmful outcome 且未触发 marker"的比例;
ESR 是在某具体目标 $g$ 下"达成 $g$ 且规避 marker"的比例(如 $g=$ 读取 credential)。

---

## 6. 开放问题与待修订（讨论共识）

记录与 idea 评审中达成的、需要在后续修订命题/系统时处理的点:

* **O1（覆盖与误报对 adaptive 的张力，最高优先级）。** 纯 off-benign-path 的
  *affordance-marker* 对"贴着良性路径作恶"(用合法工具把敏感数据编码进 subject/body 外发)的
  最强攻击 $D(M)\to 0$。需引入第二类 *provenance/canary-marker*(给真实敏感数据打不可见标记),
  使"标记数据出现在任意外发通道即报警",从而对 on-path 攻击仍有覆盖。$D(M)$ 应按两类
  marker 分开刻画。该方案见 `Discussion.md` Thread #1 §3。
* **O2（Selector 的循环论证）。** $\delta$ 小依赖准确识别良性授权路径,需论证 marker 相对
  allowlist 策略的增量价值(只需粗粒度风险边界、提供主动信号与溯源、把"是否越权"转成"是否触碰")。
* **O3（指纹抗性）。** marker 无真实副作用 → 行为级可被探测。需把 $\delta$、$r(g)$ 显式写成
  合成质量/探测抗性的函数,并实测攻击者无害探测后 $r(g)$ 的衰减。
* **O4（触发语义统一）。** 将命题 1 的 $I(M)$ 与运行时 trigger 从纯 touch 改为 commitment-touch,
  与命题 3 一致,避免 read/list 触发误报。
* **O5（组合路径覆盖）。** 组合攻击的 $T_g$ 在信任/授权转移边上,marker 与 $D(M)$ 需在边集重定义。
