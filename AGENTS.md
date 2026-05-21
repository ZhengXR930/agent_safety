# Agent-Centric Research Protocol

> 本文件是协议的 **single source of truth**。`CLAUDE.md` 仅是指向本文件的引用。

---

## 0. 核心哲学（必须保留）

- **Agent First**：除高阶科学决策外，重复执行任务由 Agent 主导。
- **Everything is Markdown**：研究过程即文档，关键状态必须落盘到 Markdown。
- **Vibe Alignment**：用户给意图与方向，Agent 负责把意图转成实现与实验。
- **Math-Guided Improvement**：优先让数学指导方法改进；至少要能数学描述与解释。

---

## 1. 核心锚点文件

- `idea.md`：研究问题、动机、目标、实验大图。
- `method.md`：方法的数学形式化（损失、假设、推论/定理、解释）+ 变更日志。
- `Discussion.md`：**当前唯一 active 议题**（多人协作主战场，一议题一主线）。
- `Discussion/Archive/`：已关闭议题归档（每议题一个 md）。
- `LOGS/`：按周记录实验结果（每周一个 `YYYY-Www.md`）。
- `MODE.md`：当前协作模式（newbie/expert）及策略。
- `code/`：项目主代码目录。
- `baseline/`：Baseline 代码目录（可不存在）。
- `ref/`：论文/资料/笔记（默认不主动扫描；被显式引用时必读，详见 § 8）。
- `tools/`：协议辅助脚本（新建周志、新建实验块、占位符 lint）。

---

## 2. 首次初始化（bootstrap 机制）

1. 若仓库存在 `bootstrap.md`，优先执行初始化向导。
2. 用户在向导中**仅回复 `A` 或 `B`** 选择模式：A=newbie，B=expert。
3. Agent 将选择结果写入 `MODE.md`（`mode / updated_at / set_by`）。
4. 完成初始化后删除 `bootstrap.md`。
5. 删除后，后续策略以 `MODE.md` 为准。

### 2.1 跨 Agent 兼容触发规则

- 若当前 Agent 不支持 `.claude` 目录下的 hooks（如 Codex / Cursor），必须手动执行与 `SessionStart` hook 等价的初始化检查：
  - 进入仓库后的第一条有效回复前，先检查 `bootstrap.md` 是否存在。
  - 若存在：不进入普通问答，立即输出初始化引导，并要求用户**仅回复 A 或 B**。
  - 引导内容须与 `.claude/settings.json` 中 `SessionStart` hook 输出等价。
  - 用户完成模式选择前，不得跳过初始化直接进入 P-E-R 循环。
- 若 `bootstrap.md` 不存在且 `MODE.md` 的 `mode ∈ {newbie, expert}`，按正常流程继续。

### 2.2 模式状态判定（消歧）

| `bootstrap.md` | `MODE.md::mode` | 行为 |
|---|---|---|
| 存在 | 任意 | **未初始化**，必须先走 bootstrap |
| 不存在 | `newbie` 或 `expert` | 按该模式正常工作 |
| 不存在 | `unset` 或缺失 | 视为协议异常，提示用户从模板重建 `bootstrap.md` |

---

## 3. 模式策略（由 MODE.md 驱动）

### 3.1 科研新手模式（newbie）
- 交互：一步一引导，不一次抛太多选项。
- 执行：默认给出最小下一步（single next action）。
- 文档：每完成一步同步写入对应文件。
- 实验：先做小规模验证（Pilot），再扩展。

### 3.2 科研老手模式（expert）
- 交互：结论先行，少解释，多直接执行。
- 执行：以任务批次推进，减少确认轮次。
- 文档：只保留关键变更与结论，避免冗长。
- 实验：直接进入主实验/消融，不强制教学式拆解。

---

## 4. 日常工作循环（P-E-R）

### 4.1 三步循环

1. **Plan**：读取 `MODE.md` + `idea.md` + `Discussion.md`，明确当前唯一问题。
2. **Execute**：修改 `code/`（或 `baseline/` 对照），必要时更新 `method.md`。
3. **Reflect**：在当周 `LOGS/YYYY-Www.md` 追加实验块，并回写 `Discussion.md` 共识。

### 4.2 前置 / 后置检查

| 阶段 | 必须先做 / 必须后做 |
|---|---|
| **Plan 前置** | 若 `Discussion.md` 无 active 议题，先与用户对齐一个并按 § 7 创建；若 `idea.md` 关键字段（One-Sentence Summary / Primary Metric）为空，先填这两项再继续。 |
| **Execute 后置** | 若 `code/` 非空且存在测试入口，运行一次 lint + 单测；任何 method 公式/假设的实质改动必须同步进 `method.md` 并写入其 Changelog（§ 9）。 |
| **Reflect 后置** | 当周 `LOGS/YYYY-Www.md` 至少追加一条完整 EXP 块（按 § 5 字段全填）；若该实验影响当前议题结论，必须在 `Discussion.md` 该议题下回帖。 |

---

## 5. LOGS 约定（周维度）

### 5.1 命名 & 组织
- `LOGS/` 每周一个文件：`YYYY-Www.md`（例：`2026-W10.md`）。
- 同一周所有实验追加在该文件。
- 实验 ID 统一格式：**`EXP-YYYYWww-NNN`**（例：`EXP-2026W10-001`，三位序号）。

### 5.2 每条 EXP 块必填字段

```
### EXP-YYYYWww-NNN

- 源意图 (Original Vibe):
- 假设 (Hypothesis):
- 是否被驳斥 (Falsified?):      Y / N / 部分
- 驳斥/支持原因 (Why):
- Agent 动作 (What changed):
- 复现信息 (Repro):
  - commit:                   <git sha 或 dirty>
  - seed:                     <int 或 N/A>
  - dataset / version:
  - env:                      <python/cuda/key libs>
  - hardware:                 <GPU/CPU>
  - command:                  `bash ...`
- 关键指标 (Metrics):
- 日志路径 (Artifacts):       <wandb / 文件路径>
- 结论 (Conclusion, 1–3 句):
- 下一步 (Next):
- 关联议题 (Discussion):       DISC-YYYYWww-NNN
```

**负结果原则**：`Falsified=Y` 的实验同样需要完整记录，**不允许悄悄删除或重命名**。负结果与正结果同等重要。

---

## 6. 周回顾（Weekly Retro）

- **触发**：每周首次会话开始时，Agent 主动执行。
- **动作**：
  1. 扫描上一周 `LOGS/YYYY-W(N-1).md` 所有 EXP；
  2. 按 `Falsified=Y / N / 部分` 分组汇总；
  3. 在 `Discussion.md` 当前 active 议题底部追加一条 `【Agent】【日期】Weekly Retro:` 回帖，列出 (a) 已驳斥假设 (b) 已支持假设 (c) 悬而未决问题；
  4. 若发现与 `idea.md` / `method.md` 的冲突，必须在 retro 里明确指出并建议对齐方案。

---

## 7. Discussion.md 多人协作约定（主战场）

详细模板见 `Discussion.md` 本身，此处仅规定不变量：

- **一议题一主线**：根目录 `Discussion.md` 同一时刻只承载 **1 个 active 议题**。
- **议题号**：`DISC-YYYYWww-NNN`，可被 LOGS / method.md / idea.md 反向引用。
- **状态机**：`Open → Resolved`。无 `Decision` 段不得关闭。
- **角色化发言**：`【PI|Lead|Collab|Agent @名字】【YYYY-MM-DD HH:MM】`。
- **Agent 发言必带硬证据**：链接到 `LOGS/...#EXP-...` 并贴关键数字。
- **关闭流程**：议题关闭时整体移动到 `Discussion/Archive/YYYY-MM-DD-<slug>.md`，根目录 `Discussion.md` 用空白模板重置或立刻承载下一个议题。
- **结论反哺**：议题 `Decision` 必须在 `Resolution.Propagated to` 字段列出反写到 `method.md §` / `idea.md §` / 哪些 `EXP-...`。

---

## 8. ref/ 使用规则

- 默认 **不主动扫描** `ref/`，避免污染上下文。
- **强制读取条件**：当 `idea.md` / `method.md` / `Discussion.md` 中出现 `ref/<path>` 形式的显式引用，Agent 必须读取被引用文件并在下一次发言里反映其内容。
- 用户口头要求时同样必须读。

---

## 9. 决策边界：高阶 vs Agent 自治

| 类别 | 例子 | 谁拍板 |
|---|---|---|
| 修改 loss / 正则形式 | 加入 $\beta\|\nabla f\|^2$ | **用户** |
| 修改假设 / 定理陈述 | 改写 `method.md` § 2 / § 3 | **用户** |
| 引入新 baseline / 新数据集 | 加 NCFM-v2、换 ImageNet→CIFAR | **用户** |
| 改 `idea.md` 研究目标 | 改 Objective 1 | **用户** |
| 关闭 / 开启 Discussion 议题 | 任意 DISC-* | **用户**（Agent 可起草 Decision 草稿） |
| 调超参 / lr / batch / 网格搜索 | 任意 sweep | Agent |
| 跑现有 baseline / 复现 | 复现 NCFM | Agent |
| 数据预处理脚本 | tokenizer、resize | Agent |
| 写 / 修单元测试 | `tests/*` | Agent |
| 整理日志、补 EXP 字段 | 任意 LOGS 编辑 | Agent |
| 起草 `method.md` Changelog 条目 | 待用户审核 | Agent |

---

## 10. Stop / Escalate 触发条件

满足任一条件时，Agent **必须停下来征求用户**，不得自行继续：

- 任一实验连续 3 次跑崩 / 不收敛。
- 与目标 SOTA 的关键指标差距超过用户在 `idea.md` 设定的阈值（若未设，按 ≥10% 触发）。
- 需要修改 `method.md § 2 形式化定义` 或 § 3 关键结论。
- 需要修改 `idea.md` § 2.3 研究目标 或 § 4.3 主指标。
- 单次实验预估开销超过当前预算（用户未设预算时，按"单跑 >2h GPU 或 >5GB 写盘"触发）。
- 涉及"删除已有 EXP 记录"或"重写已 Resolved 议题结论"。

---

## 11. 质量与边界

- 涉及定理/推导/SOTA 对比：给出处或推导过程，避免幻觉。
- 若 `idea.md`、`method.md`、`LOGS` 结论冲突：先指出冲突，再建议对齐方案。
- 默认不读取 `ref/`，除非 § 8 条件触发。
