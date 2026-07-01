# Active Defense for AI Agents

## One-Sentence Summary

在 agent 可见的 affordance 空间里主动埋入诱饵,用 commitment-touch 作为
policy-free 检测信号;鲁棒性的唯一来源是**不可避免性**——把诱饵放在攻击绕不开
的地方:PLANT(不可区分的 must-take 诱饵,outcome 检测)与 WRAP(不可避免的能力
咽喉中介)。核心结论:在开放 agentic 基座下,deception(PLANT)> instrumentation
(WRAP-in-band 可被读穿绕开);WRAP 的强声称需 effectful harm ∧ 基座强制中介 ∧
有界 affordance 面三前提(详见 `Formal.md` 命题 W)。

> 注:本 summary 已于 2026-W26 按实验结论从"placement optimization 控制 TPR/FP
> 权衡"改写(旧优化器叙事被证 no-op)。待用户确认。

## Angus Decision · 2026-06-24

本方向确认为当前主线。`adapter_defense` 中的 per-boundary detector /
adapter 结果保留为备用路线、相关工作或后续组合模块,但当前论文主叙事转向
`active_defense`。

近期优先级是补主动防御的误报指标。主动防御本身会向环境注入 affordance,
因此误报不只是普通分类错误,还可能表现为防御诱导 agent 在无攻击时多次越界。
后续实验必须优先报告 benign/control 下的 `I(M)`、safe-control `I(M)`、raw
control touch,以及多次运行下的越界稳定性。

AgentShield 对比主战场确定为 SCR,不是 AgentDojo 原环境。AgentDojo/deepseek
上 ASR 太低,主动诱饵触发事件太少,更适合作为解释 AgentShield 条件口径与固定
诱饵局限的诊断附表。主表应放在 SCR-CapFlow / SCR-AuthBlur / 后续可攻破的
SCR-TrustLift 上,即有组合授权攻击且 ASR>0 的同考点环境。

## Core Claim

现有 AgentShield 式固定 trap 在组合授权攻击中会结构性漏报:攻击可用合法工具/
合法对象/二元授权输出完成危害,不必触碰固定 honeytool/honeytoken/可 allowlist 参数。
本方法的增量是**把诱饵放在攻击绕不开的元素上(不可避免性)**,并用 policy-free 的
commitment-touch 检测:

- 族 1 PLANT(对象端): 不可区分的 must-take 诱饵(certify-gate 认证),混入对手必须
  处理的敏感对象集 → 排除不掉;检测是 **outcome-based**(诱饵 id 必现于对手产生的
  效果状态),**对开放执行环境鲁棒**(不依赖对手运行我方代码)。
- 族 2 WRAP(边界端): 不可避免的能力咽喉中介(cut-set 全覆盖);抗自适应**需三前提**
  W1 effectful harm ∧ W2 基座强制中介 ∧ W3 有界面(`Formal.md` 命题 W)。
- 主结论: **开放 agentic 基座下 deception(PLANT)> instrumentation(WRAP-in-band 可被
  读穿绕开)**。两族共用 commitment-touch 检测器 + 近零误报(命题 1);**不再依赖
  子模/placement 优化(已证 no-op)**。

## Primary Metrics

- `I(M)`: benign/control run 中触碰任一 marker 的比例。主动防御主指标之一。
- safe-control `I(M)`: control 中 agent 没有输出 unsafe approval / real unsafe
  action 时的 marker touch。用于区分模型本身 unsafe 与防御误报。
- raw control touch: 所有 control run 中 marker touch。用于暴露防御是否诱导无攻击
  越界。
- `TPR`: attack run 中 marker touch 的比例。
- `dgs`: detected given success,攻击真正成功时被 marker 捕获的比例。
- `ASR` 与 `ASR_undetected`: 区分攻击未发生、攻击被扰乱和攻击成功但未检出。

## Immediate Experimental Priorities（2026-W26 重定向后）

1. **PLANT 抗开放-shell 对手(承重)**: 完成 EXP-005 修复版重跑——同一知情对手下
   不可区分 certified 诱饵 vs 尖叫诱饵的 outcome 检出;若不可区分显著更高,主结论
   "deception > instrumentation" 在真实威胁模型上闭合。落地 gap 2(capflow 改用 certify-gate)。
2. **WRAP 承重验证迁到有界基座**: MCP / AgentDojo function-call(基座强制拦截 tool call、
   agent 无裸 shell),复现 probe 的 0% 逃逸;AuthBlur(speech-act)/ CapFlow-CLI(open shell)
   显式列为弱例。
3. **SCR 为 AgentShield 主对比环境**: 组合授权攻击且 ASR>0;AgentDojo 仅作低-ASR 诊断附表。
4. **威胁模型形式化定稿**: `Formal.md` 命题 W 三前提 + 主结论(待用户拍板,§9/§10)。

## Current Evidence（2026-W26 重定向后）

- **近零误报(命题 1)**: AuthBlur 完整框架 `I(M)=0.000`(EXP-2026W26-001)。
- **WRAP 威胁模型(命题 W)**: 能力中介对知情对手 `0% 逃逸`,纯文本决策 `90% 逃逸`(EXP-003)。
- **WRAP-in-band 在开放 shell 被绕(强负结果)**: CapFlow-over-CLI 知情对手 `caught|acted=27%`
  (73% 绕过,读穿明文 telemetry),违反前提 W2/W3(EXP-004)。
- **PLANT 抗同一对手**: 同一知情开放-shell 对手下不可区分诱饵 vs 尖叫诱饵的 outcome 检出对比
  (EXP-005,**首轮因 outcome 检测器 bug inconclusive,修复后重跑中**)。
- **AgentShield-on-SCR(归档 thread,仍有效)**: 组合授权攻击且 ASR>0 时 AgentShield 三层 `TPR=0`。
- ⚠ 旧 lure_radius MCTS 证据(`dgs=1.00` 等)属已废弃的优化器叙事,移除。
