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

from django.conf import settings
from django.db import connection, models
from django.utils.translation import ugettext_lazy as _

from backend import env
from backend.bk_web.constants import LEN_LONG, LEN_NORMAL
from backend.bk_web.models import AuditedModel
from backend.configuration import constants
from backend.configuration.constants import BizSettingsEnum, SystemSettingsEnum

logger = logging.getLogger("root")


class AbstractSettings(AuditedModel):
    """定义配置表的基本字段"""

    type = models.CharField(_("类型"), max_length=LEN_NORMAL)
    key = models.CharField(_("关键字唯一标识"), max_length=LEN_NORMAL, unique=True)
    value = models.JSONField(_("系统设置值"))
    desc = models.CharField(_("描述"), max_length=LEN_LONG)

    @classmethod
    def get_setting_value(cls, key: dict, default: Optional[Any] = None) -> Union[str, Dict]:
        """插入一条配置记录"""
        try:
            setting_value = cls.objects.get(**key).value
        except cls.DoesNotExist:
            if default is None:
                setting_value = ""
            else:
                setting_value = default
        return setting_value

    @classmethod
    def insert_setting_value(
        cls, key: dict, value: Any, desc: str = "", value_type: str = "str", user: str = "admin"
    ) -> None:
        """插入一条配置记录"""
        cls.objects.update_or_create(
            defaults={
                "type": value_type,
                "value": value,
                "desc": desc,
                "updater": user,
            },
            **key,
        )

    class Meta:
        abstract = True


class SystemSettings(AbstractSettings):
    """系统配置表"""

    class Meta:
        verbose_name = _("系统设置")
        verbose_name_plural = _("系统设置")
        ordering = ("id",)

    @classmethod
    def init_default_settings(cls, *args, **kwargs):
        """初始化system的默认配置"""
        for setting in constants.DEFAULT_SETTINGS:
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
        return super().get_setting_value(key={"key": key}, default=default)

    @classmethod
    def insert_setting_value(cls, key: str, value: Any, value_type: str = "str", user: str = "admin") -> None:
        return super().insert_setting_value(
            key={"key": key},
            value=value,
            value_type=value_type,
            user=user,
            desc=constants.SystemSettingsEnum.get_choice_label(key),
        )

    @classmethod
    def get_exact_hosting_biz(cls, bk_biz_id: int) -> int:
        """
        查询业务在 CMDB 准确托管的业务
        DBM 管理的机器托管有两类
        1. 全部托管到 DBA 业务下（env.DBA_APP_BK_BIZ_ID）
        2. 全部托管到业务下
        不支持混合的情况
        """
        if bk_biz_id in cls.get_setting_value(constants.SystemSettingsEnum.INDEPENDENT_HOSTING_BIZS.value, default=[]):
            return bk_biz_id
        return env.DBA_APP_BK_BIZ_ID


class BizSettings(AbstractSettings):
    """业务配置表"""

    bk_biz_id = models.IntegerField(help_text=_("业务ID"))

    class Meta:
        indexes = [
            models.Index(fields=["bk_biz_id"]),
        ]
        verbose_name = _("业务配置")
        verbose_name_plural = _("业务配置")
        ordering = ("id",)

    @classmethod
    def get_setting_value(cls, bk_biz_id: int, key: str, default: Optional[Any] = None) -> Union[str, Dict]:
        return super().get_setting_value(key={"key": key, "bk_biz_id": bk_biz_id}, default=default)

    @classmethod
    def insert_setting_value(cls, bk_biz_id: int, key: str, value: Any, value_type: str = "str", user: str = "admin"):
        return super().insert_setting_value(
            key={"key": key, "bk_biz_id": bk_biz_id},
            value=value,
            value_type=value_type,
            user=user,
            desc=constants.BizSettingsEnum.get_choice_label(key),
        )
