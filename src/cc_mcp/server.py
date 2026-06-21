"""CC-MCP 服务器主体

提供唯一的 codex 工具：调用 Codex 进行独立代码审查（只审不改）。
Claude 负责写代码与自测，Codex 作为终审闸口。
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated, Any, Dict, List, Literal, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from cc_mcp.tools.codex import codex_tool

# 创建 MCP 服务器实例
mcp = FastMCP("CC-MCP Server")


@mcp.tool(
    name="codex",
    description="调用 Codex 进行独立代码审查，给出 ✅PASS/⚠️OPTIMIZE/❌CHANGE 结论。只审不改，默认 sandbox: read-only。",
)
async def codex(
    PROMPT: Annotated[str, "审核任务描述"],
    cd: Annotated[Path, "工作目录"],
    sandbox: Annotated[
        Literal["read-only", "workspace-write", "danger-full-access"],
        Field(description="沙箱策略"),
    ] = "read-only",
    SESSION_ID: Annotated[str, "会话 ID"] = "",
    skip_git_repo_check: Annotated[
        bool,
        "允许非 Git 仓库",
    ] = True,
    return_all_messages: Annotated[bool, "返回完整消息"] = False,
    return_metrics: Annotated[bool, "返回指标数据"] = False,
    image: Annotated[
        Optional[List[Path]],
        Field(description="附加图片路径"),
    ] = None,
    model: Annotated[
        str,
        Field(description="指定模型"),
    ] = "",
    yolo: Annotated[
        bool,
        Field(description="跳过沙箱审批（慎用）"),
    ] = False,
    profile: Annotated[
        str,
        "配置文件名称",
    ] = "",
    timeout: Annotated[int, "空闲超时秒数"] = 300,
    max_duration: Annotated[int, "总时长上限秒数，0=无限"] = 1800,
    max_retries: Annotated[int, "最大重试次数"] = 1,
    log_metrics: Annotated[bool, "输出指标到 stderr"] = False,
) -> Dict[str, Any]:
    """执行 Codex 代码审核

    codex_tool 内部是同步阻塞实现（子进程流式读取 + 重试退避 sleep），
    通过 asyncio.to_thread 放到工作线程执行，避免阻塞 FastMCP 事件循环
    （否则一次数分钟的审查会让 stdio 传输层在整段时间内无响应）。
    """
    return await asyncio.to_thread(
        codex_tool,
        PROMPT=PROMPT,
        cd=cd,
        sandbox=sandbox,
        SESSION_ID=SESSION_ID,
        skip_git_repo_check=skip_git_repo_check,
        return_all_messages=return_all_messages,
        return_metrics=return_metrics,
        image=image,
        model=model,
        yolo=yolo,
        profile=profile,
        timeout=timeout,
        max_duration=max_duration,
        max_retries=max_retries,
        log_metrics=log_metrics,
    )


def run() -> None:
    """启动 MCP 服务器"""
    mcp.run(transport="stdio")
