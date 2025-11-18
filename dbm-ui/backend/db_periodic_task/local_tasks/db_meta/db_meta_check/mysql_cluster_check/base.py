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

    更新逻辑：
    1. 以集群为单位查询最近的记录（不按 affinity_type 过滤）
    2. 如果查询不到记录，创建新记录
    3. 如果查询到记录，更新记录（包括 affinity_type、msg、state 等）

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

    # 以集群为单位查找最近的记录（不按 affinity_type 过滤）
    last_record = (
        AffinityCheckReport.objects.filter(
            cluster_id=cluster.id,
            cluster=cluster.immute_domain,
            create_at__gte=loopback_time,
        )
        .order_by("-update_at")
        .first()
    )

    current_time = timezone.now()

    # 如果查询不到记录，创建新记录
    if not last_record:
        failed_days = 1 if state != ReportStateType.NORMAL.value else 0
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
            create_at=current_time,
            update_at=current_time,
        )
        logger.info(_("亲和性检查: 创建集群 {} 的报告 - 状态={}, 失败天数={}").format(cluster.immute_domain, state, failed_days))
        return report

    # 如果查询到记录，更新记录
    # 计算 failed_days
    if state == ReportStateType.NORMAL.value:
        # 如果当前是正常状态，failed_days 必须置为 0
        failed_days = 0
        # 检查是否从不正常变成正常
        if last_record.state != ReportStateType.NORMAL.value:
            # 集群从不正常恢复为正常，重置失败天数
            msg = _("集群 {} 状态从不正常恢复为正常，重置失败天数（原失败天数: {}）").format(cluster.immute_domain, last_record.failed_days)
            logger.info(msg)
    else:
        # 如果当前是异常状态
        if last_record.state != ReportStateType.NORMAL.value:
            # 上一条也是异常，累加 failed_days
            failed_days = last_record.failed_days + 1
        else:
            # 上一条是正常，重新开始计数
            failed_days = 1

    # 更新记录
    last_record.affinity_type = affinity_type
    last_record.state = state
    last_record.status = state == ReportStateType.NORMAL.value  # True=正常, False=异常
    # 追加消息而不是覆盖
    if last_record.msg and last_record.msg != msg:
        last_record.msg = f"{last_record.msg}\n{msg}"
    else:
        last_record.msg = msg
    last_record.failed_days = failed_days
    last_record.create_at = current_time
    last_record.update_at = current_time
    last_record.save(
        update_fields=["affinity_type", "state", "status", "msg", "failed_days", "create_at", "update_at"]
    )

    logger.info(_("亲和性检查: 更新集群 {} 的报告 - 状态={}, 失败天数={}").format(cluster.immute_domain, state, failed_days))

    return last_record


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

    query = AffinityCheckReport.objects.filter(update_at__lt=cutoff_date)

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
