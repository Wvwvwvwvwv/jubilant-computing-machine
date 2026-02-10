from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
import asyncio
import uuid
from pathlib import Path

router = APIRouter()

SANDBOX_DIR = Path.home() / "roampal-android" / "data" / "sandbox"
SANDBOX_DIR.mkdir(parents=True, exist_ok=True)

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
    
    # Сохранение кода
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
    
    # Выполнение с таймаутом
    try:
        import time
        start_time = time.time()
        
        process = await asyncio.create_subprocess_exec(
            interpreter, str(code_file),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(workspace)
        )
        
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=request.timeout
        )
        
        execution_time = time.time() - start_time
        
        return ExecutionResult(
            execution_id=execution_id,
            stdout=stdout.decode('utf-8', errors='replace'),
            stderr=stderr.decode('utf-8', errors='replace'),
            exit_code=process.returncode,
            execution_time=execution_time
        )
        
    except asyncio.TimeoutError:
        process.kill()
        raise HTTPException(status_code=408, detail="Превышен таймаут выполнения")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list")
async def list_executions():
    """Список выполненных задач"""
    
    executions = []
    for workspace in SANDBOX_DIR.iterdir():
        if workspace.is_dir():
            executions.append({
                "id": workspace.name,
                "created": workspace.stat().st_ctime
            })
    
    return {"executions": executions, "count": len(executions)}

@router.delete("/{execution_id}")
async def delete_execution(execution_id: str):
    """Удалить workspace выполнения"""
    
    workspace = SANDBOX_DIR / execution_id
    if workspace.exists():
        import shutil
        shutil.rmtree(workspace)
        return {"status": "deleted"}
    
    raise HTTPException(status_code=404, detail="Выполнение не найдено")
