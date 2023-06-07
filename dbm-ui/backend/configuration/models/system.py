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
from typing import Any, Dict, Optional, Union

from blue_krill.data_types.enum import EnumField, StructuredEnum
from django.conf import settings
from django.db import connection, models
from django.utils.translation import ugettext_lazy as _

from backend.bk_web.constants import LEN_LONG, LEN_NORMAL
from backend.bk_web.models import AuditedModel
from backend.configuration.constants import DEFAULT_SETTINGS

logger = logging.getLogger("root")


class SystemSettingsEnum(str, StructuredEnum):
    """配置的枚举项，建议将系统配置都录入到这里方便统一管理"""

    BK_ITSM_SERVICE_ID = EnumField("BK_ITSM_SERVICE_ID", _("DBM的流程服务ID"))
    RESOURCE_TOPO = EnumField("RESOURCE_TOPO", _("资源池主机存放的拓扑信息"))


class SystemSettings(AuditedModel):
    type = models.CharField(_("类型"), max_length=LEN_NORMAL)
    key = models.CharField(_("关键字唯一标识"), max_length=LEN_NORMAL, unique=True)
    value = models.JSONField(_("系统设置值"))
    desc = models.CharField(_("描述"), max_length=LEN_LONG)

    class Meta:
        verbose_name = _("系统设置")
        verbose_name_plural = _("系统设置")
        ordering = ("id",)

    @classmethod
    def init_default_settings(cls, *args, **kwargs):
        """初始化system的默认配置"""
        for setting in DEFAULT_SETTINGS:
            # logger.info("init_default_settings get_or_create_setting: {0}".format(setting))
            cls.objects.get_or_create(
                defaults={
                    "type": setting[1],
                    "value": setting[2],
                    "desc": setting[3],
                    "creator": "system",
                    "updater": "system",
                },
                key=setting[0],
            )

    @classmethod
    def register_system_settings(cls):
        """
        将system settings的配置注册到django settings中
        默认不覆盖已加载的settings配置项
        """

        # 初次部署表不存在时跳过DB写入操作
        if cls._meta.db_table not in connection.introspection.table_names():
            logger.info(f"{cls._meta.db_table} not exists, skip register_system_settings before migrate.")
            return

        for system_setting in cls.objects.all():
            if not hasattr(settings, system_setting.key):
                setattr(settings, system_setting.key, system_setting.value)

    @classmethod
    def get_setting_value(cls, key: str, default: Optional[Any] = None) -> Union[str, Dict]:
        try:
            setting_value = cls.objects.get(key=key).value
        except cls.DoesNotExist:
            setting_value = default or ""
        return setting_value

    @classmethod
    def insert_setting_value(cls, key: str, value: Any, value_type: str = "str", user: str = "admin") -> None:
        """插入一条系统配置记录"""
        cls.objects.update_or_create(
            defaults={
                "type": value_type,
                "value": value,
                "desc": SystemSettingsEnum.get_choice_label(key),
                "updater": user,
            },
            key=key,
        )
