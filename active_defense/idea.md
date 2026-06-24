# Active Defense for AI Agents

## One-Sentence Summary

在 agent 可见的 affordance 空间里主动埋入 off-benign-path 诱饵,用
commitment-touch 作为 policy-free 检测信号,统一覆盖 objective-level
honeypot 与 boundary-level honeypot,并用 placement optimization 控制
检测率与误报率的权衡。

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

现有 AgentShield 式固定 trap 在组合授权攻击中会结构性漏报:攻击可以使用合法
工具、合法对象或二元授权输出来完成危害,不必触碰固定 honeytool、固定
honeytoken 或可 allowlist 的参数。本方法的增量是把诱饵放置从固定 trap 改为
沿 objective→boundary 连续谱进行优化:

- 族 1 objective-level honeypot: 把假目标、假凭证、假记录放在攻击想选用或外发
  的对象槽位上;良性任务不应提交性使用这些假对象。
- 族 2 boundary-level honeypot: 把无副作用的诱饵动作放在 skill/tool/MCP capability
  的职责边界外侧;被授权洗白的 agent 一旦跨边界提交动作即触发。
- 两族共用 commitment-touch 检测器、近零误报命题、子模覆盖/placement 优化和
  规避成本下界。

## Primary Metrics

- `I(M)`: benign/control run 中触碰任一 marker 的比例。主动防御主指标之一。
- safe-control `I(M)`: control 中 agent 没有输出 unsafe approval / real unsafe
  action 时的 marker touch。用于区分模型本身 unsafe 与防御误报。
- raw control touch: 所有 control run 中 marker touch。用于暴露防御是否诱导无攻击
  越界。
- `TPR`: attack run 中 marker touch 的比例。
- `dgs`: detected given success,攻击真正成功时被 marker 捕获的比例。
- `ASR` 与 `ASR_undetected`: 区分攻击未发生、攻击被扰乱和攻击成功但未检出。

## Immediate Experimental Priorities

1. 补 SCR-AuthBlur family-2 boundary honeypot 的重复评估: `repeats>=2`,扩大 case,
   报告 raw-control / safe-control / `I(M)` / `dgs`。
2. 把 family-2 placement 的半径搜索从小样本 smoke test 扩成可画前沿的实验:
   `TPR-I(M)`、`dgs-I(M)`、ASR disruption 前沿。
3. 固定 SCR 为 AgentShield 主对比环境: CapFlow 与 AuthBlur 作为当前主证据,
   TrustLift 只有在先把 ASR 抬到 `>0` 后才纳入主表。
4. 将 AgentShield 在 AgentDojo 的结果写成诊断:低 ASR、条件检测口径、honeytoken
   几乎不触发、固定主动诱饵缺少统计信号。

## Current Evidence

- SCR-CapFlow: 族 1 固定诱饵约 `TPR=0.727 / I(M)=0`;MCTS 最优
  `target|4|tail` 达到 `dgs=1.00 / TPR=0.818 / I(M)=0`。
- SCR-AuthBlur: 族 2 MCTS 搜出
  `reviewer=4, reviewer-plain=4, approver=2`,达到
  `dgs=0.75 / I(M)=0 / ASR=1.0`。
- AgentShield-on-SCR: CapFlow `TPR=0` vs ours `0.727`;AuthBlur `TPR=0`
  vs ours `0.75`;TrustLift 因当前模型 ASR=0 暂不作主证据。
