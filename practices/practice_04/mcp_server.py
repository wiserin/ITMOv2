from __future__ import annotations
import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

from mcp.server import MCPServer


def run_pytest_logic(project_root: Path, target: Optional[str], timeout_sec: int) -> Dict[str, Any]:
    venv_python = project_root / ".venv" / "bin" / "python"
    python_exec = str(venv_python) if venv_python.exists() else sys.executable
    cmd = [python_exec, "-m", "pytest", "-q"]
    if target:
        tpath = (project_root / target).resolve()
        try:
            tpath.relative_to(project_root.resolve())
        except ValueError:
            return {
                "success": False,
                "exit_code": None,
                "stdout": "",
                "stderr": f"Invalid target outside project: {tpath}",
            }
        if not tpath.exists():
            return {
                "success": False,
                "exit_code": None,
                "stdout": "",
                "stderr": f"Target not found: {tpath}",
            }
        rel = os.path.relpath(str(tpath), str(project_root))
        cmd.append(rel)

    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(project_root), env.get("PYTHONPATH", "")])

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(project_root),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_sec,
            text=True,
        )
        return {
            "success": proc.returncode == 0,
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
    except subprocess.TimeoutExpired as ex:
        return {
            "success": False,
            "exit_code": None,
            "stdout": ex.stdout or "",
            "stderr": (str(ex.stderr) or "") + f"\nTimeout after {timeout_sec} seconds",
        }


app = MCPServer("practice4")


@app.tool()
def ping() -> str:
    return "pong"


@app.tool()
def run_tests(target: Optional[str] = None) -> Dict[str, Any]:
    project_root = Path(__file__).parent.resolve()
    return run_pytest_logic(project_root, target, timeout_sec=30)


if __name__ == "__main__":
    app.run()
