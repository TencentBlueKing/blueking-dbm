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
from typing import Optional

from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from backend.db_meta.models import Cluster
from backend.db_report.enums import MetaCheckSubType, ReportStateType
from backend.db_report.models import MetaCheckReport

logger = logging.getLogger("root")


def is_cluster_labeled_with(cluster: Cluster, label: dict) -> bool:
    """
    Check if cluster has the specified label
    """
    if not label:
        return True

    cluster_tags = {tag.key: tag.value for tag in cluster.tags.all()}
    for key, value in label.items():
        if cluster_tags.get(key) != value:
            return False

    return True


def calculate_failed_days(cluster_domain: str, ip: str, port: int, subtype: str, current_state: str) -> int:
    """
    Calculate consecutive failed days based on historical records

    Args:
        cluster_domain: Cluster domain name
        ip: Instance IP address
        port: Instance port
        subtype: Meta check subtype
        current_state: Current state (NORMAL/WARNING/ABNORMAL)

    Returns:
        Number of consecutive failed days
    """
    if current_state == ReportStateType.NORMAL.value:
        return 0

    # Look back 25 hours to find yesterday's record
    lookback_time = timezone.now() - timedelta(hours=25)

    last_record = (
        MetaCheckReport.objects.filter(
            cluster=cluster_domain, ip=ip, port=port, subtype=subtype, create_at__gte=lookback_time
        )
        .order_by("-create_at")
        .first()
    )

    if last_record and last_record.state != ReportStateType.NORMAL.value:
        return last_record.failed_days + 1
    else:
        return 1


def create_meta_check_report(
    cluster: Cluster,
    ip: str,
    port: Optional[int],
    subtype: MetaCheckSubType,
    msg: str,
    state: ReportStateType,
    machine_type: str = "",
    creator: str = "dba",
) -> MetaCheckReport:
    """
    Create a meta check report with state and failed_days support

    Args:
        cluster: Cluster object
        ip: Instance IP
        port: Instance port (null for cluster-level reports)
        subtype: Meta check subtype
        msg: Report message
        state: Report state (NORMAL/WARNING/ABNORMAL)
        status: Legacy status field (True=pass, False=fail)
        instance: Optional StorageInstance object (avoids DB query if provided)

    Returns:
        Created MetaCheckReport object
    """
    # Calculate failed days
    failed_days = calculate_failed_days(
        cluster_domain=cluster.immute_domain, ip=ip, port=port, subtype=subtype, current_state=state
    )

    # Create report
    report = MetaCheckReport.objects.create(
        bk_biz_id=cluster.bk_biz_id,
        bk_cloud_id=cluster.bk_cloud_id,
        ip=ip,
        port=port,
        cluster=cluster.immute_domain,
        cluster_type=cluster.cluster_type,
        state=state,
        msg=msg,
        subtype=subtype,
        failed_days=failed_days,
        machine_type=machine_type,
        creator=creator,
    )

    logger.info(
        _(
            "meta_check: created {} check report for {} {}:{} - state={}, failed_days={}, machine_type={}, creator={}".format(
                subtype, cluster.immute_domain, ip, port, state, failed_days, machine_type, creator
            )
        )
    )

    return report


def delete_old_meta_check_reports(
    report_sub_type: MetaCheckSubType, cluster_types: list = None, days: int = 30
) -> int:
    """
    Delete MetaCheckReport records older than specified days for specific cluster types

    Args:
        report_sub_type: The subtype of meta check report to delete
        cluster_types: List of cluster types to filter (if None, delete all types)
        days: Number of days to keep (default: 30)

    Returns:
        Number of deleted records
    """
    cutoff_date = timezone.now() - timedelta(days=days)

    query = MetaCheckReport.objects.filter(subtype=report_sub_type, create_at__lt=cutoff_date)

    # Filter by cluster types if provided
    if cluster_types:
        query = query.filter(cluster_type__in=cluster_types)

    deleted_count, _d = query.delete()

    logger.info(
        _("meta_check: deleted {} old records (older than {} days) for cluster_types={}").format(
            deleted_count, days, cluster_types if cluster_types else "all"
        )
    )

    return deleted_count
