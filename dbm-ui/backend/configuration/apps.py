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

from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.utils.translation import ugettext_lazy as _

logger = logging.getLogger("root")


def register_system_settings(sender, **kwargs):
    """初始化配置"""

    from .models.function_controller import FunctionController
    from .models.system import SystemSettings

    try:
        SystemSettings.init_default_settings()
        SystemSettings.register_system_settings()
        FunctionController.init_function_controller()
    except Exception as e:  # pylint: disable=broad-except
        logger.error(_("初始化配置异常，错误信息:{}").format(e))


class ConfigurationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "backend.configuration"

    def ready(self):
        post_migrate.connect(register_system_settings, sender=self)
