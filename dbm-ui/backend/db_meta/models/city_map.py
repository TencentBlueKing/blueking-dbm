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
from typing import Iterable, Optional

from django.db import models
from django.utils.translation import gettext_lazy as _

from backend.bk_web.models import AuditedModel
from backend.utils.cache import func_cache_decorator

logger = logging.getLogger("root")

# 部署时地域选「随机」时，集群和单据里存的哨兵值。它不是真实地域，
# 需要云地域的场景（CLB、计费、巡检调云 API）必须先把它过滤掉。
RANDOM_REGION = "default"


# 1. 提供机器城市到逻辑城市的映射, 如机器的城市属性是扬州的, 实际当作南京看待
# 2. 两类城市需要预先人工注册
class LogicalCity(AuditedModel):
    """
    逻辑上的城市
    """

    name = models.CharField(max_length=128, unique=True, default="")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = verbose_name_plural = _("逻辑城市表(LogicalCity)")


class BKCity(AuditedModel):
    """
    机器实际的城市
    """

    bk_idc_city_id = models.IntegerField(primary_key=True, default=0)
    bk_idc_city_name = models.CharField(max_length=128, unique=True, default="", help_text=_("IDC 城市名"))
    logical_city = models.ForeignKey(LogicalCity, on_delete=models.PROTECT)

    def __str__(self):
        return self.bk_idc_city_name

    class Meta:
        verbose_name = verbose_name_plural = _("蓝鲸城市表(BKCity)")


class BKSubzone(AuditedModel):
    """
    机器实际的园区
    """

    bk_sub_zone = models.CharField(max_length=128, default="", blank=True, null=True, help_text=_("子 Zone"))
    bk_sub_zone_id = models.IntegerField(default=0, help_text=_("子 Zone ID"))
    bk_city = models.ForeignKey(BKCity, on_delete=models.PROTECT)
    bk_cloud_region = models.CharField(max_length=128, default="", blank=True, null=True, help_text=_("云地域"))
    bk_cloud_zone = models.CharField(max_length=128, default="", blank=True, null=True, help_text=_("云可用区"))

    def __str__(self):
        return self.bk_sub_zone

    class Meta:
        verbose_name = verbose_name_plural = _("蓝鲸园区表(BKSubzone)")

    @classmethod
    @func_cache_decorator(cache_time=60 * 60 * 24)
    def get_subzone_map(cls):
        return {subzone.bk_sub_zone_id: subzone.bk_sub_zone for subzone in cls.objects.all()}


def resolve_cloud_region(cloud_zones: Optional[Iterable[str]] = None) -> str:
    """由云可用区推出云地域（region）"""
    zones = [zone for zone in (cloud_zones or []) if zone]
    if zones:
        regions = set(
            BKSubzone.objects.filter(bk_cloud_zone__in=zones)
            .exclude(bk_cloud_region__isnull=True)
            .exclude(bk_cloud_region="")
            .values_list("bk_cloud_region", flat=True)
        )
        if len(regions) == 1:
            return regions.pop()
        if len(regions) > 1:
            logger.error("cloud zones %s belong to multiple regions %s", zones, sorted(regions))

    return ""


def resolve_logical_city(cluster) -> str:
    """集群所在的逻辑城

    `Cluster.region` 存的是部署时选的逻辑城，字段即将下线，这里统一从实例机器反查：
    机器 -> bk_city（IDC 城市）-> logical_city。

    只在资源申请这类「需要给 v1 传 city」的场景使用，v2 用不到（它只要云地域）。
    集群还没有实例（新建 / 录入中）时返回空串，由调用方决定是否退化成「不限城市」。
    """
    if not getattr(cluster, "id", None):
        return ""
    instance_set = getattr(cluster, "storageinstance_set", None)
    if instance_set is None:
        return ""
    return instance_set.values_list("machine__bk_city__logical_city__name", flat=True).first() or ""


def resolve_cloud_region_by_city(city: str) -> str:
    """由城市反推云地域

    城市（逻辑城或 IDC 城市）挂在地域下面，和可用区没有上下级关系，
    所以只能在这个城市登记过的园区里找唯一的地域；找到多个就说明有歧义，返回空串。
    给「只有城市、没有可用区」的老单据兜底，比如大数据组件的部署流程。
    """
    city = (city or "").strip()
    # default 是「地域随机」的哨兵值，不是真实城市，查库也查不到，直接返回避免无谓查询
    if not city or city == "default":
        return ""
    regions = set(
        BKSubzone.objects.filter(bk_city__bk_idc_city_name=city)
        .exclude(bk_cloud_region__isnull=True)
        .exclude(bk_cloud_region="")
        .values_list("bk_cloud_region", flat=True)
    )
    if not regions:
        regions = set(
            BKSubzone.objects.filter(bk_city__logical_city__name=city)
            .exclude(bk_cloud_region__isnull=True)
            .exclude(bk_cloud_region="")
            .values_list("bk_cloud_region", flat=True)
        )
    if len(regions) == 1:
        return regions.pop()
    if len(regions) > 1:
        logger.error("city %s belongs to multiple cloud regions %s", city, sorted(regions))
    return ""


def is_unknown_cloud_region(region: Optional[str]) -> bool:
    """地域值是否「没有真实地域」

    空串（老数据没填）和 ``default``（部署时选了随机）都算没有真实地域。
    需要真实地域才能工作的场景（创建 CLB、调云 API、计费）必须先过这一层，
    否则会把哨兵值当成真实地域下发。
    """
    text = str(region or "").strip()
    return not text or text == RANDOM_REGION


def resolve_apply_region(source: dict) -> str:
    """集群注册 / 资源申请用的云地域

    优先用上游显式传的 ``bk_cloud_region``（部署时地域选「随机」会传 default）。
    存量单据还没有这个字段，先按可用区反推，再退化到按城市反推；都推不出来返回空串。
    """
    source = source or {}
    region = str(source.get("bk_cloud_region") or "").strip()
    if region:
        return region
    zones = source.get("cloud_zone_list") or source.get("zone_list") or []
    region = resolve_cloud_region(zones)
    if region:
        return region
    # 老单据只有逻辑城 / 城市编码，用它反推唯一地域
    return resolve_cloud_region_by_city(source.get("city") or source.get("city_code") or "")
