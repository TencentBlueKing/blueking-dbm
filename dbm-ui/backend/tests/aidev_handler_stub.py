# -*- coding: utf-8 -*-
"""CI/本地单测默认 ENABLE_DBM_AI=false，aidev_bkplugin 不在 INSTALLED_APPS。

AgentHandler 所在模块会 import aidev_bkplugin 的 Django 模型（如 Checkpoint）。
单测 @patch("backend.dbm_aiagent.agent.handlers.AgentHandler....") 会先加载真实模块而报错。
本函数在 conftest 最早阶段把假模块塞进 sys.modules，让 patch 打到 MagicMock 上。

这只解决「单测 patch」。未开 AI 的生产进程仍必须对 AgentHandler 延迟导入，
否则 Django/flow 一加载组件就会 import handlers，整个流程拉不起来。
"""
import os
import sys
from types import ModuleType
from unittest.mock import MagicMock

_MOD_NAME = "backend.dbm_aiagent.agent.handlers"


def install_agent_handler_stub_if_ai_disabled():
    flag = os.environ.get("ENABLE_DBM_AI", "").lower()
    if flag in ("1", "true", "yes"):
        return
    existing = sys.modules.get(_MOD_NAME)
    if existing is not None:
        return
    stub = ModuleType(_MOD_NAME)
    stub.AgentHandler = MagicMock(name="AgentHandler")
    stub._dbm_test_stub = True
    sys.modules[_MOD_NAME] = stub


install_agent_handler_stub_if_ai_disabled()
