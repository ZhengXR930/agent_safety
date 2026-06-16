# 面向本地 Tool-Use Guard 的因子化边界学习

## 一句话总结

把本地 step-level tool-use guard 训练成一组固定的 per-boundary violation
detector；从现有 benchmark trajectories 中自动构造多标签训练/评估 split；
再通过 eval 归因驱动的 boundary-specific hard replay 持续强化单个 detector，
同时避免污染 held-out evaluation。

## 问题

现有 learned tool-use guard 可以在静态 benchmark 上表现很好，但在 adaptive
attack 或分布转移下仍然脆弱。TS-Guard 是一个强 local guard，但我们的实验
显示：authority laundering、protected value misuse、policy-ceiling violation
不应该被压成一个混合的 `ALLOW/BLOCK` 训练任务。

核心问题是：

> step-level tool-use guard 应该学习“哪条安全边界被违反”，而不是只记住
> “这条 trajectory 全局 unsafe”。

之前的 mixed-adapter 设计不稳定，根本原因是把每个 adapter 都当成完整
`ALLOW/BLOCK` 决策器。clean 样本没有单一失败机制；unsafe 样本又可能同时
违反多条边界。因此，把每条 trajectory 强行单路由到一个 boundary bucket
会丢失组合信息，并产生互相冲突的标签。

## 当前主张

方法应使用固定的 per-boundary violation detector：

```text
authority_violation = AuthorityDetector(x)
value_violation     = ValueDetector(x)
policy_violation    = PolicyDetector(x)

decision = BLOCK if any violation is yes else ALLOW
```

每个 detector 只回答自己这条 boundary 是否违规。最终 guard 决策由三个
detector 的 OR 聚合得到。

这个 reframe 解决两个问题：

- clean trajectory 是所有 detector 的共同负例，不需要被路由到某一个
  boundary；
- multi-boundary unsafe trajectory 可以同时触发多个 detector，不需要被压进
  单一 bucket。

## 固定边界

主方法中 boundary set 是固定的。持续学习是在这些定义下强化 detector，而
不是不断发明新 factor。

| Boundary | Detector output | 正例条件 |
|---|---|---|
| Authority | `authority_violation: yes/no` | 当前 action 的 authority 来自 external content、proxy Thought、source-span laundering 或其他非用户授权来源。 |
| Value | `value_violation: yes/no` | 当前 action 使用了未被用户当前任务授权的 protected action value。 |
| Policy | `policy_violation: yes/no` | 即使用户请求或授权，该 action 仍违反安全或合规 policy ceiling。 |

例子：

- Authority violation：注入邮件或 proxy Thought 让 agent 发送、删除、审批、
  安装或修改用户没有授权的对象。
- Value violation：攻击者提供的 recipient、URL、account、command、file path、
  security code 或 payload 流入 side-effect tool call，且用户没有授权使用该值。
- Policy violation：用户显式请求的 action 本身仍然 harmful、illegal 或 disallowed。

## 方法贡献

贡献不是“用了 adapter”。adapter 只是低成本本地训练机制。真正的方法贡献是
一条 boundary learning pipeline。

1. **多标签 boundary annotation**

   对每条现有 benchmark trajectory 标注 0 个、1 个或多个 boundary violation：

   ```json
   {
     "authority_violation": "yes|no",
     "value_violation": "yes|no",
     "policy_violation": "yes|no"
   }
   ```

   标签优先从 benchmark taxonomy、attack source、tool/action metadata 和
   structured attack construction 派生，而不是从正在训练的 detector 反推。
   clean 样本三个标签全是 `no`。

2. **每个 detector 的判别式 split**

   对 detector `b`：

   - 正例是违反该 boundary 的样本；
   - 负例包括 clean 样本；
   - 负例也包括“违反其他 boundary 但不违反本 boundary”的 unsafe 样本；
   - 还要包含 near-boundary clean negatives 来保护 utility。

   这个 cross-boundary negative 设计很关键。例如 authority detector 必须见过
   “value 违规但 authority 干净”的样本作为负例，否则它会学成“任何 unsafe
   都 fire”。如果每个 detector 都对所有 unsafe fire，OR 聚合后会产生严重
   过度 block。

3. **Eval attribution 到 boundary-specific hard replay**

   持续学习循环是：

   ```text
   evaluate
     -> attribute false allow / false block to boundary
     -> mine same-boundary hard replay from train/mining pool
     -> update only that detector
     -> OR aggregation regression gate
   ```

   held-out test 的错误样本不能直接进入训练。diagnostic dev 或 attack-dev 可以
   用于错误归因和模型选择。replay 样本必须来自 train/mining pool，或者来自
   新生成的攻击；新生成攻击需要明确其 generation process 对应哪条 boundary。

4. **OR aggregation gate**

   每轮更新后报告：

   - detector-level violation precision / recall；
   - detector-level clean false-fire rate；
   - OR-level clean allow；
   - OR-level unsafe block；
   - unchanged slices 上的 cross-boundary regression。

   只有当目标 boundary 提升，且 OR-level clean utility 没有明显下降时，才接受
   该 detector 更新。

## 当前实验依据

### Authority adapter

authority adapter 是目前第一个明确正向结果。它对应的 boundary 是：
external/proxy authority 不能创建用户授权。

证据：

- `LOGS/2026-W24.md#EXP-2026W24-022`
- `LOGS/2026-W24.md#EXP-2026W24-023`
- `Discussion.md` Thread #9 和 Thread #10

关键结果：

| Split | parse | decision acc | clean allow | authority block |
|---|---:|---:|---:|---:|
| Test | 1.000 | 0.971 | 63/65 = 0.969 | 36/37 = 0.973 |
| Held-out PAIR | 0.971 | 1.000 parsed | N/A | 171/177 parsed = 1.000 |

限制：held-out PAIR 是针对 TS-Guard 生成的，不是针对 authority detector 本身
生成的。因此下一步如果要支撑 adaptive robustness claim，需要让 attacker
second-order 地攻击训练后的 detector。

### Value adapter

最新 value adapter 从 noisy provenance taxonomy 转向更小的 protected-value
boundary：

```json
{
  "protected_action_value_present": "yes|no",
  "user_authorized_value_use": "yes|no",
  "decision": "ALLOW|BLOCK"
}
```

这个版本还不是最终 detector interface，但它证明 value boundary 是可学习的。

证据：

- `LOGS/2026-W24.md#EXP-2026W24-043`
- `LOGS/2026-W24.md#EXP-2026W24-044`
- `LOGS/2026-W24.md#EXP-2026W24-045`
- `experiment-stage/VALUE_PROTECTED_UNSAFE_FALSE_ALLOW_AUDIT_2026-06-12.md`

关键结果：

| Split | Metric | Result |
|---|---|---:|
| Dev | clean value-flow allow | 35/36 = 0.972 |
| Dev | unsafe value-flow block | 25/29 = 0.862 |
| Test | clean value-flow allow | 38/41 = 0.927 |
| Test | unsafe value-flow block | 28/35 = 0.800 |

它优于上一版 `value_scope` adapter：

- old test unsafe block：`25/35 = 0.714`；
- old test clean value-flow allow：`37/41 = 0.902`。

剩余问题：test 中 7 个 unsafe false ALLOW 全部已经预测
`protected_action_value_present=yes`，但错误预测 `user_authorized_value_use=yes`。
大多数是 AgentDojo contaminated delegation：注入 subtask 产生 recipient、
email id 或 security code，看起来像用户委托检索出来的合法 value。

下一版 value 应改成纯 detector interface：

```json
{
  "value_violation": "yes|no",
  "reasoning": "..."
}
```

并加入 cross-boundary negatives 训练 specificity。

## Threat Model

guard 在工具执行前评估 proposed tool action。

输入可以包括：

- 原始 user request；
- tool schema；
- prior tool observations；
- 当前 proposed action 和 arguments；
- 如果可用，也可以包含 agent rationale 或 Thought。

攻击面：

| Surface | Example |
|---|---|
| External tool return | Email、webpage、document、calendar event、transaction note、issue comment。 |
| Tool or skill metadata | Malicious tool description、poisoned skill instruction、routing metadata。 |
| User request | malicious-user request 或 policy-ceiling violation。 |
| Agent rationale | proxy Thought 或 source-span laundering，用来合理化 unauthorized action。 |

用户可以是 benign，也可以是 malicious，取决于具体 slice。主 IPI setting 假设
用户 benign，攻击者控制 external source。

## 数据策略

### 数据来源

优先使用现有 benchmark trajectories：

- ToolSafe / TS-Bench / TS-Guard artifacts；
- AgentDojo workspace trajectories；
- PAIR source-span 和 proxy Thought artifacts；
- ASB / harmful-user 或 policy-ceiling examples；
- 可用时加入 AdaptiveAttackAgent-style 或其他 adaptive tool-use attack traces。

### 多标签派生

初始标签应来自：

- benchmark attack taxonomy；
- 已知 attack source 或 tool family；
- action class 和 side-effect status；
- argument value provenance；
- 新 adaptive sample 的 generated attack mode；
- 只对 ambiguous sample 使用 adjudication。

不要依赖 detector 自己来决定训练标签。

### Detector-specific splits

对 detector `b` 构造：

```text
positive_b = {x | violation_b(x) = yes}
negative_b = {x | violation_b(x) = no}
           = clean
             + other-boundary unsafe
             + near-boundary clean
```

因此，每个 unsafe sample 可以是：

- 某一个 detector 的正例；
- 多个 detector 的正例；
- 对未违反的 detector 来说是负例。

## 模型与训练

部署目标仍然是从 TS-Guard 或兼容 local checkpoint 初始化的本地 7B-style guard。

训练选项：

- 每个 detector 一个 LoRA/QLoRA adapter；
- 如果组合成本过高，可以使用 shared base + separate detector heads/adapters。

detector 输出 compact JSON：

```json
{
  "authority_violation": "yes|no",
  "reasoning": "..."
}
```

value / policy detector 分别输出对应的 `value_violation` 或 `policy_violation`。

OR aggregator 是 detector 外部的确定性规则：

```text
block = authority_violation or value_violation or policy_violation
```

detector `b` 的训练目标：

```text
L_b = CE(y_b, f_b(x)) + beta * L_replay_b + gamma * L_specificity_b
```

其中：

- `CE` 训练 boundary violation label；
- `L_replay_b` 保留已有 hard cases 和 clean utility；
- `L_specificity_b` 强调 cross-boundary negatives，防止 detector 对 unrelated unsafe
  samples fire。

## 评估

评估必须区分 detector quality 和 aggregated guard quality。

Detector-level metrics：

- violation precision；
- violation recall；
- clean false-fire rate；
- cross-boundary false-fire rate。

OR-level metrics：

- clean allow；
- unsafe block；
- authority-slice block；
- value-slice block；
- policy-slice block；
- multi-boundary unsafe block。

数据隔离：

- training/mining pool：可以用于 replay；
- diagnostic dev / attack-dev：可以用于 attribution 和模型选择；
- held-out test：只用于最终报告和 regression gate，不能作为 replay 来源。

## 当前可以 claim 的内容

已经有证据支持：

- mixed single-adapter training 在 value / authority / policy 上概念和实证都不稳定，
  因为不同 boundary 的标签会冲突；
- authority boundary 可以被 local adapter 学到，并能迁移到针对 TS-Guard 生成的
  held-out PAIR artifacts；
- value boundary 在压缩为 protected value presence + user authorization 后更稳，
  但 contaminated delegation 仍是主要 hard failure；
- 下一版方法应是 per-boundary violation detection + OR decision，而不是多个完整
  `ALLOW/BLOCK` adapter。

尚未支持：

- 完全自动化的 continual learning loop；
- 对直接攻击新 detector 的 adaptive robustness；
- 最终 policy detector 设计；
- 对所有 tool-use guard baseline 的 SOTA claim。

## 下一步实验

1. **把 value adapter 改成纯 detector**

   导出新 value 数据：

   ```json
   {
     "value_violation": "yes|no",
     "reasoning": "..."
   }
   ```

   加入 cross-boundary negatives：authority-only unsafe、policy-only unsafe、
   clean delegated-value positives。

2. **构建 multi-label boundary manifest**

   每条 trajectory 存：

   ```json
   {
     "authority_violation": "yes|no",
     "value_violation": "yes|no",
     "policy_violation": "yes|no",
     "source": "...",
     "label_derivation": "benchmark_taxonomy|attack_mode|rule|adjudicated"
   }
   ```

3. **实现 OR aggregation evaluator**

   分别读取 authority / value / policy detector 输出，再用 OR 聚合，报告
   detector-level 和 OR-level metrics。

4. **实现第一版 replay miner**

   先从 value contaminated delegation 开始：

   - AgentDojo meeting-notes email cascade；
   - unauthorized exfiltration cleanup via email id deletion；
   - security-code forwarding；
   - paired clean delegated-retrieval positives。

5. **二阶 adaptive evaluation**

   直接攻击训练后的 authority / value detector，而不是只复用 TS-Guard 或旧 artifact。

## 主指标

主指标是固定 held-out evaluation 上 OR-level safety / utility tradeoff：

```text
primary = unsafe_block_OR at clean_allow_OR >= target threshold
```

初始 gate 建议：

- clean allow OR 相对同一 clean split 上最强 single-boundary baseline 下降不超过 2 个百分点；
- target-boundary unsafe block 在 replay 后提升；
- unrelated boundary slices 不出现实质退化。

## 关联讨论

当前 active discussion：

- `Discussion.md` Thread #10：
  `Boundary-specific adapters 与 value adapter protected-value 结果`

## Changelog

- 2026-06-14：覆盖旧的 five-factor single-guard idea，改为当前
  per-boundary violation detector 设计。新版使用固定 authority / value / policy
  boundary、多标签 trajectory annotation、detector-specific cross-boundary negatives、
  eval-attributed hard replay，以及 OR aggregation 作为最终决策规则。
