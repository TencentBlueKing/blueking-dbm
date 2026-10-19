# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

import importlib
import json
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from aidev_agent.enums import CredentialType
from django.test import override_settings

_MANAGER_MOD = "backend.dbm_aiagent.agent.configs.manager"
_MODELS_MOD = "aidev_bkplugin.models"
_FAKE_MODEL_NAMES = ("Checkpoint", "Write", "EventSubscription", "EventDelivery")

MCP_SERVER = "bkdbm-mcp-prod-ticket-op"
MCP_URL = "https://bkapi.example.com/api/bk-apigateway/prod/api/v2/mcp-servers/bkdbm-mcp-prod-ticket-op/mcp/"
APP_ACCESS_TOKEN = "dbm-app-token"


def _agent_config(**server_config):
    config = {"url": MCP_URL, "transport": "streamable_http", **server_config}
    return SimpleNamespace(mcp_server_config={MCP_SERVER: config})


@pytest.fixture(scope="module")
def manager():
    """aidev 未进 INSTALLED_APPS 时 aidev_bkplugin.models 无法导入，先放入假模块，manager 才能导入。"""
    installed_fake_models = False
    if _MODELS_MOD not in sys.modules:
        try:
            importlib.import_module(_MODELS_MOD)
        except RuntimeError:
            sys.modules.pop(_MODELS_MOD, None)
            fake = ModuleType(_MODELS_MOD)
            for name in _FAKE_MODEL_NAMES:
                setattr(fake, name, MagicMock(name=name))
            sys.modules[_MODELS_MOD] = fake
            installed_fake_models = True
    try:
        yield importlib.import_module(_MANAGER_MOD)
    finally:
        if installed_fake_models:
            sys.modules.pop(_MODELS_MOD, None)


@pytest.fixture
def backend_settings():
    with override_settings(DBM_APP_ACCESS_TOKEN=APP_ACCESS_TOKEN, BK_APIGW_MCP_TIMEOUT=300):
        yield


@pytest.mark.usefixtures("backend_settings")
class TestSetBackendMcpConfig:
    def test_multi_tenant_declares_tenant_header_passthrough(self, manager):
        agent_config = _agent_config(credential_type=CredentialType.BLUEAPPS.value)

        with patch.object(manager, "BK_TENANT_ID", "tencent"):
            config = manager.DBMAgentResourceManager.set_backend_mcp_config(agent_config).mcp_server_config[MCP_SERVER]

        assert config["headers"] == {
            "X-Bkapi-Authorization": json.dumps({"access_token": APP_ACCESS_TOKEN}),
            "X-Bkapi-Timeout": "300",
            "X-Bk-Tenant-Id": "tencent",
            "X-Bkapi-Allowed-Headers": "X-Bk-Tenant-Id",
        }
        assert "credential_type" not in config
        assert config["url"].endswith("/mcp-servers/bkdbm-mcp-prod-ticket-op/application/mcp/")

    def test_single_tenant_omits_tenant_headers(self, manager):
        agent_config = _agent_config(credential_type=CredentialType.BLUEAPPS.value)

        with patch.object(manager, "BK_TENANT_ID", ""):
            headers = manager.DBMAgentResourceManager.set_backend_mcp_config(agent_config).mcp_server_config[
                MCP_SERVER
            ]["headers"]

        assert "X-Bk-Tenant-Id" not in headers
        assert "X-Bkapi-Allowed-Headers" not in headers

    def test_non_blueapps_server_headers_untouched(self, manager):
        agent_config = _agent_config(headers={"Authorization": "Bearer x"})

        with patch.object(manager, "BK_TENANT_ID", "tencent"):
            config = manager.DBMAgentResourceManager.set_backend_mcp_config(agent_config).mcp_server_config[MCP_SERVER]

        assert config["headers"] == {"Authorization": "Bearer x"}
