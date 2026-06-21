# 使用案例

> 统一前提：**代码全部由 Claude 自己写并自测**，Codex 只做独立终审（read-only，只审不改）。

## 案例 1：新增功能

**场景**：实现一组用户管理 REST API。

**流程**：
1. Claude 拆解需求，列出接口清单与影响文件。
2. Claude 直接写代码并自测（本地跑通 / 跑测试）。
3. 完成这一可独立验证的单元后，取 `git diff` 送 Codex 审查。
4. 按 Codex 清单逐条修复，复用同一会话复审，直至 ✅ PASS。

**Codex 调用示例**：
```
PROMPT: 请 review 以下用户管理 API 的改动（只审不改）。

**改动文件**：src/api/users.py, src/api/schemas.py
**改动目的**：新增 GET/POST /users、GET /users/{id}

**Git Diff**:
```diff
<粘贴 git diff --no-color 输出>
```

**重点检查**：逻辑正确性、边界条件（空值/越界/非法输入）、安全（越权/注入）、测试缺口。
无问题请明确回复"通过"。

cd: /project
sandbox: read-only
SESSION_ID: ""   # 新会话
```

---

## 案例 2：Bug 修复

**场景**：登录 token 过期后未刷新。

**流程**：
1. Claude 定位根因，写修复并补充回归测试，自测通过。
2. 送 Codex 审查修复是否到位、有无引入新问题。
3. ❌/⚠️ → 逐条修复 → 复审；同一问题最多 2 轮往返，仍卡住则抛人工裁决。

**Codex 调用示例**：
```
PROMPT: 请 review 登录 token 刷新的修复（只审不改）。

**改动文件**：src/auth/login.py, tests/test_login.py
**改动目的**：修复 token 过期未刷新；补充过期场景回归测试

**Git Diff**:
```diff
<粘贴 git diff 输出>
```

**重点检查**：刷新逻辑边界（并发刷新、刷新失败回退）、安全（凭证泄漏）、测试断言是否有效。

cd: /project
sandbox: read-only
SESSION_ID: "abc-123"   # 复用上一轮初审会话，保留上下文
```

---

## 案例 3：关键模块强制送审

**场景**：改动涉及支付写入 —— 属于铁律里的强制送审范围（鉴权/支付/数据写入/对外接口/并发）。

**要点**：
- 即使改动很小，也**必须**送 Codex 审查，不得 Claude 自我放行。
- 在 PROMPT 中明确标注高风险面，请 Codex 重点核查不可逆 / 对外可见行为。
- 必须复审到 ✅ PASS 才合入。
