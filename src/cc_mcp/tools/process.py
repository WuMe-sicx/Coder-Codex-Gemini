"""Codex 子进程执行

进程组隔离、后台线程流式读取、空闲 + 总时长双超时、优雅关闭。
"""

from __future__ import annotations

import json
import os
import queue
import shutil
import signal
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, Iterator, Optional

from cc_mcp.tools.errors import CommandNotFoundError, CommandTimeoutError

# 进程组隔离：子进程放入独立进程组，防止父进程信号泄漏和孤儿进程
_POPEN_PROCESS_GROUP: dict[str, Any] = {"process_group": 0} if sys.platform != "win32" else {}

# turn.completed 标记出现后，等待剩余输出被 drain 的延迟
GRACEFUL_SHUTDOWN_DELAY = 0.3


def _terminate_process(process: subprocess.Popen) -> None:
    """终止子进程及其整个进程组"""
    if sys.platform == "win32":
        process.terminate()
        return
    try:
        pgid = os.getpgid(process.pid)
        os.killpg(pgid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            process.terminate()
        except (ProcessLookupError, OSError):
            pass


def _kill_process(process: subprocess.Popen) -> None:
    """强制杀死子进程及其整个进程组"""
    if sys.platform == "win32":
        process.kill()
        return
    try:
        pgid = os.getpgid(process.pid)
        os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            process.kill()
        except (ProcessLookupError, OSError):
            pass


def _is_turn_completed(line: str) -> bool:
    """检查是否回合完成（Codex 的 turn.completed 标记）"""
    try:
        data = json.loads(line)
        return data.get("type") == "turn.completed"
    except (json.JSONDecodeError, AttributeError, TypeError):
        return False


@contextmanager
def safe_codex_command(
    cmd: list[str],
    timeout: int = 300,
    max_duration: int = 1800,
    prompt: str = "",
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> Iterator[tuple[Generator[str, None, None], Dict[str, Any]]]:
    """安全执行 Codex 命令的上下文管理器

    确保在任何情况下（包括异常）都能正确清理子进程。

    用法:
        with safe_codex_command(cmd, timeout, max_duration, prompt) as (gen, result_holder):
            for line in gen:
                process_line(line)
            exit_code = result_holder["exit_code"]
    """
    codex_path = shutil.which('codex')
    if not codex_path:
        raise CommandNotFoundError(
            "未找到 codex CLI。请确保已安装 Codex CLI 并添加到 PATH。\n"
            "安装指南：https://developers.openai.com/codex/quickstart"
        )
    popen_cmd = cmd.copy()
    popen_cmd[0] = codex_path

    process = subprocess.Popen(
        popen_cmd,
        shell=False,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        encoding='utf-8',
        errors='replace',  # 处理非 UTF-8 字符，避免 UnicodeDecodeError
        env=env,
        cwd=str(cwd) if cwd else None,
        **_POPEN_PROCESS_GROUP,
    )

    thread: Optional[threading.Thread] = None

    def cleanup() -> None:
        """清理子进程和线程（best-effort，不抛异常）"""
        nonlocal thread
        # 1. 先关闭 stdout 以解除读取线程的阻塞
        try:
            if process.stdout and not process.stdout.closed:
                process.stdout.close()
        except (OSError, IOError):
            pass
        # 2. 终止进程（含整个进程组）
        try:
            if process.poll() is None:
                _terminate_process(process)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    _kill_process(process)
                    try:
                        process.wait(timeout=2)  # kill 后也设超时
                    except subprocess.TimeoutExpired:
                        pass  # 极端情况：进程无法终止，放弃
        except (ProcessLookupError, OSError):
            pass  # 进程已退出，忽略
        # 3. 等待线程结束
        if thread is not None and thread.is_alive():
            thread.join(timeout=5)

    try:
        # 通过 stdin 传递 prompt，然后关闭 stdin
        if process.stdin:
            try:
                if prompt:
                    process.stdin.write(prompt)
            except (BrokenPipeError, OSError):
                pass
            finally:
                try:
                    process.stdin.close()
                except (BrokenPipeError, OSError):
                    pass

        output_queue: queue.Queue[str | None] = queue.Queue()
        raw_output_lines_holder = [0]
        result_holder: Dict[str, Any] = {"exit_code": None, "raw_output_lines": 0}

        def read_output() -> None:
            """在单独线程中读取进程输出"""
            try:
                if process.stdout:
                    for line in iter(process.stdout.readline, ""):
                        stripped = line.strip()
                        output_queue.put(stripped)
                        if stripped:
                            raw_output_lines_holder[0] += 1
                        if _is_turn_completed(stripped):
                            time.sleep(GRACEFUL_SHUTDOWN_DELAY)
                            break
                    process.stdout.close()
            except (OSError, IOError, ValueError):
                pass  # stdout 被关闭，正常退出
            finally:
                output_queue.put(None)  # 确保投递哨兵

        thread = threading.Thread(target=read_output, daemon=True)
        thread.start()

        def generator() -> Generator[str, None, None]:
            """生成器：读取输出并处理超时"""
            nonlocal thread
            start_time = time.time()
            last_activity_time = time.time()
            timeout_error: CommandTimeoutError | None = None

            while True:
                now = time.time()

                if max_duration > 0 and (now - start_time) >= max_duration:
                    timeout_error = CommandTimeoutError(
                        f"codex 执行超时（总时长超过 {max_duration}s），进程已终止。",
                        is_idle=False
                    )
                    break

                if (now - last_activity_time) >= timeout:
                    timeout_error = CommandTimeoutError(
                        f"codex 空闲超时（{timeout}s 无输出），进程已终止。",
                        is_idle=True
                    )
                    break

                try:
                    line = output_queue.get(timeout=0.5)
                    if line is None:
                        break
                    last_activity_time = time.time()
                    if line:
                        yield line
                except queue.Empty:
                    if process.poll() is not None and not thread.is_alive():
                        break

            if timeout_error is not None:
                cleanup()
                raise timeout_error

            exit_code: Optional[int] = None
            try:
                exit_code = process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                # 输出已完整获取，进程只是退出慢（Windows 常见）
                # 静默终止进程，不视为致命错误
                _terminate_process(process)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    _kill_process(process)
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        pass  # 极端情况：进程无法终止，放弃
            finally:
                if thread is not None:
                    thread.join(timeout=5)

            while not output_queue.empty():
                try:
                    line = output_queue.get_nowait()
                    if line is not None:
                        yield line
                except queue.Empty:
                    break

            result_holder["exit_code"] = exit_code
            result_holder["raw_output_lines"] = raw_output_lines_holder[0]

        yield generator(), result_holder

    except Exception:
        cleanup()
        raise
    finally:
        cleanup()
