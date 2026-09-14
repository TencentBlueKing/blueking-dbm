# -*- coding: utf-8 -*-
"""AgentHandler 必须延迟导入。

handlers 依赖 aidev_bkplugin（仅 ENABLE_DBM_AI=true 时进入 INSTALLED_APPS）。
flow 组件、单据 builder 在 Django 启动时就会被 import；若模块顶层写
`from backend.dbm_aiagent.agent.handlers import AgentHandler`，未开 AI 的环境
会加载 Checkpoint 等模型，整个流程拉不起来。

conftest 里的 stub 只保证单测 patch 不炸，挡不住生产启动路径上的顶层导入，
因此这里用 AST 扫描源码。
"""
import ast
from pathlib import Path

_HANDLER_MODULE = "backend.dbm_aiagent.agent.handlers"
_BACKEND_DIR = Path(__file__).resolve().parents[2]
# Django 启动就会走到的路径：flow 引擎/组件、单据 builder
_STARTUP_REL_DIRS = ("flow", "ticket")


def _is_handlers_import(node: ast.AST) -> bool:
    if isinstance(node, ast.Import):
        return any(
            alias.name == _HANDLER_MODULE or alias.name.startswith(_HANDLER_MODULE + ".") for alias in node.names
        )
    if isinstance(node, ast.ImportFrom):
        mod = node.module or ""
        if mod == _HANDLER_MODULE:
            return True
        if mod == "backend.dbm_aiagent.agent" and any(alias.name == "handlers" for alias in node.names):
            return True
    return False


def _iter_import_time_imports(tree: ast.AST):
    """只看 import 时就会执行的语句（跳过函数体）。类体/模块级 if/try 仍算启动路径。"""

    def walk(stmts):
        for node in stmts:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if isinstance(node, ast.ClassDef):
                yield from walk(node.body)
                continue
            if isinstance(node, ast.If):
                yield from walk(node.body)
                yield from walk(node.orelse)
                continue
            if isinstance(node, ast.Try):
                yield from walk(node.body)
                for handler in node.handlers:
                    yield from walk(handler.body)
                yield from walk(node.orelse)
                yield from walk(node.finalbody)
                continue
            if isinstance(node, (ast.With, ast.AsyncWith)):
                yield from walk(node.body)
                continue
            if _is_handlers_import(node):
                yield node

    yield from walk(tree.body)


def _scan_startup_top_level_handler_imports():
    hits = []
    for rel in _STARTUP_REL_DIRS:
        for path in (_BACKEND_DIR / rel).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in _iter_import_time_imports(tree):
                hits.append(f"{path.relative_to(_BACKEND_DIR.parent)}:{node.lineno}")
    return hits


def test_agent_handler_must_be_lazily_imported_on_flow_startup_path():
    hits = _scan_startup_top_level_handler_imports()
    assert hits == [], "ENABLE_DBM_AI=false 时顶层导入 AgentHandler 会加载 aidev_bkplugin 并拖垮 flow 启动。" f"请改为函数内延迟导入: {hits}"
