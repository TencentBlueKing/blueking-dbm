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
from django.utils.translation import ugettext_lazy as _

from backend.utils.time import datetime2str


class TendisplusLightningTask(models.Model):
    task_id = models.CharField(_("任务ID"), max_length=64, primary_key=True)
    ticket_id = models.BigIntegerField(_("单据ID"))
    user = models.CharField(_("申请人"), max_length=64, default="")
    bk_biz_id = models.CharField(_("业务bk_biz_d"), max_length=64, default="")
    bk_cloud_id = models.BigIntegerField(_("云区域ID"), default=0)
    cos_key = models.CharField(_("cos文件key"), max_length=128, default="")
    cos_file_size = models.BigIntegerField(_("cos文件大小"), default=0)
    dts_server = models.CharField(_("dts服务地址"), max_length=128, default="")
    dst_cluster = models.CharField(_("目标集群"), max_length=128, default="")
    dst_cluster_id = models.BigIntegerField(_("目标集群ID"), default=0)
    dst_cluster_priority = models.IntegerField(_("目标集群优先级,越大优先级越高"), default=0)
    dst_zonename = models.CharField(_("目标集群城市"), max_length=128, default="")
    task_type = models.CharField(_("任务类型"), max_length=128, default="")
    operate_type = models.CharField(_("操作类型"), max_length=128, default="")
    status = models.IntegerField(_("任务状态"), default=0)
    message = models.TextField(_("任务消息"), default="")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name=_("创建时间"))
    update_time = models.DateTimeField(auto_now=True, verbose_name=_("更新时间"))

    class Meta:
        verbose_name = _("Tendisplus Lightning Task")
        verbose_name_plural = _("Tendisplus Lightning Task")
        db_table = "tb_tendisplus_lightning_task"
        indexes = [
            models.Index(fields=["update_time"]),
            models.Index(fields=["dst_cluster_id"]),
            models.Index(fields=["user"]),
            models.Index(fields=["ticket_id", "dst_cluster_id"]),
        ]


def lightning_task_format_time(json_data: dict, row: TendisplusLightningTask):
    json_data["create_time"] = datetime2str(row.create_time)
    json_data["update_time"] = datetime2str(row.update_time)
