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

import logging

from aidev_bkplugin.apps import AgentConfig
from django.apps import AppConfig

logger = logging.getLogger("root")


class DbmAiagentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "backend.dbm_aiagent"

    def ready(self):
        pass


class SafeAidevBkpluginConfig(AgentConfig):
    """替换 aidev_bkplugin 默认 AppConfig，启动异常时 fail-open。"""

    name = "aidev_bkplugin"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        try:
            super().ready()
        except Exception:
            logger.exception("[dbm_aiagent] aidev_bkplugin AppConfig.ready failed; skip and continue DBM startup")
