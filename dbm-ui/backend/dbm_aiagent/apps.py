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
import os

import bkoauth
from django.apps import AppConfig
from django.conf import settings

# 全局变量，用于存储 ticket-schema.json 的内容
TICKET_SCHEMA = {}


class DbmAiagentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "backend.dbm_aiagent"

    def ready(self) -> None:
        from aidev_agent.utils.module_loading import import_string
        from aidev_bkplugin.services.factory import agent_config_factory, agent_factory

        # 初始化bkoauth
        bkoauth._init_function()

        # 注册默认的agent
        agent_factory.register(settings.AIDEV_BKPLUGIN_DEFAULT_NAME, import_string(settings.DEFAULT_AGENT))
        agent_config_factory.register(
            settings.AIDEV_BKPLUGIN_DEFAULT_NAME, import_string(settings.DEFAULT_CONFIG_MANAGER)
        )

        # 加载 init 目录下的 ticket-schema.json 文件
        global TICKET_SCHEMA
        init_dir = os.path.join(os.path.dirname(__file__), "init")
        schema_file = os.path.join(init_dir, "ticket-schema.json")
        if os.path.exists(schema_file):
            with open(schema_file, "r", encoding="utf-8") as f:
                TICKET_SCHEMA = json.load(f)
        return super().ready()
