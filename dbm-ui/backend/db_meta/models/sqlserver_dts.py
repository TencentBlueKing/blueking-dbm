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
from datetime import datetime

from django.db import models
from django.utils.translation import ugettext_lazy as _

from backend.bk_web.models import AuditedModel
from backend.flow.consts import SqlserverDtsMode
from blue_krill.data_types.enum import EnumField, StructuredEnum

logger = logging.getLogger("root")


class DtsStatus(str, StructuredEnum):
    # 迁移记录的状态枚举
    ToDo = EnumField("todo", _("待执行"))
    Terminated = EnumField("terminated", _("已终止"))
    Disconnecting = EnumField("disconnecting", _("中断中"))
    Disconnected = EnumField("disconnected", _("已断开"))

    # 全量迁移阶段状态枚举
    FullOnline = EnumField("full_online", _("全量传输中"))
    FullFailed = EnumField("full_failed", _("全量传输失败"))
    FullSuccess = EnumField("full_success", _("全量传输完成"))

    # 增量迁移阶段状态枚举
    IncrOnline = EnumField("incr_online", _("增量传输中"))
    IncrFailed = EnumField("incr_failed", _("增量传输失败"))
    IncrSuccess = EnumField("incr_success", _("增量传输完成"))


class SqlserverDtsInfo(AuditedModel):
    """
    定义sqlserver数据迁移记录表，存储sqlserver生成每一条数据迁移记录信息
    sqlserver专属
    """

    bk_biz_id = models.IntegerField(default=0, help_text=_("关联的业务id，对应cmdb"))
    source_cluster_id = models.IntegerField(default=0, help_text=_("源集群ID"))
    target_cluster_id = models.IntegerField(default=0, help_text=_("目标集群ID"))
    db_list = models.JSONField(default=list, blank=True, null=True, help_text=_("库正则"))
    ignore_db_list = models.JSONField(default=list, blank=True, null=True, help_text=_("忽略库正则"))
    dts_mode = models.CharField(max_length=64, choices=SqlserverDtsMode.get_choices(), help_text=_("迁移类型"))
    ticket_id = models.PositiveIntegerField(default=0, help_text=_("关联的单据id"))
    root_id = models.CharField(max_length=64, default="", help_text=_("关联root_id"))
    status = models.CharField(
        max_length=64, choices=DtsStatus.get_choices(), default=DtsStatus.ToDo, help_text=_("状态")
    )
    dts_config = models.JSONField(default=dict, help_text=_("迁移配置"))

    class Meta:
        verbose_name = verbose_name_plural = _("sqlserver数据迁移记录表")
        # 单据ID-源集群-目标集群组成唯一键
        unique_together = (
            "ticket_id",
            "source_cluster_id",
            "target_cluster_id",
        )

    def to_dict(self):
        """重写model_to_dict()方法转字典"""

        opts = self._meta
        data = {}
        for f in opts.concrete_fields:
            value = f.value_from_object(self)
            if isinstance(value, datetime):
                value = value.strftime("%Y-%m-%d %H:%M:%S")
            elif isinstance(f, models.FileField):
                value = value.url if value else None
            data[f.name] = value
        return data
