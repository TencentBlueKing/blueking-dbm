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
from django.db import models
from django.utils.translation import gettext_lazy as _

from backend.bk_web.models import AuditedModel
from backend.db_meta.enums import StateStorageType


class ClusterState(AuditedModel):
    """
    集群状态竖表，只存放没有已有实体的状态（Stored 字段）。
    稀疏存储：字段声明了默认值时，没有行即表示默认值。
    """

    # 不使用外键，避免级联删除；集群下架时显式清理，另有兜底任务清理孤儿行
    cluster_id = models.IntegerField(help_text=_("集群ID"))
    state_key = models.CharField(max_length=64, help_text=_("状态字段key"))
    state_value_type = models.CharField(
        max_length=16, choices=StateStorageType.get_choices(), help_text=_("底层存储类型: str/int")
    )
    state_str_value = models.CharField(max_length=256, null=True, blank=True, help_text=_("字符串值"))
    state_int_value = models.BigIntegerField(null=True, blank=True, help_text=_("整数值"))
    extra = models.JSONField(default=dict, help_text=_("扩展信息，结构由字段的 extra_class 声明"))

    class Meta:
        verbose_name = verbose_name_plural = _("集群状态(ClusterState)")
        unique_together = ("cluster_id", "state_key")
        indexes = [
            models.Index(fields=["state_key", "state_str_value"]),
            models.Index(fields=["state_key", "state_int_value"]),
        ]

    def __str__(self):
        return f"{self.cluster_id}:{self.state_key}"
