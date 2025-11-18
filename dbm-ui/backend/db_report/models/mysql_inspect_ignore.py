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

from backend.db_meta.enums import ClusterType


class MysqlInspectIgnore(models.Model):
    """MySQL备份巡检忽略配置表"""

    bk_biz_id = models.IntegerField(help_text=_("业务的id"))
    cluster_type = models.CharField(max_length=64, choices=ClusterType.get_choices(), default="")
    cluster = models.CharField(max_length=255, help_text=_("集群域名"))
    subtype = models.CharField(max_length=64, help_text=_("忽略的巡检类型"))
    reason = models.TextField(default="", help_text=_("忽略原因"))
    is_enabled = models.BooleanField(default=True, help_text=_("是否启用"))

    class Meta:
        managed = True
        app_label = "db_report"
        db_table = "tb_mysql_inspect_ignore"
        verbose_name = _("巡检忽略配置")
        verbose_name_plural = _("巡检忽略配置")
        # 添加唯一索引，确保同一个集群的同一个巡检类型只能有一条配置
        unique_together = ["cluster", "bk_biz_id", "subtype"]
        index_together = ["subtype", "cluster_type"]

    def __str__(self):
        return f"{self.bk_biz_id}-{self.cluster}-{self.subtype}"
