---
name: ccg-workflow
description: |
  CCG (Coder-Codex-Gemini) collaboration for code and document tasks.
  Use when: writing/modifying code, editing documents, implementing features, fixing bugs, refactoring, or code review.
  协调 Coder 执行代码/文档改动，Codex 审核代码质量。
---

# CCG 工作流协作流程

## 角色分工

- **Claude**：项目规划者 + 快检者 + 最终决策者（**禁止直接修改或改动代码/文档**）
- **Coder**：项目执行者（代码/文档改动）
- **Codex**：项目审核者 + 高级代码顾问（**每次 Coder 完成后必须审核**）
- **Gemini**：高阶顾问（按需） → 详见 `/gemini-collaboration`

## 任务拆分原则（分发给 Coder）

> ⚠️ **一次调用，一个目标**。禁止向 Coder 堆砌多个不相关需求。

- **精准 Prompt**：目标明确、上下文充分、验收标准清晰
- **按模块拆分**：相关改动可合并，独立模块分开
- **每模块必审**：每模块完成 Claude 快检后，必须调用 Codex 审核通过才能继续

## 核心流程（四步闭环）

### 1. Claude 规划

分析需求、拆分任务、准备精准 Prompt。

调用前（复杂任务推荐）：
- 搜索受影响的文件/符号
- 在 PROMPT 中列出修改清单
- **复杂问题可先与 Codex 沟通**：架构设计或复杂方案可先咨询后再委托 Coder 执行

### 2. Coder 执行

所有代码、文档等内容改动或修改任务，**直接委托 Coder 执行**。

### 3. Claude 快检

Coder 执行完毕后，Claude 快速读取验收：
- **无误** → 继续下一步（调用 Codex 审核）
- **有误** → 委托 Coder 修复（**严禁禁止 Claude 自行写代码,无论简单与否都禁止 Claude 自行写代码**）

### 4. Codex 审核

每次 Coder 执行完成并通过 Claude 快检后，**必须调用 Codex 审核**：
- 检查代码质量、潜在 Bug
- 结论：✅ 通过 / ⚠️ 优化 / ❌ 修改

**审核结果处理**：

- ✅ 通过 → 继续下一步任务
- ⚠️/❌ 有问题 → 委托 Coder 修复 → 再次审核 → 循环直至项目测试通过

## 工具参考

| 工具 | 用途 | sandbox | 重试 |
|------|------|---------|------|
| Coder | 执行文件改动 | workspace-write | 默认不重试 |
| Codex | 代码文件审核或审查 | read-only | 默认 1 次 |
| Gemini | 顾问/执行 | workspace-write (yolo) | 默认 1 次 |

> 💡 **Gemini 详细指南**：如需了解 Gemini 的具体调用方式和触发场景，请执行 `/gemini-collaboration` 技能。

**会话复用**：保存 `SESSION_ID` 保持上下文。

## 独立决策

Coder/Codex/Gemini 的意见仅供参考。你（Claude）是最终决策者，需批判性思考，做出最优决策。

详细和参考参数：[coder-guide.md](coder-guide.md) | [codex-guide.md](codex-guide.md)|[examples.md](examples.md)

推荐约束提示词：[constraint.md](constraint.md)
