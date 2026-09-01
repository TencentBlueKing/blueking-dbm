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
import logging

from aidev_agent.enums import CredentialType
from aidev_agent.pydantic_models import AgentConfig
from aidev_bkplugin.services.agent_builder import LLMOverrideResourceManager
from aidev_bkplugin.services.agent_session import SessionManager
from django.conf import settings
from django.core.cache import cache

from backend.components import bk
from backend.components.base import DataAPI
from backend.configuration.constants import SystemSettingsEnum
from backend.configuration.models import SystemSettings
from backend.env import DEFAULT_USERNAME
from backend.utils.local import local

logger = logging.getLogger("root")

# Agent 级别 access_token 缓存 key 模板与过期时间（秒）
AGENT_ACCESS_TOKEN_CACHE_KEY_TPL = "agent_access_token::{agent_code}::{username}"
AGENT_ACCESS_TOKEN_CACHE_TTL = 12 * 60 * 60

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


class DBMAgentResourceManager(LLMOverrideResourceManager):
    """DBM Agent配置管理器"""

    def __init__(self, username="", agent_code: str = None, agent_secret: str = None, model: str = ""):
        """
        :param model: 覆盖智能体发布时配置的 chat_model，为空时沿用平台配置
        """
        agent_code = agent_code or settings.AGENT_APP_CODE
        agent_secret = agent_secret or settings.AGENT_APP_SECRET
        # TODO：这里不能传递真实的username，暂时为空
        username = "" if username == DEFAULT_USERNAME else username
        super().__init__(app_code=agent_code, app_secret=agent_secret, username=username, model=model)

    @classmethod
    def set_backend_mcp_config(cls, agent_config: AgentConfig):
        """设置后台mcp鉴权配置"""
        mcp_servers = agent_config.mcp_server_config
        for name, config in mcp_servers.items():
            # 将请求连接替换为应用请求，网关是加上application标识
            if "application" not in config["url"]:
                parsed_url = config["url"].rstrip("/").rsplit("/", 1)
                config["url"] = parsed_url[0] + "/application/" + parsed_url[1] + "/"
            # apigw mcp 添加校验头，后台请求用admin身份调用
            if config.get("credential_type", "") == CredentialType.BLUEAPPS.value:
                # auth = {"bk_app_code": settings.APP_CODE, "bk_app_secret": settings.SECRET_KEY, "bk_username": "admin"}
                # config["headers"] = {"X-Bkapi-Authorization": json.dumps(auth)}
                # config["headers"]["X-Bk-Username"] = "admin"
                # config["headers"]["X-Bkapi-Allowed-Headers"] = "X-Bk-Username"
                auth = {"access_token": settings.DBM_APP_ACCESS_TOKEN}
                config["headers"] = {"X-Bkapi-Authorization": json.dumps(auth)}
                config["headers"]["X-Bkapi-Timeout"] = str(settings.BK_APIGW_MCP_TIMEOUT)
                config.pop("credential_type")

        return agent_config

    def get_agent_config(self, *args, **kwargs) -> AgentConfig:
        """可以使用本地 AGENT_CONFIG 配置覆盖"""
        agent_config: AgentConfig = super().get_agent_config(*args, **kwargs)
        # 后台调用对话模型，需要考虑 mcp server 调用无用户鉴权(celery/pipeline任务)
        if DataAPI.is_backend_request(None):
            agent_config = self.set_backend_mcp_config(agent_config)

        return agent_config

    def _resolve_user_access_token(self, username):
        """使用 Agent app_code + 用户身份信息，向鉴权网关(OAUTH_API_URL)换取 Agent 级别的 access_token。

        bkoauth 数据库缓存的 access_token 由 DBM 自身 app_code 派发，其主体与 Agent 不一致；
        因此这里携带当前请求的用户认证信息(bk_token/bk_ticket)，以 Agent app_code 为主体，
        走网关标准接口换取 access_token。为提升效率，按 `agent_code::username` 维度缓存。
        仅在存在请求上下文（非 celery/pipeline 后台任务）且请求用户与目标用户一致时生效。
        """
        request = local.request
        if not username or not request:
            return ""

        # 认证信息(bk_token/bk_ticket)属于当前登录用户，仅当与目标用户一致时才可用于换取其 token
        if getattr(getattr(request, "user", None), "username", "") != username:
            return ""

        # 优先从缓存获取access token
        agent_code = self.get_agent_code()
        cache_key = AGENT_ACCESS_TOKEN_CACHE_KEY_TPL.format(agent_code=agent_code, username=username)
        access_token = cache.get(cache_key)
        if access_token:
            return access_token

        # 以 Agent app 凭证为主体，通过鉴权网关标准接口换取用户 access_token
        access_token = bk.resolve_user_access_token(request, self.app_code, self.app_secret)
        if access_token:
            cache.set(cache_key, access_token, AGENT_ACCESS_TOKEN_CACHE_TTL)
        return access_token

    def resolve_access_token(self, username: str = None) -> str:
        """解析 access_token：

        - 后台/虚拟用户(admin / DBM_APP_USER)：使用 DBM 平台虚拟账户 token（由 DBM app_code 派发，用于后台任务）；
        - 显式传入 access_token：直接使用；
        - 其余真实用户：以 Agent app_code 为主体，携带用户身份向 PaaS 平台换取 Agent 级别 token（带缓存）。
        """
        _username = username or self.username
        # 后台/虚拟用户直接使用 DBM 平台虚拟账户 access_token
        if _username in ("admin", settings.DBM_APP_USER, DEFAULT_USERNAME):
            return settings.DBM_APP_ACCESS_TOKEN
        # 显式传入 access_token 优先
        if self.access_token:
            return self.access_token
        return self._resolve_user_access_token(_username)

    def get_paas_sbx_client(self, executor_info: dict, **kwargs):
        """修改paas sandbox的鉴权配置"""
        client = super().get_paas_sbx_client(executor_info, **kwargs)
        if executor_info.get("executor", "") not in ["", "admin", DEFAULT_USERNAME]:
            return client
        # 手动修改url里面的app_code为项目app_code，保持应用鉴权一致性
        sandbox_app_urls = [
            "create_sandbox",
            "list_agent_sandbox_volumes",
            "create_agent_sandbox_volume",
            "delete_agent_sandbox_volume",
        ]
        for url in sandbox_app_urls:
            ins = getattr(client, url)
            ins.path = ins.path.replace("{app_code}", settings.APP_CODE)
        # 如果是后台请求，则使用虚拟身份调用
        user, access_token = settings.DBM_APP_USER, settings.DBM_APP_ACCESS_TOKEN
        client.update_bkapi_authorization(access_token=access_token, bk_username=user)
        return client


def build_resource_manager(agent_code, username, model: str = "") -> DBMAgentResourceManager:
    """
    构建子智能体 resource-manager
    如果没配置，则默认走主智能体调用（快捷指令路由）
    :param agent_code: 子智能体 code，未配置 token 时回退到主智能体
    :param username: 用户名，用于用户态 access_token 注入（view 层透传）
    :param model: 覆盖智能体发布时配置的 chat_model，为空时沿用平台配置
    """
    agent_token_config = SystemSettings.get_setting_value(key=SystemSettingsEnum.AGENT_TOKEN_CONFIG, default={})
    agent_token = agent_token_config.get(agent_code, "")
    if not agent_token:
        return DBMAgentResourceManager(username, model=model)
    return DBMAgentResourceManager(username, agent_code, agent_token, model=model)


def build_session_manager(agent_code, username) -> SessionManager:
    """
    构建子智能体 session-manager
    如果没配置，则默认走主智能体调用（快捷指令路由）
    """
    resource_manager = build_resource_manager(agent_code, username)
    return SessionManager(
        username=username, agent_code=resource_manager.get_agent_code(), resource_manager=resource_manager
    )
