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
import json

from aidev_agent.enums import CredentialType
from aidev_agent.packages.resource_manager import AgentResourceManager, ResourceManagerProtocol
from aidev_agent.pydantic_models import AgentConfig
from aidev_bkplugin.services.agent_session import SessionManager
from django.conf import settings

from backend.components.base import DataAPI
from backend.configuration.constants import SystemSettingsEnum
from backend.configuration.models import SystemSettings

AGENT_CONFIG_TEMPLATE = {
    # 使用的 LLM（联系接口人获取可使用的 LLM 模型名称列表）。
    "chat_model": "deepseek-v3",
    # 非深度思考模型
    "non_thinking_llm": "",
    # 在 AIDev 站点上传知识，然后将对应的知识库 ID 或者知识 ID 填在此处，可以在 agent 使用的时候检索对应范围的知识。
    # 通常来讲，选择的知识越多，检索速度也会越慢，检索效果也会越差。一般建议只选择该 agent 需要使用的知识，不要选择无关知识。
    "knowledgebase_ids": [],
    "knowledge_ids": [],
    # 在 AIDev 站点注册工具，然后将对应的工具 tool_code 填在此处，可以在 agent 使用的时候调用相关工具。
    "tool_codes": [],
    # 在 CommonQAAgent 内置 prompt 的基础上，用户自定义的增量 prompt。
    # 目前内部实现方式是将用户自定义的增量 prompt 直接拼接到 CommonQAAgent 内置 prompt 上。
    # 因此，该 prompt 更适合只需简单的、与 CommonQAAgent 内置 prompt 没有冲突的自定义场景，
    # 例如要求 agent 根据用户最新提问使用的语言（中/英文）进行自适应的答复等场景。
    # 对于复杂的自定义 prompt 需求，请参考 README_AGENT_PLUGIN.md [情况二] 的内容，
    # 直接重写完整的 agent prompt 并注册到 CommonQAAgent 中进行替换。
    "role_prompt": "",
}


class DBMAgentResourceManager(AgentResourceManager):
    """DBM Agent配置管理器"""

    def __init__(self, agent_code: str = None, agent_secret: str = None, username: str = ""):
        agent_code = agent_code or settings.AGENT_APP_CODE
        agent_secret = agent_secret or settings.AGENT_APP_SECRET
        super().__init__(agent_code=agent_code, agent_secret=agent_secret)

    @classmethod
    def set_backend_mcp_config(cls, agent_config: AgentConfig):
        mcp_servers = agent_config.mcp_server_config
        for name, config in mcp_servers.items():
            # 将请求连接替换为应用请求，网关是加上application标识
            if "application" not in config["url"]:
                parsed_url = config["url"].rstrip("/").rsplit("/", 1)
                config["url"] = parsed_url[0] + "/application/" + parsed_url[1] + "/"
            # apigw mcp 添加校验头，后台请求用admin身份调用
            if config.get("credential_type", "") == CredentialType.BLUEAPPS.value:
                auth = {"bk_app_code": settings.APP_CODE, "bk_app_secret": settings.SECRET_KEY, "bk_username": "admin"}
                config["headers"] = {"X-Bkapi-Authorization": json.dumps(auth)}
                config["headers"]["X-Bk-Username"] = "admin"
                config["headers"]["X-Bkapi-Timeout"] = str(settings.BK_APIGW_MCP_TIMEOUT)
                config["headers"]["X-Bkapi-Allowed-Headers"] = "X-Bk-Username"
                config.pop("credential_type")

        return agent_config

    def get_agent_config(self, *args, **kwargs) -> AgentConfig:
        """可以使用本地 AGENT_CONFIG 配置覆盖"""
        agent_config: AgentConfig = super().get_agent_config(*args, **kwargs)
        # 后台调用对话模型，需要考虑 mcp server 调用无用户鉴权(celery/pipeline任务)
        if DataAPI.is_backend_request(None):
            agent_config = self.set_backend_mcp_config(agent_config)

        return agent_config

    def get_paas_sbx_client(self, executor_info: dict, **kwargs):
        client = super().get_paas_sbx_client(executor_info, **kwargs)
        # 手动修改url里面的app_code为项目app_code，保持鉴权一致性
        sandbox_app_urls = [
            "create_sandbox",
            "list_agent_sandbox_volumes",
            "create_agent_sandbox_volume",
            "delete_agent_sandbox_volume",
        ]
        for url in sandbox_app_urls:
            ins = getattr(client, url)
            ins.path = ins.path.replace("{app_code}", settings.APP_CODE)
        return client


def build_resource_manager(agent_code: str = None, username: str = "") -> ResourceManagerProtocol:
    """
    构建子智能体 resource-manager
    如果没配置，则默认走主智能体调用（快捷指令路由）
    :param agent_code: 子智能体 code，未配置 token 时回退到主智能体
    :param username: 用户名，用于用户态 access_token 注入（view 层透传）
    """
    agent_token_config = SystemSettings.get_setting_value(key=SystemSettingsEnum.AGENT_TOKEN_CONFIG, default={})
    agent_token = agent_token_config.get(agent_code, "")
    if not agent_token:
        return DBMAgentResourceManager(username=username)
    return DBMAgentResourceManager(agent_code, agent_token, username=username)


def build_session_manager(username: str = "", agent_code: str = None) -> SessionManager:
    """
    构建子智能体 session-manager
    如果没配置，则默认走主智能体调用（快捷指令路由）
    """
    resource_manager = build_resource_manager(agent_code)
    return SessionManager(
        username=username, agent_code=resource_manager.get_agent_code(), resource_manager=resource_manager
    )
