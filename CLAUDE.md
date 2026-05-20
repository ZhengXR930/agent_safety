# Agent-Centric Research Protocol

## 0. 核心哲学（必须保留）

- **Agent First**：除高阶科学决策外，重复执行任务由 Agent 主导。
- **Everything is Markdown**：研究过程即文档，关键状态必须落盘到 Markdown。
- **Vibe Alignment**：用户给意图与方向，Agent 负责把意图转成实现与实验。
- **Math-Guided Improvement**：优先让数学指导方法改进；至少要能数学描述与解释。

---

## 1. 核心锚点文件

- `idea.md`：研究问题、动机、目标、实验大图。
- `method.md`：方法的数学形式化（损失、假设、推论/定理、解释）。
- `Discussion.md`：当前问题的轻量发帖式讨论。
- `LOGS/`：按周记录实验结果（每周一个 `YYYY-Www.md`）。
- `MODE.md`：记录当前协作模式（新手/老手）及对应执行策略。
- `code/`：项目主代码目录。
- `baseline/`：Baseline 代码目录（可不存在）。
- `ref/`：论文/资料/笔记（默认不读取，除非用户明确要求）。

---

## 2. 首次初始化（bootstrap 机制）

1. 若仓库存在 `bootstrap.md`，优先执行初始化向导。
2. 用户在向导中选择模式：`newbie` 或 `expert`。
3. Agent 将选择结果写入 `MODE.md`（包括策略说明与更新时间）。
4. 完成初始化后删除 `bootstrap.md`。
5. 删除后，后续策略以 `MODE.md` 为准，不会丢失模式信息。

### 2.1 跨 Agent 兼容触发规则

- 若当前 Agent 不支持 `.claude` 目录下的 hooks，也必须手动执行与 `SessionStart` hook 等价的初始化检查。
- 具体要求：
  - 在进入仓库后的第一条有效回复前，先检查 `bootstrap.md` 是否存在。
  - 若存在 `bootstrap.md`，不要先进入普通问答；应立即向用户输出初始化引导，并要求用户只回复 `A` 或 `B`。
  - 初始化引导内容应与 `.claude/settings.json` 中的 `SessionStart` hook 保持等价：说明协议用途、列出核心文件、要求选择 `newbie` 或 `expert`。
  - 在用户完成模式选择前，不跳过初始化直接进入常规 P-E-R 循环。
  - 若 `MODE.md` 已是有效模式且 `bootstrap.md` 不存在，则按正常流程继续。

---

## 3. 模式策略（由 MODE.md 驱动）

### 3.1 科研新手模式（newbie）

- 交互风格：一步一引导，不一次抛太多选项。
- 执行策略：默认给出最小下一步（single next action）。
- 文档策略：每完成一步就同步写入对应文件，便于用户看到进展。
- 实验策略：先做小规模验证（Pilot），再扩展。

### 3.2 科研老手模式（expert）

- 交互风格：结论先行，少解释，多直接执行。
- 执行策略：以任务批次推进，减少确认轮次。
- 文档策略：只保留关键变更与结论，避免冗长。
- 实验策略：直接进入主实验/消融，不强制教学式拆解。

---

## 4. 日常工作循环（P-E-R）

1. **Plan**：读取 `MODE.md` + `idea.md` + `Discussion.md`，明确当前唯一问题。
2. **Execute**：修改 `code/`（或 `baseline/` 对照），必要时更新 `method.md`。
3. **Reflect**：在当周 `LOGS/YYYY-Www.md` 追加实验块，并回写 `Discussion.md` 共识。

---

## 5. LOGS 约定（周维度）

- `LOGS` 中每周一个文件：`YYYY-Www.md`。
- 同一周所有实验都写进该文件。
- 每条实验记录至少包含：
  - 实验 ID
  - 源意图（Original Vibe）
  - Agent 动作（改了什么）
  - 关键指标
  - 结论与下一步

---

## 6. 质量与边界

- 涉及定理/推导/SOTA 对比：给出处或推导过程，避免幻觉。
- 若 `idea.md`、`method.md`、`LOGS` 结论冲突：先指出冲突，再建议对齐方案。
- 默认不读取 `ref/`，除非用户明确指定材料。
