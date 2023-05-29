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
from django.utils.translation import ugettext as _

logger = logging.getLogger("root")


def init_config(sender, **kwargs):
    """初始化配置自动执行"""
    try:
        from backend.dbm_init.services import Services

        Services.init_custom_metric_and_event()
    except Exception as e:  # pylint: disable=broad-except
        logger.warning(_("初始化配置异常，错误信息:{}").format(e))


def register_resource_class():
    """初始化注册resource类"""
    from backend.db_services.dbbase.resources import register

    register.register_all_resource()


class DbmInitConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "backend.dbm_init"

    def ready(self):
        """
        项目初始化，自动生成配置文件和运行相关服务
        注：这部分目前统一挪到k8s的job进行初始化
        """
        register_resource_class()
        pass
