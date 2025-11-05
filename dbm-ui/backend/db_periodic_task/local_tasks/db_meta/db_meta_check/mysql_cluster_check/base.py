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
from datetime import timedelta
from typing import Set

from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.utils.translation import gettext as _

from backend.db_meta.models import BKCity, Cluster, LogicalCity
from backend.db_report.enums import ReportStateType
from backend.db_report.models import AffinityCheckReport

logger = logging.getLogger("root")


def get_cluster_expected_city_ids(cluster: Cluster) -> Set[int]:
    """
    根据集群的 region 获取期望的 bk_idc_city_id 集合

    Args:
        cluster: 集群对象

    Returns:
        set: 该集群 region 对应的所有 bk_idc_city_id 集合

    Raises:
        LogicalCity.DoesNotExist: 如果 region 对应的逻辑城市不存在
    """
    try:
        # cluster.region → LogicalCity.name
        logical_city = LogicalCity.objects.get(name=cluster.region)
        # LogicalCity → BKCity.bk_idc_city_id
        expected_city_ids = set(
            BKCity.objects.filter(logical_city=logical_city).values_list("bk_idc_city_id", flat=True)
        )
        return expected_city_ids
    except ObjectDoesNotExist:
        logger.warning(_("集群 {} 的 region '{}' 在 LogicalCity 表中不存在").format(cluster.immute_domain, cluster.region))
        return set()


def create_or_update_affinity_report(
    cluster: Cluster,
    affinity_type: str,
    msg: str,
    state: ReportStateType,
    creator: str = "admin",
) -> AffinityCheckReport:
    """
    创建或更新亲和性检查报告

    如果昨天的记录存在且错误信息相同，则只更新 failed_days，不创建新记录
    否则创建新记录

    Args:
        cluster: 集群对象
        affinity_type: 亲和性类型（CROS_SUBZONE/SAME_SUBZONE_CROSS_SWTICH/CROSS_RACK）
        msg: 检查消息
        state: 报告状态
        creator: 创建者

    Returns:
        AffinityCheckReport: 创建或更新的报告对象
    """
    loopback_time = timezone.now() - timedelta(hours=25)

    # 查找最近的记录
    last_record = (
        AffinityCheckReport.objects.filter(
            cluster_id=cluster.id,
            cluster=cluster.immute_domain,
            affinity_type=affinity_type,
            create_at__gte=loopback_time,
        )
        .order_by("-create_at")
        .first()
    )

    # 如果找到记录且错误信息和状态都相同
    if last_record and last_record.msg == msg and last_record.state == state:
        # 如果是异常状态，累加 failed_days
        if state != ReportStateType.NORMAL.value:
            last_record.failed_days += 1
            last_record.update_at = timezone.now()
            last_record.save(update_fields=["failed_days", "update_at"])
            logger.info(_("亲和性检查: 更新集群 {} 的报告，失败天数: {}").format(cluster.immute_domain, last_record.failed_days))
            return last_record
        else:
            # 如果是正常状态，保持 failed_days=0，更新时间即可
            last_record.update_at = timezone.now()
            last_record.save(update_fields=["update_at"])
            logger.info(_("亲和性检查: 集群 {} 保持正常状态").format(cluster.immute_domain))
            return last_record

    # 否则创建新记录（状态变化或消息变化）
    failed_days = 0
    if state != ReportStateType.NORMAL.value:
        # 如果当前是异常状态
        if last_record and last_record.state != ReportStateType.NORMAL.value:
            # 上一条也是异常，累加 failed_days
            failed_days = last_record.failed_days + 1
        else:
            # 上一条是正常或不存在，重新开始计数
            failed_days = 1
    # 如果当前是正常状态，failed_days = 0（已在上面初始化）

    report = AffinityCheckReport.objects.create(
        bk_biz_id=cluster.bk_biz_id,
        bk_cloud_id=cluster.bk_cloud_id,
        cluster_id=cluster.id,
        cluster=cluster.immute_domain,
        cluster_type=cluster.cluster_type,
        region=cluster.region,
        affinity_type=affinity_type,
        state=state,
        status=(state == ReportStateType.NORMAL.value),  # True=正常, False=异常
        msg=msg,
        failed_days=failed_days,
        creator=creator,
    )

    logger.info(_("亲和性检查: 创建集群 {} 的报告 - 状态={}, 失败天数={}").format(cluster.immute_domain, state, failed_days))

    return report


def delete_old_affinity_reports(cluster_types: list = None, days: int = 30) -> int:
    """
    删除指定天数之前的亲和性检查报告

    Args:
        cluster_types: 集群类型列表（如果为None，删除所有类型）
        days: 保留天数（默认30天）

    Returns:
        int: 删除的记录数
    """
    cutoff_date = timezone.now() - timedelta(days=days)

    query = AffinityCheckReport.objects.filter(create_at__lt=cutoff_date)

    # 按集群类型过滤
    if cluster_types:
        query = query.filter(cluster_type__in=cluster_types)

    deleted_count, deleted_details = query.delete()

    logger.info(
        _("亲和性检查: 删除了 {} 条旧记录（超过 {} 天），集群类型={}").format(
            deleted_count, days, cluster_types if cluster_types else _("全部")
        )
    )

    return deleted_count
