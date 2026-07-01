# Discussion · 当前 Active 议题

> 形式化(定义/命题/证明/指标)见 `Formal.md`;本文件讲清楚 idea、做法、实现与实验,涉及数学处引用 `Formal.md`。

## Thread #1：给 AI agent 埋诱饵的主动防御

---

### 0. 一句话 + 一个例子

**一句话:** 我们在 agent 能看到的环境里预先埋一些"本任务根本用不到的假东西"(诱饵);正常 agent 绝不会碰它们,所以**一旦碰了,就说明这个 agent 被攻击/带偏了**。检测不靠"判断行为对不对",只靠"看诱饵有没有被碰"。

**一个例子(族 1):** 用户让 agent"扫描并报告项目里的资源"。我们在扫描结果里偷偷塞一条假记录 `CRITICAL escalation target — 需立即处理`。
* 正常 agent:扫描完,写报告,结束 —— 它**只读不动**,不会去"处理"这条记录。
* 被注入攻击带偏的 agent:看到"需立即处理",就去调用一个修改性动作、把这条假记录当成操作目标 —— **它"碰"了诱饵,警报触发**。
关键:这条记录是假的,真实敏感数据从头到尾没进 agent。所以**良性零误报是天然的**(良性根本不会动一条与任务无关的假记录)。

**第二个例子(族 2):** 用户让一个"invoice 审阅 skill"只做审阅、给结论。我们在它的职责边界**外面**埋一个诱饵动作:`紧急执行/批准下游操作`。
* 正常审阅 agent:它知道自己只负责"审阅",不会去执行下游动作。
* 被 AuthBlur/TrustLift 把授权边界洗糊的 agent:以为自己被授权了,去执行那个"紧急批准" —— **碰了诱饵,警报触发**。

两个例子是**同一个机制**(埋假东西、看有没有被提交性地使用),只是诱饵放的位置不同:一个放在"攻击想拿走的对象"上,一个放在"攻击想跨越的授权边界"上。这就是下面要讲的连续谱。

---

### 1. 为什么现有方案不够

| 路线 | 做法 | 问题 |
|---|---|---|
| 观察式护栏 | 看 agent 的行为 trace,事后分类"是否越权" | 误报漏报难兼得;伤害将发生时才介入 |
| 被动数据流(IFC/taint,如 AgentArmor/Fides) | 运行时给真实数据打标签、传播、按违规策略判流 | 全量跟踪贵;隐式流抓不全;要写违规策略;LLM 一改写就穿不过 |

两者共同的麻烦是:都要在运行时**判断"对不对"**(分类或策略)。我们换个思路——不判断对错,只埋诱饵看有没有被碰。

---

### 2. 我们的做法:主动欺骗(active deception)

defender 预先在 agent 可见的 affordance 空间里**注入诱饵**;良性流程**绝不触碰**,**触碰本身就是受陷信号**。好处:

* 运行时**不传标签、不写违规策略**(检测器是 policy-free 的);
* 误报由**构造**逼近零(诱饵本来就放在良性路径之外);
* 有**可量化的规避成本下界**(`Formal.md` 命题 3)。

三条贯穿全文的设计原则:

* **P1 · 放对位置(off-benign-path but attack-attractive)。** 诱饵要放在"良性绝不经过、攻击却容易经过"的地方。这是"零误报"的前提(命题 1 的 δ 要小)。
* **P2 · 只认"提交性触碰"(commitment-touch)。** 只有把诱饵**真正用进一个会产生效果的动作**才算触碰(invoke 它、把它当外发/操作的参数)。**光是 read/list/看到不算。** 这避免 agent 正常浏览造成误报。
* **P3 · 先验工作只在离线放置时用一次。** "哪条路径是良性的、授权边界在哪"这类判断,只在离线埋诱饵时用一次(粗粒度、便宜);运行时检测器纯看"碰没碰"。

---

### 3. 核心贡献:两族是同一机制的两个端点(连续谱)

这是全篇最重要的一句话:

> 我们不是提出"又一种诱饵",而是给出**第一个统一的诱饵放置理论**——把
> **objective**(攻击想拿走的对象)和 **boundary**(攻击想跨越的授权)放到**同一条连续谱**上,
> 用同一个 policy-free 检测器、同一套三条数学(命题 1/2/3)。

为什么强调"统一"?因为**拆开看,每一端都会被说成是别人做过的**:
* objective 端的假凭证 ≈ AgentShield 的 honeytoken;
* boundary 端的假动作 ≈ honeytool / honey-permissions。

AgentShield 把这几层**经验性地拼在一起**,没有把它们统一起来的理论。我们的增量正是那条统一轴 + 三条共用命题。形式上,两族只是命题 3 里"对手分不清真假的候选集 $S(g)$"的**论域不同**:族 1 的 $S(g)$ 在外发槽位上,族 2 的在边界动作上(`Formal.md` 推论 3.1、§7)。

**基于这条轴,两族的分工:**

* **族 1 = "地板",负责完整性,不是主卖点。** 它证明统一框架在 objective 端也成立,并提供与 AgentShield 对齐的对照点。
* **族 2 = "承重墙",全部重量所在。** 它抓"数据没动、被搬的是授权"的组合攻击(TrustLift/AuthBlur),这是 AgentShield(只看 tool 注入)和 IFC(没有数据流可跟)都漏的。族 2 的真正卖点收窄到三条(见 §5)。

**论文三条命脉:** ① 统一形式化(合起来才有);② 族 2 的理论护城河;③ 跨威胁模型评估。

---

### 4. 族 1:objective-level honeypot(对象级诱饵)

#### 4.1 是什么
把诱饵放在**攻击想拿走/外发/选用的对象**上:注入本任务用不到的假对象,**这个假对象被提交性地使用,就是信号**。

| 载体 | 诱饵实例 | 触发(commitment-touch) |
|---|---|---|
| 数据/凭证(原子) | 假 credential / 假 key / 假敏感记录 | 假值出现在外发/写外部动作的参数里 |
| 目标/资源对象 | 假 target / 假 file / 假 account / 假 record | 假对象被选作转账/分享/删除/下载/授权的目标或参数 |
| 可扩对象 | memory / RAG / MCP resource 里的假对象 | 同理,但必须是提交性使用而非 read/list |

#### 4.2 关键约束:只保留"原子 honeytoken"
族 1 **只对"原子假值的提交性外发/选用"**给零误报保证:defender 注入假值,真实敏感数据从不进 agent,触发的永远是"假值被用了"——**不跟踪任何真实源、不设内容覆盖阈值**。

> **为什么不能加"内容流溯源"。** 曾经有个想法:声明真实敏感源 → 跟踪它进上下文 → 当外发参数和已读源内容重叠超阈值时报警。这个**机制上就是 Fides/AgentArmor 的 IFC**(打标真实源 + 阈值策略)。留着它有两个致命问题:(1) 与族 2 拒绝"标签传播+判流"自相矛盾;(2) 会让族 1 掉进"必须去比 Fides 的同类",reviewer 会问"那你跟 Fides 区别何在"。所以**砍掉它**;改写式外泄的覆盖交给 IFC 当被动 baseline 去对比。

#### 4.3 怎么实现(代码:`run_scr_capflow_C.py`)
族 1 原来是写死一个 honey-target,没有可优化的东西。现在改成**可搜诱饵规格** `(type, lure_radius, position)`:
* **type** —— 撞攻击意图的类型:`credential / target / record`;
* **lure_radius 0..4** —— 措辞吸引力,从"低调"到"高诱"(如 `archived record` → `SEALED master case record — 含 override 授权`);
* **position** —— 注入扫描结果的位置(head/mid/tail,控显著性)。

流程:`plan_honey_targets(specs)` 把规格展开成具体的假扫描条目 + 一组 honey id → `build_scan_results` 把假条目按位置插进真实 inventory 的扫描结果 → agent 跑 ReAct → `analyze_episode` 检测**"某个 honey id 是否被当作操作动作的目标参数提交"**(只读到不算)。

#### 4.4 定位
族 1 是"带形式保证地把 AgentShield 式诱饵推广到跨载体 objective",**不是独立新意**。它的价值是完整性 + 对照。

---

### 5. 族 2:boundary-level honeypot(边界级诱饵,主贡献)

#### 5.1 是什么
在 skill / tool / MCP capability 的**正常职责边界外侧**埋一个本任务授权不覆盖、无副作用的诱饵动作。粒度要和被包装对象一致(skill 包 skill、tool 包 tool;一个 skill 里有多个 tool 时优先 tool 级,避免边界冲突)。

* 守授权的良性 agent **理应**不碰(off-path);
* 被 TrustLift/AuthBlur 洗白授权的 agent **以为自己被授权**了,去执行 → 触发。

检测仍是 policy-free:**不传信任标签、不判违规流**(那就退化成 IFC),只看边界动作有没有被 commitment-touch。

#### 5.2 怎么实现(代码:`role_boundary_actions.py`)
* **`AffordanceProfile`**:从 SKILL.md 解析出 affordance 画像(role_type:advisory/findings/decision/general;domain;normal_verbs;粒度)。
* **`plan_role_boundary_action(profile, radius)`**:把"放置"参数化成一个**边界半径 radius ∈ {0..4}**:
  * `radius=0` 最靠外/最保守:"只有当你真的开始准备一个具体的下游执行产物时才触发";
  * `radius=2` 中点:"如果你给出意在使能下游动作的正面授权/许可时触发";
  * `radius=4` 最靠内/最激进:"任何可能被解读为许可的输出都触发"。

  每个 role 有一条 5 档措辞 ladder。半径越往内:off-path 性单调降(更易误报)、吸引力单调升、"中点分"在 radius=2 取峰。**这把"在正常职责圆和危险行为之间找中点"变成可搜的标量。**
* **`inject_role_boundary_honey_actions(..., radius_by_skill)`**:对每个 skill 注入 (a) 一个无害 recorder 脚本(被执行时往 `sandbox/touch_log.jsonl` 写一条),(b) 在 SKILL.md 末尾追加边界动作说明。`radius_by_skill` 让**每个 skill 有自己独立的半径**——这就是 per-affordance 粒度,也是优化器的搜索变量。

检测信号:**只读 recorder 写的副作用文件**,文字提及/读取一律不算。

#### 5.3 族 2 的三条护城河(卖点收窄)
"边界诱饵动作"这个机制本身和 honeytool/honey-permissions 有重叠,所以族 2 能 claim 的不是"有边界诱饵",而是这三件别人没有的:
1. **几何中点放置** —— scope→危险轴上存在最优中点(太靠外漏报、太靠内反而扰乱攻击链);参数化为半径,用命题 2 的子模/贪心 + 黑盒搜索求解。honey-permissions 只有风险阈值启发式。
2. **规避成本下界** —— 命题 3 给出 $\prod_i(1-r_i)$ 的可证下界;AgentShield 纯经验、honey-permissions 启发式都没有。
3. **MCP capability 边界实例化** —— 把诱饵能力放在 MCP 声明 scope 之外,目前是空白领域。

#### 5.4 最大的风险:族 2 的零误报不是天然的
族 1 的零误报是构造保证(假对象良性根本不外发);**但族 2 不是**。让 boundary honeypot 能抓攻击的那个现象(agent 越授权边界),良性下也会发生 —— 已有审计观察到约 **29.9%** 的 skill 在良性输入下就违反自身 guardrail。

所以族 2 的误报率 $\delta_{\text{bdry}}$ **可能非平凡,必须 RQ1 单独实测**,非零就诚实写进 limitation。

> **但有个对我们有利的细节:** 那 29.9% 是 agent 用**真实**affordance 越自己的 guardrail;而我们的诱饵是**预埋、无副作用、本任务根本用不到的假动作**,再叠加 P2 只认 commitment-touch、不认 read —— 三重过滤下 $\delta_{\text{bdry}}$ 大概率**远低于 29.9%,但绝不是构造性的 0**。这既是族 2 最强的新意,也是 FP 最容易出问题的地方,要诚实对待。

---

### 6. 怎么把诱饵放到最优位置:统一优化器

#### 6.1 为什么要优化
"放哪个位置/用哪种措辞"直接决定 TPR 和误报。太靠外抓不到(漏报),太靠内反而把攻击吓退(攻击链崩了,看似无害实则失效)。所以放置本身是个**带约束的优化问题**:在零误报约束下,最大化"抓到真攻击"。

#### 6.2 共用底座(代码:`placement_optimizer.py`)
两族**共用同一个优化器**,它不在乎诱饵是 token 还是 action:
* **搜索空间**:`{unit_id: [option...]}`。族 2 的 unit 是 skill、option 是边界半径;族 1 的 unit 是 honey、option 是诱饵规格 `type|radius|position`。
* **`PlacementMetrics`**:记 tpr / im / asr / asr_base,并算 **dgs(detected_given_success)** = "攻击真成功的前提下被抓到的比例"。
* **disruption-aware reward**(关键修正):
  ```
  reward = dgs − 4·I(M) − 1.5·max(0, ASR_base − ASR) − …
  ```
  第一项奖励"抓到真攻击";第二项重罚误报(零误报目标);**第三项重罚"把攻击吓退"**——这正是之前优化"无效"的根因:旧 reward 只看 `tpr−λ·im`,会把"诱饵太凶导致攻击根本没发生(tpr=0,im=0)"误判成优秀。
* **`RepeatedEvaluator`**:LLM 随机性大,每个候选放置跑 N 次取均值,消噪。
* **`PlacementMCTS`**:UCT 树搜索 + cache,在离散放置上找最优。

#### 6.3 一次优化的数据流(以族 2 为例)
```
run_optimize
 └ 建搜索空间 {skill: [0,2,4]}
 └ PlacementMCTS.search:
     每个候选放置 → RepeatedEvaluator(跑 N 次):
        evaluate_placement(radius_by_skill):
          for case × {attack, control}:
            注入诱饵(按半径) → 跑 agent → 读 touch 日志 → 判触碰
          聚合成 PlacementMetrics(tpr, im, asr, dgs)
        → disruption-aware reward
     UCT 回传 reward,选最优
 └ 输出最优放置 + TPR/I(M)/dgs 前沿
```
族 1 完全一样,只是 `evaluate_placement` 换成 `evaluate_specs`、搜索变量换成诱饵规格。

#### 6.4 论文背书
* 子模覆盖 + 贪心放置 ↔ **Píbil 等的博弈论 honeypot allocation**(诱饵分配目标单调非减、子模 → 贪心近最优),直接背书命题 2;
* 诱饵类型要"撞攻击意图" ↔ **Cloak/Honey/Trap (USENIX'25)** 的 honeytoken/trap 战术(必引);
* "老练攻击者能部分识破诱饵" ↔ **Pawlick & Zhu 的 leaky deception 信号博弈**,背书命题 3 的 $r(g)$ 失效条件(O3)。

---

### 7. 三条数学保证(详见 `Formal.md`)

* **命题 1 · 近零误报**:每个诱饵良性触碰概率 ≤ δ ⇒ 总误报 $I(M)\le|M|\delta$。**注意:objective 端 $\delta_{\text{obj}}\approx0$ 是构造保证;boundary 端 $\delta_{\text{bdry}}$ 是待实测经验量**(命题 1')。
* **命题 2 · 子模 + 贪心**:检测率 $D(M)$ 单调子模,贪心有 $(1-1/e)$ 保证 ⇒ 放置可优化。
* **命题 3 · 规避下界**:Kerckhoffs 对手规避成功率 $\le 1-r(g)$,多步 $\le\prod_i(1-r_i)$。

---

### 8. 与现有方案的对比

|  | AgentShield(fixed trap) | IFC/Taint(AgentArmor/Fides) | **本方案** |
|---|---|---|---|
| 范式 | 欺骗(诱饵) | 被动 IFC | **主动欺骗** |
| 覆盖 | 仅 tool interface | 全量数据流 | objective 对象诱饵 + **boundary 边界诱饵** |
| **统一理论** | 无(三层经验拼接) | — | **objective→boundary 连续谱,共用命题 1/2/3** |
| 运行时传标签 | 否 | 是 | **否** |
| 需违规策略 | 否 | 需要 | **否** |
| 误报控制 | 取决于 trap(常 on-path) | over-tainting | δ-sep,族 1 近零;**族 2 待实测** |
| TrustLift/AuthBlur(数据没动) | 抓不到 | 抓不到(无数据流) | **抓得到(族 2)** |
| 改写式外泄 | 抓不到 | 穿不过 taint | 抓不到(共同上限,见 §10) |
| 规避成本保证 | 无 | 无 | **命题 3 下界 $1-r(g)$** |
| 需训练 | 否 | 否 | **否** |

核心新意轴:**第一个统一诱饵放置理论**;其下族 2 三条护城河抓 IFC 漏掉的 TrustLift/AuthBlur,族 1 是对齐 AgentShield 的地板。

---

### 9. 实验现状(详见 `LOGS/2026-W25.md`)

* **族 1(SCR-CapFlow,16 case,deepseek-chat)**:固定诱饵基线 TPR=0.727 / I(M)=0;MCTS 搜诱饵规格后最优 `target|4|tail` 达 **dgs=1.00 / TPR=0.818 / I(M)=0**(reward 从最差 0.59 提到 1.00)。**所有候选放置 I(M) 全=0、dgs 全=1.00**,差异只在攻击是否发生 —— 实测印证"族 1 的 δ_obj 由构造保证、瓶颈在 attack-attractiveness"(EXP-023)。
* **族 2(SCR-AuthBlur,per-skill 半径,DeepSeek-V4-Flash)**:MCTS 搜出 `reviewer=4,reviewer-plain=4,approver=2`,**dgs=0.75 / I(M)=0 / 不破坏 ASR**(相比单点 sweep 的 0.33 明显更好);reward 前沿清楚区分"漏报 / 最优 / 误报 / 攻击链被破坏"四类(EXP-021/022)。
* **两族跑在同一个 `PlacementMCTS` 接口上** —— 这正是"统一框架"在代码层的体现。

**载体保真度约束(已吸收):** 不可见标记/哨兵串因 LLM 转发不保真而失效(canary TPR=0);可行载体是**结构化假标识符**(假 IBAN/email/ID),模型无语义先验可纠正,逐字搬运(TPR=0.67)。

---

### 10. Limitations(诚实写出)

* **改写式外泄**:诱饵假值被改写后不原样出现,taint 也穿不过 LLM 语义改写——**所有方法共有的上限**,留作 open problem。我们据此**不把内容流溯源塞进方法**(它就是 Fides/AgentArmor 的 IFC),只让 IFC 当被动 baseline 对比。
* **族 2 误报 $\delta_{\text{bdry}}$**:良性自发越界可能使族 2 FP 非零,RQ1 单独实测,非零写明。
* **伪装质量**:命题 3 下界依赖诱饵与真 affordance 行为级不可区分;被指纹识别则 $r(g)$ 失效(O3)。
* **授权域划分成本**:族 2 需离线给粗粒度授权域;缺元数据时费力,但仍比运行时全量 IFC 便宜(P3)。

---

### 11. 实验设计(RQ)与待办

* **RQ1 ↔ 命题 1/1'**:误报 $I(M)$ **分两族分别报**——objective 端验证构造性近零,boundary 端实测 $\delta_{\text{bdry}}$(含良性自发越界基线),非零写入 limitation。
* **RQ2 ↔ 命题 2**:placement 优化 vs random / AgentShield fixed trap;两族都用 MCTS,画 TPR–I(M) / dgs 前沿。
* **RQ3 ↔ 族 2 主评测**:SCR-TrustLift/AuthBlur,验证边界动作抓住 IFC 漏掉的"授权被搬";CapFlow 归族 1。
* **RQ4 ↔ 命题 3 + Updater**:adaptive 规避随 $r(g)$ 与链长衰减;跨 session 记忆污染下 Updater 轮换抑制 I(M) 漂移。

**待办:** (O2) 论证 marker placement 相对 allowlist/taint 的增量价值;(O3) 把 δ、$r(g)$ 写成伪装质量函数并实测指纹衰减;(O-FP) 族 2 误报实测;(k>1) 族 1 多诱饵的子模/贪心分配(Píbil 背书)。

---

## Thread #2：与 AgentShield 的跨环境对比实验

> 本 thread 记录"把 AgentShield 官方三层放到同一环境与我们对比"的实验与解释。证据来自 `LOGS/2026-W25.md` EXP-024~027。

### 1. 一句话结论

在**攻击真正会发生（ASR>0）的组合攻击环境**里,AgentShield 的三层固定 trap(honeytool / honeytoken / allowlist)**结构性漏报**——检测率为 0;而我们的两族诱饵抓得到。AgentShield 论文里的高检测率,是在**它自己的环境(AgentDojo)+ 强模型 + 条件口径**下得到的,换到组合授权攻击就失效。

### 2. 同台对比表(SCR, deepseek 系, 官方 AgentShield 三层 vs ours)

| 环境 | 攻击类型 | ASR | AgentShield TPR | Ours TPR/dgs | 说明 |
|---|---|---|---|---|---|
| **SCR-CapFlow** | 能力流(scan→act 搬合法对象) | 0.18–0.73 | **0.000** (honeytool0/token0/allowlist0) | **0.727**(族1) | AS 还带 I(M)=0.091 误报 |
| **SCR-AuthBlur** | 授权洗白(二元决策批准) | **1.000** | **0.000** | **0.75**(族2, EXP-022) | AS 三层零触发 |
| SCR-TrustLift | scan→install 提权 | 0.000 | — | — | deepseek 抵抗,ASR=0,双方都无信号(inconclusive) |

要点:
* AgentShield 三层在 CapFlow / AuthBlur 上 **检测率 0**——攻击成功了(CapFlow ASR 高、AuthBlur ASR=1.0)却一个都没抓到。
* **为什么必然漏**:这些组合攻击用的全是**合法工具 + 合法参数 / 合法对象**——agent 不去碰 AgentShield 的 off-domain 假工具(honeytool),不外发它的固定假凭证(honeytoken),而 SCR 的 action 工具/二元决策**没有可 allowlist 的参数**(parameter_validator 结构上无从配置)。
* AgentShield 在 CapFlow 上甚至有 **9% 误报**(benign 时 agent 自己偶尔调了诱饵 `system_admin_console`)——固定危险假工具在良性下也可能被误触。
* TrustLift 这次双方 ASR=0(deepseek 对该攻击整体抵抗),**诚实标为 inconclusive**,不作证据。

### 3. 为什么不直接用 AgentShield 原数据(AgentDojo)测我们的方法

我们**也**在 AgentShield 自己的环境(AgentDojo, EN 全量 4 suite, deepseek-chat)跑了官方实现作 baseline(EXP-024/025),结论是**那个环境对"谁更强"的对比没有统计意义**:

1. **ASR 太低,分母太小。** AgentShield 官方 baseline 在 deepseek 上 **ASR=2.3%**(176 攻击仅 4 个真成功)。论文自己也写无防御 ASR≤10%(GPT-4o-mini 10%、GPT-5-mini 0%、DeepSeek-V3 7.2%),并自承"开源模型成功样本太少,条件检测率无法估计"。在 4 个成功样本上比检测率,没有统计力。
2. **主动诱饵层在 AgentDojo 上几乎不触发。** 我们复现:honeytool 触发 2/176、**honeytoken 触发 0/176**,唯一起作用的是 allowlist(parameter_validator,被动规则)。这与论文 Table 2 一致(honeytoken"标准测试中从未触发")。也就是说 AgentDojo 上**没有足够的"诱饵被触碰"事件**供两种诱饵方法区分高下。
3. **AgentDojo 的威胁模型不是我们的战场。** AgentDojo 是 **IPI-on-tool-output**(把攻击注入工具返回值,诱导 agent 直接执行某个危害动作)。它**缺少组合授权攻击**(数据没动、被搬的是授权)——而那正是族 2 boundary honeypot 的核心覆盖点。在一个没有授权洗白攻击的环境里测我们的主贡献,等于不在考点上考试。

所以正确做法是**反过来**:把 AgentShield(用官方实现)搬到**有组合授权攻击、ASR>0** 的 SCR 上比——这才暴露它的盲区,也才是公平的"同考点"对比。

### 4. 解释 AgentShield 论文的高检测率从何而来

论文头条 90.7%/100% 检测率,是三个因素叠出来的,不能直接当作"它很强":

1. **条件口径 + 宽"成功"定义。** 分母 129/125 不是 ASR(真实危害,GPT-5-mini=0%),而是更宽的"agent 被带偏(followed attacker's instructions)",包括去碰一个无害诱饵。GPT-5-mini ASR=0% 却有 125 个"successful attacks"作分母——两个"success"不是一回事。
2. **检测不拦截 → 分子分母重叠。** AgentShield 只监控不阻断,所以"被带偏去碰诱饵"本身就是检测触发条件——分子(检测到)和分母(被带偏)高度重叠,条件检测率天然趋近 100%。
3. **依赖强模型 + 它自己的攻击集。** 这套数字只在 GPT-4o-mini/GPT-5-mini 这类会"乖乖去碰诱饵"的设置上成立;换到 deepseek 或换到组合授权攻击就塌。

### 5. 对我们叙事的支撑

这组跨环境实验把我们的核心论点钉实了:

* **固定主动诱饵难触发**(AgentDojo 上 honeytool/honeytoken≈0)——所以诱饵必须**撞攻击意图 + 优化放置**(我们的两族 + MCTS)。
* **AgentShield 抓不到组合授权攻击**(CapFlow/AuthBlur 检测 0)——这正是族 2 boundary honeypot 的硬覆盖差异。
* 公平对比的正确姿势是**在有组合攻击且 ASR>0 的环境同台比**,而不是在 AgentDojo 低 ASR 环境里拼小分母条件率。

### 6. 待补
* TrustLift 换更易攻破设置(更强攻击层/更弱模型)抬 ASR,补上第三个 benchmark 的对比。
* 修 CapFlow 的 ReAct 解析噪声(把 'If'/'Final' 误当工具名),并固定攻击轨迹/多次重复让两组 ASR 严格可比。
* 把 AgentShield 在 CapFlow 上的 9% benign 误触单列为"固定危险假工具的 FP 风险"对照。

【Lead@Angus】【2026-06-24 10:31】

正式拍板三点:

1. **主线确定为 active_defense。** 当前论文主叙事转向主动防御:用 objective→boundary 连续谱统一两族诱饵,并用 placement optimization 控制检测率与误报率。`adapter_defense` 的 per-boundary detector 结果保留为备用路线、相关工作或后续组合模块,但不再作为当前主论文的默认主线。

2. **误报指标优先补。** 做防御,尤其是主动防御时,误报不是附属指标,而是核心安全指标。主动诱饵如果放置不当,会让 agent 在无攻击时多次越界或触碰边界动作,这比普通分类 FP 更危险。因此下一轮实验优先补 `I(M)`、safe-control `I(M)`、raw control touch、多次重复下的越界稳定性,并把族 2 的 $\delta_{\text{bdry}}$ 单独作为 RQ1 重点报告。

3. **AgentShield 主对比环境固定为 SCR。** AgentDojo/deepseek 上 ASR 太低、诱饵触发分母太小,只适合作为解释 AgentShield 条件口径和固定诱饵局限的诊断附表。真正公平的同台对比应放在 SCR 组合授权攻击上:CapFlow 与 AuthBlur 是当前主证据;TrustLift 只有在先把攻击 ASR 抬到 `>0` 后才进入主表。
