from pathlib import Path
from uuid import uuid4
from typing import Any, Dict, List
import ast
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import json

def _is_python_file(path: Path) -> bool:
    return path.suffix == ".py"

def analyze_repo_code(repo_path: Path) -> Dict[str, Any]:
    modules = []
    tests = []
    configs = []

    for path in repo_path.rglob("*.py"):
        rel = path.relative_to(repo_path).as_posix()

        # logic to Detect tests by common patterns
        is_test_file = (
            rel.startswith("tests/")                 # tests/...
            or rel.endswith("_test.py")             # foo_test.py
            or rel.split("/")[-1].startswith("test_")  # test_foo.py anywhere
        )

        if is_test_file:
            tests.append(rel)

        module_info = _analyze_repo_file(path, rel)
        modules.append(module_info)
    
    for pattern in ("*yaml", "*yml", ".env"):
        for path in repo_path.rglob(pattern):
            configs.append(path.relative_to(repo_path).as_posix())


    return {
        "modules": modules,
        "tests" : tests,
        "configs": configs,
    }

def _analyze_repo_file(path: Path, rel_path: str) -> Dict[str, Any]:
    source = path.read_text(encoding="utf-8", errors='ignore')
    tree = ast.parse(source)

    functions=[]
    classes =[]
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            calls = _collect_calls(node)
            functions.append(
                {
                    "name": node.name,
                    "calls": list(sorted(calls)),
                }
            )
        elif isinstance(node, ast.ClassDef):
            methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
            classes.append(
                {
                    "name": node.name,
                    "methods": methods,
                }
            )
    return{
        "path": rel_path,
        "functions": functions,
        "classes": classes,
    }

def _collect_calls(func_node: ast.FunctionDef) -> set[str]:
    calls: set[str] = set()
    for node in ast.walk(func_node):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
    return calls

async def save_code_structure(
    db: AsyncSession,
    job_id,
    repo_url: str,
    branch: str,
    structure: Dict[str, Any],
) -> None:
    stmt = text("""
        insert into code_structures (id, job_id, repo_url, branch, structure_json)
        values (:id, :job_id, :repo_url, :branch, CAST(:structure_json AS jsonb))
""")
    await db.execute(
        stmt,
        {
            "id": uuid4(),
            "job_id": job_id,
            "repo_url": repo_url,
            "branch": branch,
            "structure_json": json.dumps(structure),
        },
    )
    await db.commit()