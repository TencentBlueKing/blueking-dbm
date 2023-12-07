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
import urllib

from django.db import models
from django.utils.translation import gettext_lazy as _

from backend import env
from backend.bk_web.constants import LEN_LONG, LEN_MIDDLE, LEN_NORMAL
from backend.bk_web.models import AuditedModel
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import AppCache, Cluster

__all__ = ["Dashboard"]


class Dashboard(AuditedModel):
    """仪表盘"""

    name = models.CharField(verbose_name=_("名称"), max_length=LEN_MIDDLE, default="")
    view = models.CharField(verbose_name=_("视图类型"), max_length=LEN_MIDDLE, default=_("集群监控视图"))

    cluster_type = models.CharField(max_length=64, choices=ClusterType.get_choices(), default="")

    details = models.JSONField(verbose_name=_("详情"), default=dict)
    variables = models.JSONField(verbose_name=_("变量"), default=dict)

    # grafana相关
    org_id = models.BigIntegerField(verbose_name=_("grafana-org_id"))
    org_name = models.CharField(verbose_name=_("grafana-org_name"), max_length=LEN_NORMAL)
    uid = models.CharField(verbose_name=_("grafana-uid"), max_length=LEN_NORMAL)
    url = models.CharField(verbose_name=_("grafana-url"), max_length=LEN_LONG)

    class Meta:
        verbose_name = _("仪表盘")
        unique_together = (("name", "view"),)

    def get_url(self, bk_biz_id, cluster_id, view=None):
        from backend.bk_dataview.grafana.constants import DEFAULT_ORG_ID, DEFAULT_ORG_NAME

        cluster = Cluster.objects.filter(id=cluster_id).last()

        params = {
            "orgId": DEFAULT_ORG_ID,
            "orgName": DEFAULT_ORG_NAME,
            "var-cluster_domain": getattr(cluster, "immute_domain", None),
            "var-cluster_name": getattr(cluster, "name", None),
            # "var-instance": getattr(instance, "ip_port", None),
            # "var-host": getattr(getattr(instance, "machine", None), "ip", None),
            "var-app_id": bk_biz_id,
            "var-appid": bk_biz_id,
            "var-app": AppCache.get_app_attr(bk_biz_id, default=bk_biz_id),
            # "kiosk": 1,
        }

        return env.BK_SAAS_HOST + f"{self.url}?" + urllib.parse.urlencode(params)
