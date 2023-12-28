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
from collections import defaultdict
from typing import Dict, List

from django.db import models
from django.forms import model_to_dict
from django.utils.translation import ugettext_lazy as _

from backend import env
from backend.bk_web.models import AuditedModel
from backend.db_meta.enums import ClusterEntryRole, ClusterEntryType
from backend.db_meta.models import Cluster

logger = logging.getLogger("root")


class ClusterEntry(AuditedModel):
    """
    集群访问入口
    1. 从 Cluster 中独立出来
    2. 这样支持多个访问入口比较方便
    3. CLB从辨识度和后期的运营来说都不如DNS好, 因此需要引入: DNS--->CLB--->proxies
    """

    cluster = models.ForeignKey(Cluster, on_delete=models.PROTECT)
    cluster_entry_type = models.CharField(max_length=64, choices=ClusterEntryType.get_choices(), default="")
    entry = models.CharField(max_length=200, unique=True, default="")

    forward_to = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="forward_from",
        related_query_name="forward_from",
        blank=True,
        null=True,
        default=None,
    )
    role = models.CharField(
        max_length=64, choices=ClusterEntryRole.get_choices(), default=ClusterEntryRole.MASTER_ENTRY.value
    )

    class Meta:
        unique_together = ("cluster_entry_type", "entry")
        verbose_name = verbose_name_plural = _("集群访问入口(ClusterEntry)")

    @classmethod
    def get_cluster_entry_map(cls, cluster_ids: List[int]) -> Dict[int, Dict[str, str]]:
        """
        返回格式如：
        {
            1: {
                "master_domain": "gamedb.db",
                "slave_domain": "gamedr.db"
                "clb": "gameclb.db"
            }
        }
        ToDo ClusterEntry 添加了专门的角色信息, 这里的逻辑可以简化掉了
        """
        cluster_entry_map = defaultdict(dict)
        for entry in cls.objects.filter(cluster_id__in=cluster_ids).select_related("cluster"):
            access_entry = entry.entry
            # 这里假设非DNS只有一个入口，无需额外区分
            if entry.cluster_entry_type != ClusterEntryType.DNS:
                cluster_entry_map[entry.cluster_id][entry.cluster_entry_type] = access_entry
                continue

            # DNS 需额外区分主域名和从域名， entry 中 cluster.immute_domain 为主域名
            # 那么不等于 cluster.immute_domain 的则理解为是从域名
            if access_entry == entry.cluster.immute_domain:
                cluster_entry_map[entry.cluster_id]["master_domain"] = access_entry
            else:
                cluster_entry_map[entry.cluster_id]["slave_domain"] = access_entry
        return cluster_entry_map

    @property
    def detail(self):
        """入口详情"""

        if self.cluster_entry_type == ClusterEntryType.CLB:
            detail_obj = self.clbentrydetail_set.first()
            # 补充clb域名
            clb_dns = ClusterEntry.objects.filter(forward_to=self, cluster_entry_type=ClusterEntryType.CLBDNS).first()
            return {**model_to_dict(detail_obj), **{"clb_domain": getattr(clb_dns, "entry", "")}} if detail_obj else {}

        if self.cluster_entry_type == ClusterEntryType.POLARIS:
            detail_obj = self.polarisentrydetail_set.first()
            return {**model_to_dict(detail_obj), **{"url": getattr(detail_obj, "url", "")}} if detail_obj else {}

        if self.cluster_entry_type == ClusterEntryType.CLBDNS:
            detail_obj = self.forward_to
            return model_to_dict(detail_obj) if detail_obj else {}

        return {}

    def __str__(self):
        return "{}:{}".format(self.cluster_entry_type, self.entry)


class CLBEntryDetail(AuditedModel):
    """
    存储 CLB 管理所需 关键参数
    """

    entry = models.ForeignKey(
        ClusterEntry,
        on_delete=models.CASCADE,
    )
    clb_ip = models.CharField(default="", max_length=30, unique=True)
    clb_id = models.CharField(default="", max_length=30)
    listener_id = models.CharField(default="", max_length=30)
    clb_region = models.CharField(default="", max_length=50)

    @property
    def url(self):
        return ""

    def __str__(self):
        return "{}".format(self.clb_ip)


class PolarisEntryDetail(AuditedModel):
    """
    存储 Polaris 管理所需 关键参数
    """

    entry = models.ForeignKey(
        ClusterEntry,
        on_delete=models.CASCADE,
    )
    polaris_name = models.CharField(default="", max_length=50, unique=True)
    polaris_l5 = models.CharField(default="", max_length=30)
    polaris_token = models.CharField(default="", max_length=50)
    alias_token = models.CharField(default="", max_length=50)

    @property
    def url(self):
        return f"{env.NAMESERVICE_POLARIS_DOMAIN}/#/services/alias?alias={self.polaris_l5}"

    def __str__(self):
        return "{}".format(self.polaris_name)
