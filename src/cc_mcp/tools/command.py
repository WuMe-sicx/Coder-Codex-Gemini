"""构建 `codex exec` 命令行 argv

抽成纯函数便于单测——这里正是 resume 子命令构造曾经出 bug 的地方。
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional


def build_codex_cmd(
    *,
    sandbox: str,
    cd: Path,
    skip_git_repo_check: bool = True,
    image_list: Optional[List[Path]] = None,
    model: str = "",
    profile: str = "",
    yolo: bool = False,
    session_id: str = "",
) -> List[str]:
    """返回 `codex exec ...` 的 argv（PROMPT 始终走 stdin，不进 argv）。

    关键：`resume` 是 `codex exec` 的**子命令**，选项集与 exec 不同——
      - resume 不支持 --sandbox / --cd / --profile（沿用原会话设置）
      - resume 的选项必须放在 `resume` **之后**；exec 级 flag（尤其 --json）
        放在 resume 之前会导致 resume 不输出 JSONL，解析不到 thread_id /
        agent_message，复审上下文续接形同失效
      - resume 的 PROMPT 用 `-` 显式声明从 stdin 读取
    工作目录对 resume 由 Popen(cwd=cd) 保证（resume 无 --cd）。
    `--image` 为多值选项，按文件重复传递而非逗号拼接。
    """
    images = image_list or []

    if session_id:
        cmd = ["codex", "exec", "resume", "--json"]
        if skip_git_repo_check:
            cmd.append("--skip-git-repo-check")
        for img in images:
            cmd.extend(["--image", str(img)])
        if model:
            cmd.extend(["--model", model])
        cmd.extend([str(session_id), "-"])  # SESSION_ID 位置参数；`-`=从 stdin 读 PROMPT
        return cmd

    cmd = ["codex", "exec", "--sandbox", sandbox, "--cd", str(cd), "--json"]
    if skip_git_repo_check:
        cmd.append("--skip-git-repo-check")
    for img in images:
        cmd.extend(["--image", str(img)])
    if model:
        cmd.extend(["--model", model])
    if profile:
        cmd.extend(["--profile", profile])
    if yolo:
        # codex 无 --yolo；正确 flag 是 --dangerously-bypass-approvals-and-sandbox
        cmd.append("--dangerously-bypass-approvals-and-sandbox")
    return cmd
