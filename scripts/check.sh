#!/usr/bin/env bash
# 本地检查脚本（替代 CI）：提交前本地跑一遍 import / 测试 / 构建。
# 用法：./scripts/check.sh
set -euo pipefail

cd "$(dirname "$0")/.."

echo "== [1/3] import 健全性 =="
uv run python -c "import cc_mcp.server; print('  OK:', cc_mcp.server.mcp.name)"

echo "== [2/3] 单元测试 =="
uv run python -m unittest discover -s tests

echo "== [3/3] 构建 =="
uv build >/dev/null && echo "  build OK"

echo
echo "✅ 本地检查全部通过"
echo "（lint / 类型检查未配置；如需可加 ruff / mypy 到本脚本）"
