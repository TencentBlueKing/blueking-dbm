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


class TendisplusLightningJob(models.Model):
    id = models.BigAutoField(_("ID"), primary_key=True)
    ticket_id = models.BigIntegerField(_("单据ID"), default=0)
    user = models.CharField(_("申请人"), max_length=64, default="")
    bk_biz_id = models.CharField(_("业务bk_biz_d"), max_length=64, default="")
    bk_cloud_id = models.BigIntegerField(_("云区域ID"), default=0)
    dst_cluster = models.CharField(_("目标集群"), max_length=128, default="")
    dst_cluster_id = models.BigIntegerField(_("目标集群ID"), default=0)
    cluster_nodes = models.TextField(_("集群节点"), default="")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name=_("创建时间"))

    class Meta:
        verbose_name = _("Tendisplus Lightning Job")
        verbose_name_plural = _("Tendisplus Lightning Job")
        db_table = "tb_tendisplus_lightning_job"

        indexes = [
            models.Index(fields=["create_time"]),
            models.Index(fields=["dst_cluster_id"]),
            models.Index(fields=["user"]),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["ticket_id", "dst_cluster"],
                name="uniq_ticket_cluster",
            )
        ]
