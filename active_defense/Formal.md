# Formal · 主动防御的形式化

> 形式化 **single source of truth**:对象、定义、命题、证明、指标。`Discussion.md` 讲 idea 与做法,涉及数学引用本文件编号。
> 本版核心 = **一条母原则 + 两条正交完备性轴**:
> **母原则(强不可避免性 §2.1):** 对手为达成 $g$ 所做的任何规避(绕开 / 改写 / 探测区分),**要么使 $g$ 失败,要么跨过一个被观测的边界**。
> **(I) 不可避免性 primitive 全集 {PLANT, WRAP}**(§2:marker 放哪绕不开)——强UA 的两个充分构造。
> **(II) 观测二维全集**(§2.5)= **落点 {STATE, TRANSMISSION} × 时机 {ACCESS, COMMITMENT} = 2×2 四格**(commitment/access 在哪、何时被看到)。
> 覆盖面:**tool / skill / MCP 统一**为"forced-or-observable 的 {STATE,TRANSMISSION} 边界"实例(§5.5),不再区分粒度。
> 删去被证伪的子模优化(旧命题 2,ε-预算 no-op)与几何中点放置。

---

## 1. 对象与记号

设 $\mathcal{U}$ 为一次部署中真实的 affordance 全集(工具、凭证、数据、动作目标、MCP capability、参数等)。
**marker** $m$ 是注入的人工 affordance:(i) 与真实同类**不可区分**;(ii) 无真实副作用;(iii) 被插桩,触发即可观测。
放置 $M\subseteq\mathcal{M}$,agent 看到 $\mathcal{A}_M=\mathcal{U}\cup M$。两种执行分布:良性 $\mathcal{B}$ 与受陷 $\mathcal{C}$。

**commitment-touch。** "触碰"统一指**提交性触碰**:把 marker 绑入一个**会产生效果的动作**(invoke、绑为外发/特权/状态变更动作的目标或参数)。**单纯 read/list/提及不算。** 记 $\mathrm{touch}(\rho)\subseteq\mathcal{A}_M$。

**检测器(policy-free)。** $\rho$ 触发检测 $\iff \mathrm{touch}(\rho)\cap M\neq\varnothing$。运行时**不传标签、不跑违规策略**,只判触碰集交集是否非空。$\mathrm{touch}(\rho)$ **从何观测**由观测全集 {STATE, TRANSMISSION} 给定(§2.5)。

$$I(M)=\Pr_{\rho\sim\mathcal{B}}[\mathrm{touch}(\rho)\cap M\neq\varnothing],\qquad
  D(M)=\Pr_{\rho\sim\mathcal{C}}[\mathrm{touch}(\rho)\cap M\neq\varnothing].$$
目标:$I(M)\approx0,\ D(M)\to1$。

---

## 2. 核心原理:不可避免性(unavoidability)

marker 只有**被触碰**才检测得到。对自适应对手,鲁棒性的**唯一来源**是:marker 落在对手为达成目标 $g$ **绕不开**的元素上。两族是"不可避免性"的两个实例,区别在**什么不可避免**与**检测如何观测**:

* **族 1 · PLANT(对象端)。** 诱饵是**不可区分的 must-take 诱饵**:混入对手必须处理的敏感对象集,对手**无法把它从目标里排除**(因为分不出真假)。检测是 **outcome-based**:诱饵 id 必然出现在对手为达成 $g$ 而产生的**效果状态**里。
* **族 2 · WRAP(边界端)。** 诱饵是**不可避免的 affordance 割集**:每条 in-scope→off-scope 的通路都被插桩(cut-set 完整覆盖),对手**无法绕道**。

> 不是"又一种诱饵",而是**把 marker 放在目标绕不开的元素上**这一条原理的两种落地。下面分别给出各自的鲁棒性命题与**成立前提**——两族的前提**不对称**,这是本版最重要的修正。

### 2.1 母原则:强不可避免性(strong unavoidability)

§2 的"放在绕不开的元素上"对**被动对手**够用,但**自适应对手会主动规避**:它可以尝试(a)**绕开** marker、(b)**改写** marker 值使其不原样出现、(c)**探测区分** marker 真假后剔除。鲁棒性要求这三种规避**本身也绕不开**。

**命题 UA(强不可避免性)。** 放置 $M$ 对达成目标 $g$ 的自适应对手鲁棒,当且仅当:对手的任一规避操作 $\{绕开,改写,探测区分\}$,**或使 $g$ 失败,或跨过一个被观测边界**(§2.5 四格之一)。

**两族是 UA 的两个充分构造:**
* **WRAP** 用"**没有别的路**"实例化 UA:绕开 = 跨割集 = 被观测(§5)。
* **PLANT** 用"**分不出真假**"实例化 UA:改写会破坏 $g$(对 verbatim-critical 诱饵)或落到 ACCESS 面(对 off-path 诱饵),探测区分需跨被观测边界(probe-resistant 诱饵),见 §4。

> 这给"§7 两原语即全集"一个**可证母命题**:全集性不靠枚举,而靠"**规避必可观测或自败**"这一条——{PLANT, WRAP} 是它已知的两个构造(候选第三态"绕开即留痕"实为 ACCESS 面观测,归 §2.5,非新 primitive)。

---

## 2.5 观测全集:落点 × 时机(2×2 四格)

不可避免性({PLANT, WRAP},§2)回答"marker 放哪绕不开";还需**第二条正交公理**回答"commitment 在哪被看到"。它**同样是全集,不是开放枚举**。

**定义(两个观测面)。** commitment-touch 要可观测,marker 必落入两类足迹之一:
* **STATE(状态)**:commitment **持久化为对某存储的改动**(文件 / DB / 配置 / memory)。观测 = 读结果状态(snapshot / diff)。
* **TRANSMISSION(传输)**:commitment **跨过一个边界被发送**(网络外发 / 对下游消费者的输出 / 被中介的工具调用)。观测 = 拦截该边界。

**命题 O(观测完备性 · 落点维)。** 任一**有害**效果必**改变持久状态**或**对外传输**——否则它只停留在 agent 推理内、无任何外部后果(即非 harm;read/mention 亦非 commitment)。故 $\{\text{STATE},\text{TRANSMISSION}\}$ 覆盖一切**可观测的 harm**,无第三类。$\blacksquare$

**映射(既往枚举的通道归位)。** FS / DB / 配置改动 → STATE;网络 egress / agent 输出(被下游读的决策,如 AuthBlur DECISION)/ MCP 工具调用 → TRANSMISSION。"加一个 egress 通道"不增加 primitive,只是 TRANSMISSION 面的一个边界。

**第二维 · 时机 {ACCESS, COMMITMENT}(何时抓)。** 落点回答"harm 在哪面",还需第二正交维回答"在**触碰的哪一步**抓":
* **COMMITMENT**:marker 被**绑进产生效果的动作**(外发 / 调用 / 引用为依据)。看"marker 值是否出现在效果里"。
* **ACCESS**:marker 被**读取/访问**(打开、载入、取值)。看"marker 是否被读",**不看值**。

**命题 O′(时机完备)。** 一次提交性触碰必先 ACCESS(取到 marker)再 COMMITMENT(用出去),二者穷尽"触碰"的可观测时点。故**观测全集 = 落点 × 时机 = {STATE,TRANSMISSION} × {ACCESS,COMMITMENT} = 2×2 四格**。$\blacksquare$

**双模检测器(为什么需要两维)。** 时机维不是冗余,它是**改写式外泄(§7 上限)的正解**:
* **COMMITMENT 模**:对 **verbatim-critical** marker(功能性标识符,起作用必逐字搬运)——改写即破坏 $g$,故对改写**免疫**;
* **ACCESS 模**:对 **off-path** marker(良性读率 $\delta_{\text{read}}\!\approx\!0$)——**读即抓**,与下游如何改写**无关**,亦对改写免疫。
残留界外 = **on-path 自由文本内容**(良性也读、且可被摘要改写):既非 verbatim、又非 off-path → 归 IFC 互补(§7)。

**与 primitive 的统一(两轴正交、组合即全集)。** 在 STATE 或 TRANSMISSION 这**唯二**落点上:
* 放一个 **must-take 不可区分元素** → **PLANT**(观测面 + 诱饵);
* 把该落点做成 **agent 绕不开的强制咽喉** → **WRAP**(观测面 + 强制)。

于是方法空间(primitive × 落点)= **{PLANT, WRAP} × {STATE, TRANSMISSION}** 的 2×2(每格再叠**时机** {ACCESS, COMMITMENT} 由双模检测器选择):

| | **STATE(持久化)** | **TRANSMISSION(对外传输)** |
|---|---|---|
| **PLANT**(诱饵不可区分) | 诱饵进副作用文件(SCR 外传,EXP-005) | 诱饵随外发出去 / 被引用进决策(网络外传;AuthBlur 授权 EXP-006) |
| **WRAP**(强制咽喉) | 强制中介的状态写入边界(sandbox FS 层) | 强制中介的传输边界(MCP server 端调用,MCPTox EXP-015) |

> 时机维在此表之上正交:每格既可在 **COMMITMENT**(值出现在效果里)抓,也可在 **ACCESS**(被读即抓,off-path)抓——后者是改写式外泄的兜底。

**覆盖 = 把两个边界都插桩**(状态存储 + 传输边界)。边界**若强制**(agent 绕不开,如 MCP server / sandbox 的 FS-网络层)→ 它即 WRAP 咽喉;**若仅可观测**(如 CLI 下 snapshot-diff、HTTP_PROXY)→ 它承载 PLANT。**开放 shell 之所以"PLANT 成立、WRAP-in-band 不成立":** STATE/TRANSMISSION 两边界在隔离环境里**可观测**(snapshot-diff 已是 STATE 观测,故 PLANT 抗开放 shell),但**未被强制**(in-band 中介可绕,故 WRAP 失效)——"可观测"与"被强制"是不同性质,见 §5/§7。

---

## 3. 近零误报(命题 1)

**定义($\delta$-separation)。** 放置 $M$ 关于良性是 $\delta$-separation,若 $\forall m\in M:\ \Pr_{\rho\sim\mathcal{B}}[m\in\mathrm{touch}(\rho)]\le\delta$。

**命题 1。** 若 $M$ 是 $\delta$-separation,则 $I(M)\le|M|\delta$;$|M|\delta\ll1$ 时误报近零。
*证明。* $I(M)=\Pr[\bigcup_{m}A_m]\le\sum_m\Pr_{\mathcal{B}}[A_m]\le|M|\delta$。$\blacksquare$

**benign-fit(怎么逼近 $\delta\to0$)。** 从**纯良性数据**按 role-class 学每个 marker 的良性触碰率 $\hat\delta$,**withhold** 掉 $\hat\delta>\tau$ 的 marker。关键不对称:**FP 可由良性数据自校正(benign-fit 兜),漏覆盖不行(良性里没有攻击信号)。** 故放置策略是"保留所有 FP-clean",不是子集预算优化(见 §7 优化器退场)。
*实测:* AuthBlur 完整框架 $I(M)=0.000$(EXP-2026W26-001)。

---

## 4. 族 1:PLANT — 不可区分 + outcome-based 检测

**定义(certify-gate,不可区分性)。** 诱饵 $m$ 经认证当且仅当一个 **Distinguisher** 在 $[m]\cup\text{peers}$(位置轮转)中挑出 $m$ 的命中率 $\le$ chance$+$margin(二项检验 $p\ge\alpha$,trials 足量)。生成→认证→不过则 Camoufleur 重做(拒绝采样);仍不过则丢弃(可区分诱饵是**有害混淆**,宁缺毋滥)。

**认证判别器 = 在环 agent 模型(关键,收 §7-#3)。** Distinguisher 取**部署的同款/更强模型**——因为攻击**经 agent 执行**,agent 自己就是**提交前唯一的判别器**;它分不出 ⇒ 在环对手分不出。**外部更强判别器不破我们**:对手把数据发去外部再筛时,诱饵**已跨传输边界=已被 TRANSMISSION 抓**,外部区分发生在提交之后、太晚。

**定义(probe-resistance,收主动探测)。** $m$ 是 probe-resistant,若**任何能把 $m$ 与真区分开的检验,要么不存在(一切无副作用本地检查——格式/校验位/元数据——皆通过),要么是跨被观测边界的动作**(拿凭证去 auth、调 honey 工具、打 endpoint)。故对手"探测区分"只能:本地探测(筛不掉)或去用它(=触碰=被抓)。**残留界外**:存在纯本地无副作用即可判真、而我们伪造不了对应真实项的对象。

**命题 P(PLANT 规避下界,outcome-based)。** 设目标 $g=$"对敏感对象集施加效果动作",令不可区分候选集 $S(g)$ 含真实敏感对象与诱饵,密度 $r=|M\cap S(g)|/|S(g)|$。**在下列前提下**,任何达成 $g$ 的对手触碰诱饵概率 $\ge r$,故 $\Pr[\mathrm{evade}\mid g]\le 1-r$:
* **(P1) 交换不可区分**:诱饵过 certify-gate 且判别器 $\le$ 在环 agent 模型类(对手排除不掉);
* **(P2) probe-resistant**:主动探测区分只能跨被观测边界或本地失效(对手筛不掉);
* **(P3) 改写不逃**:诱饵 **verbatim-critical**(改写破坏 $g$,COMMITMENT 模抓)**或** off-path(ACCESS 模"读即抓",与改写无关)。

P1–P3 即命题 UA 在 PLANT 上的三个规避出口(区分/探测/改写)全部封死。$\blacksquare$

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

**WRAP 的领地 = 任何被强制的边界(不止 MCP)。** WRAP 成立 ⟺ 效果**必经一个 agent 绕不开的强制边界**(W2∧W3)。强制边界有两类典型:
* **MCP server 端**:tool 在 server 执行,agent 无凭证/网络路径自行复刻(发企业邮件、改生产 IAM、写远端库)。
* **被插桩的 sandbox 边界**:agent 有开放 shell,但 shell 也跑在 sandbox 里——它**砸不掉 sandbox 自己的 FS / 网络层**。把中介挪到该层(FS-写审计 / egress 代理),即得强制 STATE / TRANSMISSION 咽喉。**agent 大多在 sandbox 内运行 → WRAP 的领地其实很广**,不限于 MCP。

关键区分:WRAP 的失效(EXP-004,73% 绕)是因为中介是 **in-band**(焊进 agent 自己运行的脚本)→ 可绕;移到**强制边界**(MCP / sandbox 层)即不可绕。即:**WRAP ⟺ 中介在 agent 触及外、被基座强制**;凡只剩"可观测但未强制"的边界(如 CLI 下 in-band / HTTP_PROXY),退回 PLANT。

**越界粒度 = benign-fit 学出,不靠静态推断能力边界。** WRAP 的 in→off-scope 割不需要预先推断每个单元"该做什么";**off-scope 由良性基线定义**(benign-fit:良性调用/参数集之外即越界)。粒度可到**工具名**(调了良性不调的工具)或**参数/目标**(read_customer 在范围内、但读了良性不读的客户 id → 参数级越界)。这消解了"单个 tool 边界难静态推断"的顾虑:**不推断、只观测 + 学良性**。

---

## 5.5 覆盖面:tool / skill / MCP 是同一套的三个实例

三者不是三种方法,而是"**在哪条 {STATE,TRANSMISSION} 边界、边界被强制还是仅可观测**"的不同基座。同一 {PLANT, WRAP} × 观测二维直接套用:

| 基座 | 边界性质 | WRAP(抓越界) | PLANT(抓洗白/对象) | 实证 |
|---|---|---|---|---|
| **MCP** | server 端**强制** | ✅ off-scope 调用,0 逃逸 | ✅ 蜜罐工具/参数(范围内洗白) | WRAP:MCPTox/MSB;PLANT-in-MCP 待跑 |
| **tool(结构化工具调用)** | 调用接口**强制**(整割) | ✅ 同 MCP | ✅ 蜜罐工具/参数 | 同上 |
| **skill(沙箱内)** | sandbox FS/网络层**可强制** | ✅ 沙箱边界中介(FS-写/egress) | ✅ 沙箱内埋蜜罐资源(读即抓/外传抓) | PLANT-in-sandbox 机制验证(caught=1/FP=0) |
| **开放-shell** | 仅**可观测**(未强制) | ❌ 退化 | ✅ 唯一承重墙 | SCR capflow caught\|acted=100%/FP0 |

**要点:** tool-use / MCP 下 **WRAP(越界)⊕ PLANT(范围内洗白)正交覆盖**;skill 在沙箱内两者皆可(边界可强制则 WRAP,否则 PLANT);开放-shell 仅 PLANT。**"面向 skill/MCP 而非单个 tool"的旧限制解除**——单 tool 亦可(整割 + benign-fit,不需按 tool 静态建模边界)。

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

**母原则 + 两轴即全集,不需要第三个 primitive、也不需要枚举观测。** 全集性由**命题 UA(§2.1)**支撑:鲁棒 ⟺ 规避(绕开/改写/探测区分)必可观测或自败。{PLANT, WRAP} 是 UA 的两个已知充分构造(① 分不出真假 ② 没有别的路);观测 = **落点 {STATE,TRANSMISSION} × 时机 {ACCESS,COMMITMENT}** 二维四格(§2.5)。任何"新机制"要么塌回 {PLANT,WRAP} 之一,要么只是四格上的一个新边界(如 egress = TRANSMISSION×COMMITMENT 的一个边界,"绕开即留痕"= ACCESS 面,**皆非新 primitive**),要么靠基座强制(环境假设,不是新机制)。**授权/权限属 PLANT × TRANSMISSION**(假授权被引用进决策,EXP-006)。**PLANT 是开放基座的通用承重墙**;**WRAP 仅在边界被强制(MCP server / sandbox FS-网络层)时成立**;**tool-use 下二者正交(WRAP 越界 ⊕ PLANT 洗白,§5.5)**。AuthBlur(speech-act)、CapFlow-over-CLI(开放 shell 且未强制)是 WRAP-in-band 的界外/弱例。

**优化器退场。** ε-子模/子集预算优化(旧命题 2)被实验证为 **no-op**:良性 FP **不随** $|M|$ 增长 → 预算永不 binding;且丢覆盖的子集选择对自适应对手**有害**。"优化"退化为 benign-fit 的"保留所有 FP-clean"。**论文贡献不是优化算法**,而是:① affordance 边界的**自动感知**;② **不可区分**的伪装(certify-gate);③ **commitment-touch** policy-free 检测;④ **基座级能力中介**。几何中点放置 / lure_radius / MCTS 一并退出主叙事。

**与 IFC 的分界。** manufacture-then-observe:埋假物、看假物是否被提交触碰;运行时**不跟踪真实数据、不跑 source→sink 策略**。**改写式外泄**大部分已由双模检测收口(verbatim-critical 走 COMMITMENT 对改写免疫;off-path 走 ACCESS "读即抓"不看值,§2.5);**残留界外 = on-path 自由文本内容**(良性也读、可摘要改写)——这一小块归 IFC(Fides/AgentArmor)内容流溯源,只作**被动 baseline** 对照/互补,不塞进主动框架。

**已吸收的载体约束。** 不可见 Unicode / 哨兵串因 LLM 转发不保真而失效(canary TPR=0);可行 PLANT 载体是**结构化假标识符**(假 IBAN/email/ID),逐字搬运。诱饵命名**不得自描述**(honey/decoy/trap/sentinel),自描述既吓退 agent 又是混淆(TrustLift ASR 0.74→0.14)。

**开放问题 / 界外。**
* (O-fingerprint) certify-gate 统计功效:加 trials + 二项检验,判别器取**在环 agent 模型**(§4)——已给方向,待实测。
* (O-probe) probe-resistant 诱饵生成(本地校验位/格式/元数据全通过)待实现与验证;纯本地可判真、我们伪造不了对应真实项的对象 = **界外**。
* (O-rewrite) **on-path 自由文本内容**的改写式外泄 = **界外**(归 IFC 互补,§7)。
* (O-granularity) WRAP 参数级越界 + benign-fit 到参数(§5.5)待形式化与实测(抓"范围内单一具名"洗白)。
* (O-substrate) W2/W3 在真 MCP/AgentDojo 端到端复现(MCPTox EXP-015 已初证);(O-sandbox) sandbox 边界强制中介(FS-写/egress)把 skill/开放-shell 纳入 WRAP;(O-egress) CLI 下 egress 抓包代理解锁网络外传 PLANT。
* (O-prevent) **检测 ≠ 阻止**:PLANT 是事后绊线(诱饵无害,但同一动作命中真目标时真危害已成);WRAP 可 block,PLANT 需接 response 层——**主动防御 ⊋ 检测**,prevention/response 另述。
* (O-persist) **跨会话/记忆投毒**(session-1 埋、session-N 发作)的因果链,单-episode 观测未覆盖 → 界外/待扩。
* (O-singleaction) 开放 shell 上无 must-take、边界未强制、且良性也碰的单一具名动作 = deception 逻辑界外(归 prevention)。
