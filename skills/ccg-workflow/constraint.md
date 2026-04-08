# 任何项目都务必遵守的规则

---

## Communication
* 优先使用 ccg-workflow 工具进行协作与任务流转
* 所有关键操作必须具备可追溯记录（SESSION_ID / 变更记录）
### Failover（必须具备）
当 ccg-workflow 不可用：
* 使用 Git + Markdown 记录过程
* 在 docs/ 或 discuss/ 中补充记录
* 后续补同步
---
## Documentation
* 编写 .md 文档必须使用中文说明（必要时可附英文）
* 正式文档统一存放在 docs/ 目录
* 讨论 / 方案 / 草稿统一存放在 discuss/ 目录
### 文档结构要求（必须）
* Context（背景）
* Goal（目标）
* Solution（方案）
* Risk（风险）
### 生命周期（必须）
* discuss/ 内容超过30天：
  * 删除 或
  * 归档到 docs/history/
---
## Code Architecture
### 硬性指标（必须）
（1）动态语言（Python / JS / TS）单文件 ≤ 300 行（例外需说明）
（2）静态语言（Java / Go / Rust）单文件 ≤ 400 行（例外需说明）
（3）单层目录文件建议 ≤ 8 个，超出需模块拆分（非强制）
### 架构原则（必须）
* 禁止循环依赖（Circular Dependency）
* 禁止吞异常
* 必须可测试（Testable）
### Code Smell（强制触发机制）
发现以下问题必须中断并确认：
* 僵化（Rigidity）
* 冗余（Redundancy）
* 循环依赖（Circular Dependency）
* 脆弱性（Fragility）
* 晦涩性（Obscurity）
* 数据泥团（Data Clump）
* 不必要复杂性（Needless Complexity）
处理流程：
1. 标注问题
2. 给出优化方案
3. 等待用户确认
---
## Run & Debug
* 必须在 scripts/ 目录维护统一 .sh 启停脚本
* 所有生产运行必须通过 scripts/ 执行
### 开发环境（允许）
* 允许直接使用 npm / uv / python 等命令
* 但 scripts 必须保持可用
### 异常处理（必须）
* scripts 执行失败：
  1. 优先修复 scripts
  2. 不允许长期绕过
### 日志（必须）
* 所有项目必须配置 Logger（文件输出）
* 输出目录：logs/
* 日志级别：INFO / WARN / ERROR
---
## Git（新增必须模块）
### 分支策略
* main：生产
* dev：开发主线
* feature/*：功能开发
* fix/*：修复
### Commit 规范
* feat: 新功能
* fix: 修复
* refactor: 重构
* docs: 文档
### 合并规则（必须）
* 必须通过 PR
* 必须 Code Review
---
## CI/CD（必须）
每次提交必须通过：
* Lint
* Type Check
* Test
* Build
---

## Security（必须）
* 禁止提交：
  * API Key
  * Token
  * 密码
* 必须使用：
  * .env
  * .env.example
### 推荐
* 最小权限原则
* 日志脱敏
---
## Python
* 虚拟环境统一使用 .venv
* 数据结构必须强类型（dataclass / pydantic）
### 推荐
* 优先使用 uv
* fallback 允许 pip
---
## React / Next.js / TypeScript / JavaScript
* 强制使用 TypeScript（除非构建工具不支持）
* 严禁使用 CommonJS
### 必须通过
* tsc --noEmit
* eslint
### 推荐
* 使用最新稳定版本（避免锁死版本）
## PHP
* 所有文件必须 declare(strict_types=1);
* 禁止使用 mixed（非必要）
* 必须使用 Composer
### 强制
* 必须具备单元测试（PHPUnit）
### 推荐
* DTO / enum / readonly
* 遵循 PSR-1 / PSR-4 / PSR-12
## 项目结构

```
root/
├── docs/
├── discuss/
├── scripts/
├── logs/
├── src/
├── tests/
└── .env.example
```

## 异常处理

* 禁止吞异常
* 必须明确异常类型
* 必须可追踪


## 版本策略

* 使用推荐版本（避免锁死）
* 建议季度升级

## 核心执行原则

```
1. 可运行 > 完美设计
2. 可维护 > 技术炫技
3. 可追溯 > 临时方案
4. 简单优先 > 过度设计
```