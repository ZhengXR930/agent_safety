# 科研流程协议 · 当前研究仓库

> 本仓库已合并 `AngusDujw/Angus-Research-Protocol` 新模板，并保留原有研究讨论与 idea 内容。仓库已经初始化完成，因此根目录不保留 `bootstrap.md`，当前模式见 `MODE.md`。

## 当前研究状态

- **当前 idea**：`idea.md`，从 `idea/idea_2026-05-20_authorization-chain-rlvr.md` 导入为新模板根目录锚点。
- **当前 active 议题**：`Discussion.md` / `DISC-2026W21-001`，讨论是否从 Authorization-Chain RLVR 转向“小模型快速本地危险 tool-use guard”。
- **历史兼容副本**：旧版讨论仍保留在 `discussion/Discussion.md`，便于核对迁移前上下文。

## 关键文件

| 文件 | 作用 |
|---|---|
| `AGENTS.md` | 协议正文，single source of truth |
| `MODE.md` | 当前协作模式与策略 |
| `idea.md` | 当前研究问题、动机、目标、实验大图 |
| `method.md` | 方法数学形式化与 Changelog |
| `Discussion.md` | 当前唯一 active 议题 |
| `LOGS/YYYY-Www.md` | 周维度实验/阅读/维护记录 |
| `tools/` | 新建周志、新建 EXP、自检 lint、hook 安装脚本 |

## 常用命令

```bash
python3 tools/lint_protocol.py
python3 tools/new_week.py
python3 tools/new_exp.py "源意图一句话"
bash tools/install_hooks.sh
```

## 模板来源

新协议模板来自：<https://github.com/AngusDujw/Angus-Research-Protocol>
