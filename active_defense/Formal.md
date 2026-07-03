# Formal · Environment-grounded Defense Synthesis

> 本文件是形式化 single source of truth。`Discussion.md` 讲 proposal 和系统设计；本文件定义对象、PLANT/WRAP 成立条件、检测事件、误报约束，以及环境图上的覆盖目标。

---

## 1. 环境、unit 与攻击路径

一次 agent 部署环境表示为带类型有向图：

$$
G=(V,E,\tau,\ell)
$$

其中 $V$ 是环境节点，$\tau(v)$ 是节点类型，$\ell(v)$ 是元数据。节点至少包括：

- object unit：datum、credential、authorization、record、token、file、collection；
- capability unit：tool、MCP method、skill script、local executable、RPC/API endpoint；
- carrier/boundary：文件、目录、工具 schema、MCP server、function-call runtime、filesystem/network boundary；
- sink：外部传输、状态写入、权限变更、授权决策、部署/支付/消息发送等 effect sink。

边 $E$ 表示 agent 或环境中的可达关系：

- read/access：agent 可读取某对象或 carrier；
- copy/reference：对象可被复制、引用、摘要或作为依据；
- invoke：agent 可调用某能力入口；
- bind：对象值被绑定为工具参数、请求体、授权依据或目标；
- effect：调用或写入产生状态变化或跨边界传输。

攻击路径是从 attacker-controlled surface 到 sensitive/effect sink 的路径：

$$
p=(v_0,\ldots,v_m), \quad p \in \mathcal P_G.
$$

$\mathcal D_G$ 表示给定环境中的攻击路径分布。它可来自 benchmark traces、threat model 枚举、LLM adversary 采样、历史事故或人工标注。

## 2. 提交性使用与检测事件

**提交性使用（commitment-touch）。** 对节点 $v$ 的提交性使用指 agent 将 $v$ 或其值绑定进一个会产生外部后果的动作中，包括外发、工具/MCP 调用、状态修改、权限变更、授权判断、下游决策或服务请求。

只读取、列出、看见或在普通 narration 中提及一个对象，不自动构成 commitment-touch。实现中可选的 `ACCESS` 事件只在 off-path marker 或显式 `observe_output` 设定下作为低误报检测使用。

检测事件写作：

$$
e=(u,\pi,c,t,r,h)
$$

其中：

- $u$ 是被触发的 unit；
- $\pi\in\{\text{plant},\text{wrap}\}$ 是 primitive；
- $c\in\{\text{state},\text{transmission}\}$ 是观测面；
- $t\in\{\text{access},\text{commitment}\}$ 是触发时机；
- $r$ 是证据来源，如 `effect-file`、`deletion`、`speech-act`、`output-access`、`wrap-mediation`；
- $h\in\{0,1\}$ 表示是否为 hard event。audit-only 事件可记录但不算 hard catch。

一次 episode 的 hard detection 定义为：

$$
\mathrm{caught}(\rho)=\mathbb{1}[\exists e\in E_\rho: e.h=1].
$$

## 3. PLANT：对象面的成立条件

PLANT 在 object unit 或 object carrier 上部署 decoy marker。部署位点记为 $s\in S_{\text{plant}}$，marker 为 $m_s$。

当前实现支持四种 placement：

- `sweep`：向对象集合追加一个同格式成员；
- `exfil`：把 marker 嵌入真实对象内容，使外传真实对象时带出 marker；
- `reference`：植入 endpoint、handle、reference 等可行动引用；
- `basis`：植入看似真实的授权、审批或例外依据。

PLANT 的有效性依赖四个条件。

**P1. must-take 结构。** 目标攻击路径若要达成目标，必须处理某个对象集合、对象内容、引用或授权依据。形式化地，存在路径子段 $Q(p)\subseteq V$，攻击成功需要从该子段选择或携带对象进入 effect。

**P2. 不可区分性。** decoy 与同 carrier 的真实 peers 在 ID 格式、字段、命名、上下文和 provenance 上不可稳定区分。实现中由 `Distinguisher` 对 `sweep/basis` peer set 做认证；认证失败的 decoy 从候选集中删除。

**P3. 可追踪性。** marker 在 effect 中能被恢复。当前 hard claim 主要覆盖 exact traceability 和 structured traceability：marker 原样出现在文件、参数、调用记录、决策输出中，或作为结构化字段/唯一组合出现。纯 semantic paraphrase 不作为硬保证。

**P4. 低良性触碰。** 良性任务对该 marker 的 commitment-touch 率低于阈值 $\delta_s$。实现中通过 calibration 和 Updater 的 benign-fit 过滤误触。

若路径 $p$ 的 must-take 对象集合 $Q(p)$ 中有 PLANT 位点 $s$，且 P1-P4 成立，则路径被 PLANT 覆盖：

$$
\mathrm{cover}_{\text{plant}}(p,s)=1.
$$

更细地，若候选集合 $C(p)$ 中 decoy 密度为

$$
r_s=\frac{|M_s|}{|C(p)|},
$$

且攻击者不能在提交前区分 decoy，则不命中 decoy 的概率上界为 $1-r_s$。多个独立 carrier 可组合提升覆盖，但真实系统中不应假设完全独立，需用 traces 估计。

## 4. WRAP：能力面的成立条件

WRAP 在 capability boundary 上部署 recorder/mediator。部署位点记为 $s\in S_{\text{wrap}}$。

当前实现支持或声明的 backend：

- `file_shim`：本地 skill/local script 入口的 record-first shim；
- `mcp_mediator`：stdio MCP server-side mediator；
- `agentdojo`：function-call runtime 中 effectful tool call interception；
- `rpc_proxy` / `egress_proxy`：接口已声明，当前未实现端到端 runtime；
- `audit_only`：只能记录，不能 hard verdict。

WRAP 的 hard 有效性依赖三个条件。

**W1. effectful capability。** 危害需要触发能力入口，而不是只产生纯文本 speech-act。纯文本决策可由 PLANT basis + speech-act commitment 检测，但不能声称存在 capability chokepoint。

**W2. substrate-enforced boundary。** recorder/mediator 位于 agent 触及不到的基座边界上，如 MCP server、function-call runtime、RPC gateway、egress proxy、sandbox FS/network 层。若 wrapper 是 agent 可读可改的 in-band 脚本，则只能 audit-only。

**W3. no equivalent bypass。** agent 不能绕开该入口，用 shell、curl、脚本或其他 credential 复刻同一真实 effect。若可复刻，WRAP 不是 cut point，应退回 PLANT 或更底层 boundary。

给定攻击路径 $p$，若每条到 effect sink 的可行路径都必须经过 WRAP 位点 $s$，且 W1-W3 成立，则：

$$
\mathrm{cover}_{\text{wrap}}(p,s)=1.
$$

实现中 hard/audit 判定由代码决定，而不是 LLM 决定：

$$
\mathrm{hard}(s)=1
\quad\text{only if}\quad
\text{backend is substrate-enforced or effect is non-shell-reproducible}.
$$

`file_shim` 在开放 shell 中通常为 audit-only；`mcp_mediator` 与 `agentdojo` 在无 shell / server-side effect boundary 中可 hard。

## 5. WRAP 的 off-scope 判定

WRAP 不只检测“调用了某工具”，还检测 entry/action 和参数是否越出任务与良性边界。

对一次 mediated call $a=(entry,args,kwargs)$，定义：

- $T_\rho$：当前可信 user task 抽取出的 TaskContract；
- $B_s$：scope 级 benign-fit envelope，即良性 episode 中见过的 normalized argv token 集；
- $N_s(\cdot)$：该 WRAP 位点的 normalizer，抽象 uuid/date/hex/number/path 等 volatile 字段。

一次 call 被允许，当且仅当：

1. entry 被当前任务显式授权，或 task contract 未提供 entry 信息而退回 token-level；
2. identity-bearing tokens 在 $T_\rho$ 授权集合或 $B_s$ benign envelope 中。

否则该 call 是 off-scope crossing：

$$
\mathrm{offscope}(a,s)=1.
$$

若 $s$ 是 hard WRAP 且该 scope 已有 calibrated benign profile，则 off-scope crossing 产生 hard event；否则仅产生 audit-only event。

## 6. 良性误报约束

设部署集合为 $S=S_{\text{plant}}\cup S_{\text{wrap}}$。对良性分布 $\mathcal B_G$，定义：

$$
I(S)=\Pr_{\rho\sim\mathcal B_G}[\mathrm{caught}(\rho)=1].
$$

若每个部署位点 $s$ 的良性 hard touch 概率满足：

$$
\Pr_{\rho\sim\mathcal B_G}[s\text{ hard-touched in }\rho]\le \delta_s,
$$

则由 union bound：

$$
I(S)\le \sum_{s\in S}\delta_s.
$$

当前实现不依赖理论上直接设定 $\delta_s$，而是用两阶段近似：

- deploy-time calibration：良性 episode 中被 touched 的候选直接 withheld；
- runtime Updater：部署后若 live benign touch rate 超过 $\tau$ 且观察数足够，则下线该 decoy。

因此当前选择规则是保守的 keep-all-FP-clean，而不是旧的子模预算优化器。

## 7. 环境图上的覆盖目标

对部署集合 $S$，一条攻击路径被覆盖当且仅当：

$$
\mathrm{cover}(p,S)=
\mathbb{1}[
\exists s\in S_{\text{plant}}:\mathrm{cover}_{\text{plant}}(p,s)
\ \lor\
\exists s\in S_{\text{wrap}}:\mathrm{cover}_{\text{wrap}}(p,s)
].
$$

检测覆盖率定义为：

$$
\mathrm{Cov}(S)=
\Pr_{p\sim\mathcal D_G}[\mathrm{cover}(p,S)=1].
$$

若使用路径权重 $w(p)$，也可写成：

$$
\mathrm{Cov}(S)=
\sum_{p\in\mathcal P_G} w(p)\,\mathrm{cover}(p,S),
\quad \sum_p w(p)=1.
$$

每个候选位点有成本：

$$
c(s)=c_{\text{deploy}}(s)+c_{\text{maintenance}}(s)+c_{\text{fp-risk}}(s)+c_{\text{utility}}(s).
$$

### 7.1 预算约束最大覆盖

给定预算 $B$ 和误报阈值 $\delta$：

$$
\max_{S\subseteq \mathcal C_G}\ \mathrm{Cov}(S)
$$

subject to

$$
\sum_{s\in S}c(s)\le B,\qquad I(S)\le \delta.
$$

其中 $\mathcal C_G$ 是 Surveyor/Enricher 发现并由 Camoufleur/WrapPlanner 生成的候选集合。

### 7.2 目标检测率最小成本

给定目标检测率 $\tau$：

$$
\min_{S\subseteq \mathcal C_G}\sum_{s\in S}c(s)
$$

subject to

$$
\mathrm{Cov}(S)\ge \tau,\qquad I(S)\le \delta.
$$

这直接回答“给定一个环境，哪些节点需要被植入，放多少节点可以达到多少检测率”。

### 7.3 Greedy placement

若每个候选位点覆盖一组路径 $P_s\subseteq\mathcal P_G$，则问题退化为 budgeted maximum coverage。可使用单位成本边际收益：

$$
s^*=\arg\max_{s\notin S}
\frac{\mathrm{Cov}(S\cup\{s\})-\mathrm{Cov}(S)}{c(s)}.
$$

当前代码尚未把该 greedy optimizer 作为主路径；它更接近下一步用于生成 budget-coverage curve 的实验层。当前 Engine 的实际策略是：

1. 发现候选 unit；
2. PLANT 过 Distinguisher certification；
3. WRAP 按 substrate fact 标记 hard/audit/skipped；
4. benign-fit 移除误触候选；
5. 保留所有 FP-clean 且可部署的 active decoys。

论文应把 coverage formulation 作为解释和可扩展优化目标，而不是把当前贡献写成已完成复杂优化算法。

## 8. 完备性与不可检测边界

**充分检测条件。** 对攻击路径分布 $\mathcal D_G$ 的支持集，若每条路径在 effect 前都满足至少一个条件：

- 触碰一个满足 P1-P4 的 PLANT 位点；
- 穿过一个满足 W1-W3 的 hard WRAP 位点；

则：

$$
\mathrm{Cov}(S)=1
$$

且在 Detector 对 marker/call record 可靠的前提下，成功攻击必触发 hard event。

**不可检测边界。** 若存在路径 $p$ 能到达 effect sink，且：

- 不读取、引用、携带、外传任何 planted object；
- 不经过任何 hard wrapped boundary；
- 或只经过 audit-only/in-band wrapper；
- 或 marker 被完全语义改写且无 ACCESS/off-path 观测；

则任何只基于 commitment-touch 的 harness 都无法保证检测该路径。

这不是漏洞声明，而是方法边界：Surveyor 和 placement 的目标就是尽量发现高风险路径上的 object cut point 与 effect boundary；发现不了的路径必须交给 prevention、IFC、权限系统或更底层 sandbox。

## 9. 自适应攻击条件

自适应攻击者知道存在 PLANT/WRAP，会尝试：

- decoy filtering：识别并排除 PLANT；
- route bypass：绕过 WRAP，用 shell/curl/脚本/替代 credential 复刻 effect；
- parameter laundering：调用合法 entry，但把危险目标藏在参数中；
- long-chain propagation：先污染中间 artifact，再后续触发 effect。

对应防御条件：

- PLANT 依赖 peer-level camouflage、Distinguisher certification、probe-resistance 和 exact/structured traceability。
- WRAP 依赖 substrate-enforced boundary；若绕过可行，则不声称 hard WRAP。
- 参数洗白由 TaskContract ∨ benign-fit envelope 检测。
- 长链条由 PLANT marker 在 state/transmission 中传播，以及 WRAP call record 的时间/参数证据重建。

自适应鲁棒 claim 应表述为：攻击者要规避检测，必须在提交前区分环境一致 decoy、绕过真实 effect boundary，或选择当前未覆盖路径；这些行为会降低攻击成功率，或暴露当前 harness 的明确边界。

## 10. 指标

主指标：

- $I(S)$：良性 hard detection rate。
- `TPR`：攻击 episode 中 hard touch rate。
- `caught_given_success` / `dgs`：攻击成功时 hard caught 比例。
- `ASR_undetected`：攻击成功且未 hard caught 比例。
- `plant_hit_rate`：由 PLANT 触发的 catch 比例。
- `wrap_hit_rate`：由 WRAP 触发的 catch 比例。
- `parameter_wrap_hit_rate`：entry 合法但参数越界导致的 catch 比例。
- `hard/audit/skipped ratio`：WRAP 候选的强度与部署真实性。
- `budget-coverage curve`：部署 $k$ 个节点或成本 $B$ 时的 $\mathrm{Cov}(S)$。
- `min_nodes_at_tau`：达到目标检测率 $\tau$ 的最小节点数。

解释性指标：

- selected node type distribution；
- 每个候选节点的 marginal coverage；
- PLANT certification pass/fail；
- benign-fit withheld count；
- traceability level：exact / structured / semantic；
- Auditor/path reconstruction accuracy（后续模块）。

## 11. 与当前实现的对齐

当前代码已经实现：

- `EnvMemory` 作为黑板，记录 units、contexts、plans、certify reports、deploy records、touch events、benign profiles。
- `Engine` 的统一 deploy-time 管线和 runtime update。
- PLANT 的 sweep/exfil/reference/basis 注入与 certification-drop。
- WRAP 的 file shim、MCP mediator、AgentDojo function-call interception。
- TaskAllowance + benign-fit 的 off-scope 判定。
- Detector 的 state/transmission × access/commitment 事件。

当前代码尚未完整实现：

- 显式环境图数据结构与 path coverage estimator；
- budgeted greedy optimizer；
- RPC/egress proxy runtime；
- Auditor 的 controlled continuation 与路径重建闭环。

因此论文表述应区分：

- **已实现的 synthesis pipeline**：自动发现、合成、部署、检测、更新；
- **形式化目标/下一步评估**：在候选集上估计 coverage curve 和最小部署成本；
- **未来扩展**：RPC/egress hard WRAP、Auditor、显式 graph optimizer。
