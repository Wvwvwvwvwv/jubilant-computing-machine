import asyncio
import errno
import os
from pathlib import Path
import resource
import shutil
import subprocess
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

SANDBOX_DIR = Path.home() / "roampal-android" / "data" / "sandbox"
SANDBOX_DIR.mkdir(parents=True, exist_ok=True)


def _is_termux_android() -> bool:
    prefix = os.environ.get("PREFIX", "")
    android_root = os.environ.get("ANDROID_ROOT", "")
    return "com.termux" in prefix or bool(android_root)


def _apply_seccomp_if_available():
    """Best-effort seccomp policy (applied only when module is available)."""
    try:
        import seccomp  # type: ignore

        filt = seccomp.SyscallFilter(defaction=seccomp.ERRNO(errno.EPERM))
        # Conservative allow-list for common interpreted workloads.
        allowed = [
            "read",
            "write",
            "close",
            "fstat",
            "lseek",
            "mmap",
            "mprotect",
            "munmap",
            "brk",
            "rt_sigaction",
            "rt_sigprocmask",
            "rt_sigreturn",
            "ioctl",
            "pread64",
            "pwrite64",
            "readv",
            "writev",
            "access",
            "pipe",
            "select",
            "sched_yield",
            "mremap",
            "msync",
            "mincore",
            "madvise",
            "dup",
            "dup2",
            "nanosleep",
            "getpid",
            "socket",
            "connect",
            "sendto",
            "recvfrom",
            "recvmsg",
            "shutdown",
            "bind",
            "listen",
            "getsockname",
            "getpeername",
            "socketpair",
            "setsockopt",
            "getsockopt",
            "clone",
            "fork",
            "vfork",
            "execve",
            "exit",
            "wait4",
            "kill",
            "uname",
            "fcntl",
            "fsync",
            "fdatasync",
            "truncate",
            "ftruncate",
            "getdents",
            "getcwd",
            "chdir",
            "fchdir",
            "rename",
            "mkdir",
            "rmdir",
            "creat",
            "link",
            "unlink",
            "symlink",
            "readlink",
            "chmod",
            "fchmod",
            "chown",
            "fchown",
            "lchown",
            "umask",
            "gettimeofday",
            "getrlimit",
            "getrusage",
            "sysinfo",
            "times",
            "ptrace",
            "getuid",
            "syslog",
            "getgid",
            "setuid",
            "setgid",
            "geteuid",
            "getegid",
            "setpgid",
            "getppid",
            "getpgrp",
            "setsid",
            "setreuid",
            "setregid",
            "getgroups",
            "setgroups",
            "setresuid",
            "getresuid",
            "setresgid",
            "getresgid",
            "getpgid",
            "setfsuid",
            "setfsgid",
            "getsid",
            "capget",
            "capset",
            "prctl",
            "arch_prctl",
            "set_tid_address",
            "set_robust_list",
            "futex",
            "clock_gettime",
            "clock_getres",
            "clock_nanosleep",
            "openat",
            "newfstatat",
            "unlinkat",
            "renameat",
        ]
        for name in allowed:
            try:
                filt.add_rule(seccomp.ALLOW, name)
            except Exception:
                continue
        filt.load()
    except Exception:
        # seccomp module may be absent on Termux; keep best-effort behavior.
        return


def _sandbox_preexec():
    """Best-effort resource limits for child process."""
    resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
    # On Android bionic, too-low RLIMIT_AS can crash loader CFI shadow mapping.
    if not _is_termux_android():
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 * 1024, 10 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
    resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
    os.setsid()
    _apply_seccomp_if_available()


def _clam_scan(path: Path):
    """Run ClamAV scan if available; blocks execution on malware detection."""
    scanner = shutil.which("clamscan") or shutil.which("clamdscan")
    if not scanner:
        return

    proc = subprocess.run(
        [scanner, "--no-summary", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode == 1:
        raise HTTPException(status_code=400, detail="Файл отклонен ClamAV: обнаружена угроза")
    if proc.returncode not in (0, 1):
        raise HTTPException(status_code=500, detail=f"Ошибка ClamAV: {proc.stderr.strip()}")


class CodeExecutionRequest(BaseModel):
    code: str
    language: str = "python"
    timeout: int = 30


class ExecutionResult(BaseModel):
    execution_id: str
    stdout: str
    stderr: str
    exit_code: int
    execution_time: float


@router.post("/execute", response_model=ExecutionResult)
async def execute_code(request: CodeExecutionRequest):
    """Выполнить код в песочнице"""

    execution_id = str(uuid.uuid4())[:8]
    workspace = SANDBOX_DIR / execution_id
    workspace.mkdir(exist_ok=True)

    if request.language == "python":
        code_file = workspace / "script.py"
        interpreter = "python"
    elif request.language == "javascript":
        code_file = workspace / "script.js"
        interpreter = "node"
    elif request.language == "bash":
        code_file = workspace / "script.sh"
        interpreter = "bash"
    else:
        raise HTTPException(status_code=400, detail="Неподдерживаемый язык")

    code_file.write_text(request.code)
    _clam_scan(code_file)

    try:
        import time

        start_time = time.time()

        process = await asyncio.create_subprocess_exec(
            interpreter,
            str(code_file),
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(workspace),
            env={"PATH": os.environ.get("PATH", "")},
            preexec_fn=_sandbox_preexec,
        )

        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=request.timeout)

        execution_time = time.time() - start_time

        return ExecutionResult(
            execution_id=execution_id,
            stdout=stdout.decode("utf-8", errors="replace"),
            stderr=stderr.decode("utf-8", errors="replace"),
            exit_code=process.returncode if process.returncode is not None else 1,
            execution_time=execution_time,
        )

    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        raise HTTPException(status_code=408, detail="Превышен таймаут выполнения")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_executions():
    """Список выполненных задач"""

    executions = []
    for workspace in SANDBOX_DIR.iterdir():
        if workspace.is_dir():
            executions.append({"id": workspace.name, "created": workspace.stat().st_ctime})

    return {"executions": executions, "count": len(executions)}


@router.delete("/{execution_id}")
async def delete_execution(execution_id: str):
    """Удалить workspace выполнения"""

    workspace = SANDBOX_DIR / execution_id
    if workspace.exists():
        import shutil as _shutil

        _shutil.rmtree(workspace)
        return {"status": "deleted"}

    raise HTTPException(status_code=404, detail="Выполнение не найдено")
