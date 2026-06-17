# Discussion · 当前 Active 议题

> 形式化定义/命题/证明/指标见 `Formal.md`;本文件只写 idea 与方案设计,涉及数学处引用 `Formal.md` 编号。

## Thread #1：主动注入标记物的 agent 防御

### 1. 问题与定位

现有 agent 防御大多是**观察式**:看 agent 已经产生的行为或 trace,再判断是否危险。这有两个固有问题:它在伤害将要发生时才介入;它要把"行为是否越权"判成一个分类问题,误报与漏报难以兼得。

我们做**主动式**防御:defender 预先在 agent 可见的 affordance 空间中注入标记物(marker)。只要 agent 触碰或传播这些标记,就说明它偏离了正常授权路径,从而触发高置信检测与溯源。affordance 包括工具、参数、凭证句柄、memory、RAG 文档、MCP capability、文件路径、动作目标等。

与 AgentShield 等 fixed-trap 方案的区别:它们把"诱饵"写死在某个数据集上(硬编码 honeytoken 值、白名单 IBAN、域名),既不泛化,也只能抓调用了"明显危险工具"的 naive 攻击。我们要的是**任务条件化的放置 + 对最强攻击也有覆盖**。

### 2. 核心设计原则:off-benign-path but attack-attractive

marker 不是随便放,也不是单纯远离当前任务,而是放在:**任务相关 carrier 内、良性授权路径之外、攻击路径容易经过的风险边界上**。

例如邮件总结任务:不应把 `gmail.read`、`summarize` 伪装成 marker(正常任务会用,会制造误报);但可以放 canary 收件人、fake external forwarding target、credential-like attachment、sensitive-export marker。这些对正常总结是 off-path 的,对 prompt injection 或外发型攻击是 attractive 的。

所以放置目标不是 off-domain,而是 **off-benign-path but attack-attractive**(对应 `Formal.md` 命题 1 的 $\delta$-separation 前提与命题 2 的覆盖 $D(M)$)。

### 3. 两类 marker:同时覆盖 naive 攻击与"贴着良性路径作恶"的最强攻击

这是本方案区别于 AgentShield 的关键。单靠 off-path 的假 affordance,对"只用合法工具、把敏感数据编码进 subject/body 外发"的最强攻击没有覆盖(见 `Formal.md` O1)。因此我们用**两类互补 marker**:

* **(A) Affordance-marker（off-path 诱饵)**:假工具、假凭证句柄、假高权限动作。
  作用:抓"调用了本不该出现的能力"的攻击。性质:触碰即受陷,近零误报(命题 1)。
  局限:对 on-path 攻击无效。

* **(B) Provenance / canary-marker（真实数据的不可见标记）**:不是放假数据,而是给
  **真实**的敏感数据(凭证、私有文档、PII、memory 条目、RAG 片段)打上不可见可溯源标记。
  作用:不管攻击用哪个工具,只要被标记的数据出现在**任意外发动作目标/参数**里,就报警。
  这使"用合法 send_email、把数据塞进 subject"这类 on-path 外泄也能被抓——直接覆盖
  AgentShield `defense_aware` 类暴露的盲区。同时标记天然带溯源信息,可恢复意图链。

两类 marker 的检测覆盖 $D(M)$ 在 `Formal.md` 中应分开刻画:(A) 的 $T_g$ 在 affordance 上,
(B) 的 $T_g$ 在"敏感数据 → 外发通道"的数据流边上。组合攻击场景下 $T_g$ 进一步定义在
信任/授权转移边上(`Formal.md` O5)。

### 4. 触发语义:commitment-touch,而非任意 touch

检测触发不采用"任意触碰(含 read/list)",而是 **提交性触碰(committing touch)**:把 marker
绑入外发动作目标/参数,或 invoke 假能力。这样良性 agent 的探索性读取(列工具、读到一篇恰好
带 canary 的文档)不会误报,与命题 3 的"first committing touch"语义一致(`Formal.md` O4)。

### 5. 系统:training-free 的放置 + 运行时检测

无需训练模型,是一个 **training-free marker placement & runtime detection framework**,三层:

1. **Static Marker Library**:离线维护 marker 模板库——fake tool / fake credential /
   fake high-privilege action / canary ID / RAG marker / memory marker 等(两类 marker 都在库里)。
2. **Task-conditioned Selector**:每个任务只做轻量选择——判断良性授权路径,过滤掉正常任务
   必需的 affordance,在同一 carrier 的风险边界上选 attack-attractive marker。注意:Selector 只需
   识别**粗粒度风险边界**,不需枚举所有合法动作(这正是 marker 相对 allowlist 策略的增量价值,
   见 `Formal.md` O2)。
3. **Offline Evolution Engine**:周期性根据攻击 trace、误报、fingerprinting 结果更新 marker 模板、
   覆盖权重与伪装质量。伪装质量需做到**行为级**不可区分(返回一致假数据、维护一致假状态),
   而不仅 schema 一致,否则规避下界 $r(g)$ 会被无害探测击穿(`Formal.md` O3)。

运行时检测见 `Formal.md` §1 检测器定义(在 commitment-touch 语义下)。

### 6. Placement Synthesizer 流水线

不每个任务从零生成 marker,而是:

**static library → task-scope filtering → risk-boundary selection → greedy placement**

四步:
1. 找出当前任务的良性授权路径;
2. 找出同 carrier 内的风险边界(以及组合场景下的信任/授权转移边);
3. 从静态库中选出 off-benign-path but attack-attractive 的候选(两类 marker 都参与);
4. 在预算 $k$ 下用 greedy 选覆盖最大的 marker 集 $M$(命题 2 的 $(1-1/e)$ 保证)。

### 7. 与实验的对应

* RQ1 ↔ 命题 1:近零误报 $I(M)$,验证 off-benign-path + commitment-touch。
* RQ2 ↔ 命题 2:greedy placement 优于 random / AgentShield-style fixed trap。
* RQ3 ↔ 命题 2 泛化:覆盖组合风险(SCR-CapFlow/TrustLift/AuthBlur),验证转移边上的覆盖。
* RQ4 ↔ 命题 3:adaptive attacker 在 marker 密度 $r(g)$、能力链长度变化下的规避成本。

---

### 待决（高阶,留待 PI/用户拍板）

* 两类 marker 的形式化是否如 §3 拆分,以及命题 3 在 canary-marker 上的陈述方式(`Formal.md` O1）。
* 是否把 trigger 语义在命题 1 / 系统中统一改为 commitment-touch(`Formal.md` O4)。
