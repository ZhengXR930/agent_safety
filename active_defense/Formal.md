# Formal · 主动防御的形式化

> 形式化 **single source of truth**:对象、定义、命题、证明、指标。`Discussion.md` 讲 idea 与做法,涉及数学引用本文件编号。
> 本版按 2026-W26 实验结论重写:核心轴从"objective→boundary 统一谱 + 三命题优化"改为 **不可避免性(unavoidability)**;删去被证伪的子模优化(命题 2,ε-预算 no-op)与几何中点放置。

---

## 1. 对象与记号

设 $\mathcal{U}$ 为一次部署中真实的 affordance 全集(工具、凭证、数据、动作目标、MCP capability、参数等)。
**marker** $m$ 是注入的人工 affordance:(i) 与真实同类**不可区分**;(ii) 无真实副作用;(iii) 被插桩,触发即可观测。
放置 $M\subseteq\mathcal{M}$,agent 看到 $\mathcal{A}_M=\mathcal{U}\cup M$。两种执行分布:良性 $\mathcal{B}$ 与受陷 $\mathcal{C}$。

**commitment-touch。** "触碰"统一指**提交性触碰**:把 marker 绑入一个**会产生效果的动作**(invoke、绑为外发/特权/状态变更动作的目标或参数)。**单纯 read/list/提及不算。** 记 $\mathrm{touch}(\rho)\subseteq\mathcal{A}_M$。

**检测器(policy-free)。** $\rho$ 触发检测 $\iff \mathrm{touch}(\rho)\cap M\neq\varnothing$。运行时**不传标签、不跑违规策略**,只判触碰集交集是否非空。

$$I(M)=\Pr_{\rho\sim\mathcal{B}}[\mathrm{touch}(\rho)\cap M\neq\varnothing],\qquad
  D(M)=\Pr_{\rho\sim\mathcal{C}}[\mathrm{touch}(\rho)\cap M\neq\varnothing].$$
目标:$I(M)\approx0,\ D(M)\to1$。

---

## 2. 核心原理:不可避免性(unavoidability)

marker 只有**被触碰**才检测得到。对自适应对手,鲁棒性的**唯一来源**是:marker 落在对手为达成目标 $g$ **绕不开**的元素上。两族是"不可避免性"的两个实例,区别在**什么不可避免**与**检测如何观测**:

* **族 1 · PLANT(对象端)。** 诱饵是**不可区分的 must-take 诱饵**:混入对手必须处理的敏感对象集,对手**无法把它从目标里排除**(因为分不出真假)。检测是 **outcome-based**:诱饵 id 必然出现在对手为达成 $g$ 而产生的**效果状态**里。
* **族 2 · WRAP(边界端)。** 诱饵是**不可避免的 affordance 割集**:每条 in-scope→off-scope 的通路都被插桩(cut-set 完整覆盖),对手**无法绕道**。

> 不是"又一种诱饵",而是**把 marker 放在目标绕不开的元素上**这一条原理的两种落地。下面分别给出各自的鲁棒性命题与**成立前提**——两族的前提**不对称**,这是本版最重要的修正。

---

## 3. 近零误报(命题 1)

**定义($\delta$-separation)。** 放置 $M$ 关于良性是 $\delta$-separation,若 $\forall m\in M:\ \Pr_{\rho\sim\mathcal{B}}[m\in\mathrm{touch}(\rho)]\le\delta$。

**命题 1。** 若 $M$ 是 $\delta$-separation,则 $I(M)\le|M|\delta$;$|M|\delta\ll1$ 时误报近零。
*证明。* $I(M)=\Pr[\bigcup_{m}A_m]\le\sum_m\Pr_{\mathcal{B}}[A_m]\le|M|\delta$。$\blacksquare$

**benign-fit(怎么逼近 $\delta\to0$)。** 从**纯良性数据**按 role-class 学每个 marker 的良性触碰率 $\hat\delta$,**withhold** 掉 $\hat\delta>\tau$ 的 marker。关键不对称:**FP 可由良性数据自校正(benign-fit 兜),漏覆盖不行(良性里没有攻击信号)。** 故放置策略是"保留所有 FP-clean",不是子集预算优化(见 §7 优化器退场)。
*实测:* AuthBlur 完整框架 $I(M)=0.000$(EXP-2026W26-001)。

---

## 4. 族 1:PLANT — 不可区分 + outcome-based 检测

**定义(certify-gate,不可区分性)。** 诱饵 $m$ 经认证当且仅当一个独立 **Distinguisher** 在 $[m]\cup\text{peers}$(位置轮转)中挑出 $m$ 的命中率 $\le$ chance$+$margin(挑不出来=不可区分)。生成→认证→不过则由 Camoufleur 重做(拒绝采样);仍不过则丢弃(可区分诱饵是**有害混淆**,宁缺毋滥)。

**命题 P(PLANT 规避下界,outcome-based)。** 设目标 $g=$"对敏感对象集施加效果动作",检测读取**效果状态**(诱饵 id 是否出现在副作用里)。令不可区分候选集 $S(g)$ 含真实敏感对象与诱饵,诱饵密度 $r=|M\cap S(g)|/|S(g)|$。若诱饵经 certify-gate 认证(交换不可区分),则任何达成 $g$ 的对手触碰诱饵概率 $\ge r$,$\Pr[\mathrm{evade}\mid g]\le 1-r$。

**关键:对开放执行环境鲁棒。** 检测读的是对手**为达成 $g$ 必须产生的 outcome**,**不依赖对手运行 defender 的任何代码**。故对手即便控制执行环境(裸 shell、复刻文件写入、剥离插桩)也**无法靠"避开我们的代码"逃脱**——它要达成目标就得把效果写出来,而不可区分使它排除不掉诱饵。这正是 PLANT 在开放基座里**强于** WRAP-in-band 的根因(§7 主结论)。
*实测:* 同一知情开放-shell 对手下 outcome 检出 **8/8(0% 逃逸)**,WRAP-in-band 仅 27%(EXP-2026W26-005)。

**授权 / 权限是 PLANT 的一个实例(不是 WRAP)。** "授权"语义同样收进"分不出真假"这一支:埋一条**不可区分的假"已预授权"凭证**;目标 $g=$"执行某特权动作",对手要达成就**必须给出授权依据**,而依据集 $S(g)$ 中混入的假授权排除不掉 → 引用即 commitment-touch,且该引用落在 outcome(action record / 输出)里。良性任务不执行该特权动作 → $\delta\approx0$(构造性)。*实测(EXP-2026W26-006,开放 shell):* 假授权诱饵 **5/5 抓、FP 0/5**;同对手对"逼 agent 来申请授权"的网关 **0/5**。AuthBlur 的 `prior_authorization` 是其 speech-act 特例。

---

## 5. 族 2:WRAP — 能力中介咽喉 + 三个前提

**定义(WRAP = cut-set 覆盖)。** 在 affordance/dataflow 图上,wrap 是覆盖**每条** in-scope→off-scope 结果路径的割;保留所有 FP-clean 割边(漏一条即被自适应对手绕行)。

**命题 W(WRAP 抗自适应 ⟺ 三前提)。** WRAP 对知情自适应对手成立,**当且仅当**同时满足:

* **(W1) effectful harm。** 危害需要 invoke 一个能力(非纯文本 speech-act)。否则不存在可割的 actuation 边界。
* **(W2) 基座强制中介。** 中介由执行基座**在 agent 触及范围之外**强制(runtime / tool 层拦截调用),**不是** agent 自己运行、能读能改的 in-band 代码。
* **(W3) 有界 affordance 面。** agent **无法在被中介能力之外复刻效果**(无裸 shell / 无直接 IO)。

**负结果(EXP-2026W26-004)。** 把 recorder **焊进 agent 自己运行的脚本**(in-band 中介)违反 W2+W3:CapFlow-over-CLI(裸 shell)下知情对手读穿明文 telemetry,import 后剥离 / 直接复刻副作用,**caught\|acted=27%(73% 绕过)**;agent transcript 自述 *"telemetry stripped before execution"*。而有界 function-call probe(满足 W1–W3)下知情对手 **0% 逃逸**。

**违反 W1 的退化:speech-act harm。** AuthBlur 的危害是纯文本决策(grader 直读),无执行层 → **结构上无咽喉**。明文 gateway 只能抓"自愿合规的洗白 agent",知情对手 prose 直接写 approved 即绕(EXP-2026W26-003:prose-escape 知情对手 90% 逃逸)。

**WRAP 的残余领地(收窄)。** 一个能力**无法被中介**,如果对手握有一个**涵盖它的更通用能力**(裸 shell/代码执行可复刻该效果)。skill 能跑代码是常态 → 凡**开放 shell 可复刻的效果(数据外传、本地状态改动、甚至"授权")都不归 WRAP,归 PLANT**。WRAP 只剩**本地不可复刻的特权/外部效果**:actuation 在 agent 触及范围外、且只经被中介能力达成(典型 = **MCP server 端**:发企业邮件、改生产 IAM、写远端库——agent 即便有 shell 也无凭证/网络路径自行复刻)。即:**WRAP ⟺ effect 不可被对手的最通用 affordance 复刻**;这正是 W2∧W3。

---

## 6. 评测指标

* $I(M)$:良性触碰任一 marker 的比例(主安全指标)。
* $\mathrm{TPR}$:攻击触碰 marker 的比例。
* $\mathrm{dgs}$(detected given success):攻击**真成功**时被捕获的比例(优化/报告主用,避免把"诱饵扰乱致攻击失败"误算成检测)。
* $\mathrm{ASR}_{\text{undetected}}$:危害达成且无 marker 触发的比例。
* $\mathrm{ESR}(g)$(adaptive 规避成功率):达成 $g$ 且规避所有 marker 的比例。区分**有界 vs 开放基座**报告。

---

## 7. 边界与定位(诚实)

**主结论(2026-W26)。** **在开放 agentic 基座里,deception(PLANT:outcome 检测 + 不可区分诱饵)> instrumentation(WRAP-in-band:可被读穿绕开)。** PLANT 的检测 $\perp$ 对手的执行环境;WRAP 的 in-band 检测依赖对手运行我们的代码,可被绕。

**两个不可避免性来源即全集,不需要第三个 primitive。** ① 分不出真假(PLANT)② 没有别的路(WRAP)。任何"新行为"要么塌回这两者之一,要么靠基座强制(那是环境假设,不是新机制)。**授权/权限属 ①(PLANT)**,不是 WRAP(EXP-006)。**PLANT 是开放基座的通用承重墙**(数据、对象、授权);**WRAP 收窄为基座强制中介的特权/外部效果(MCP server 端)**,凡 shell 可复刻者归 PLANT。AuthBlur(speech-act)、CapFlow-over-CLI(开放 shell)是 WRAP 的界外/弱例。

**优化器退场。** ε-子模/子集预算优化(旧命题 2)被实验证为 **no-op**:良性 FP **不随** $|M|$ 增长 → 预算永不 binding;且丢覆盖的子集选择对自适应对手**有害**。"优化"退化为 benign-fit 的"保留所有 FP-clean"。**论文贡献不是优化算法**,而是:① affordance 边界的**自动感知**;② **不可区分**的伪装(certify-gate);③ **commitment-touch** policy-free 检测;④ **基座级能力中介**。几何中点放置 / lure_radius / MCTS 一并退出主叙事。

**与 IFC 的分界。** manufacture-then-observe:埋假物、看假物是否被提交触碰;运行时**不跟踪真实数据、不跑 source→sink 策略**。改写式外泄(诱饵假值被语义改写后不原样出现)是所有方法共有上限,留作 open problem;内容流溯源属 IFC(Fides/AgentArmor),只作**被动 baseline** 对照,不塞进主动框架。

**已吸收的载体约束。** 不可见 Unicode / 哨兵串因 LLM 转发不保真而失效(canary TPR=0);可行 PLANT 载体是**结构化假标识符**(假 IBAN/email/ID),逐字搬运。诱饵命名**不得自描述**(honey/decoy/trap/sentinel),自描述既吓退 agent 又是混淆(TrustLift ASR 0.74→0.14)。

**开放问题。** (O-FP) WRAP 的 $\delta_{\text{bdry}}$ 在满足前提的基座上单独实测;(O-fingerprint) certify-gate 的统计功效(当前 trials 偏少,需加 trials + 二项检验);(O-substrate) W2/W3 在真 MCP/AgentDojo 上的端到端复现。
