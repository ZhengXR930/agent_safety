# tools/ · 协议辅助脚本

零依赖，纯 Python 3.9+。

| 脚本 | 作用 | 用法 |
|---|---|---|
| `new_week.py` | 新建当周 `LOGS/YYYY-Www.md`（已存在则跳过） | `python tools/new_week.py` 或 `python tools/new_week.py 2026-W11` |
| `new_exp.py` | 往当周 LOGS 追加一个 EXP 骨架（自动算 NNN / 填 commit hash / 主机名） | `python tools/new_exp.py "源意图一句话"` |
| `lint_protocol.py` | 扫描所有 Markdown，报告未填占位符 / 错误 EXP-ID / Resolved 议题缺 Decision | `python tools/lint_protocol.py` 或 `python tools/lint_protocol.py LOGS/` |
| `install_hooks.sh` | 把 git 指向 `.githooks/`，启用 pre-commit 自动 lint（每个新 clone 跑一次即可） | `bash tools/install_hooks.sh` |

## pre-commit 行为

装上后每次 `git commit` 会自动跑 `lint_protocol.py`：
- 0 退出 → commit 正常进行
- 非 0 退出 → commit 被中止，必须先修复占位符 / EXP-ID / 议题 Decision
- 紧急绕过：`git commit --no-verify`（不推荐）

## 设计原则

- **零依赖**：只用标准库，避免污染科研项目自身的环境。
- **不破坏现有文件**：`new_week.py` 已存在则跳过；`new_exp.py` 只追加不重写。
- **可被 Agent 直接调用**：所有脚本以非零退出码报错，便于 Agent 检测。
