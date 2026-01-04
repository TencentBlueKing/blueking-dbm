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


def get_last_record(
    cluster_domain: str,
    ip: str,
    port: int,
    subtype: str,
    current_state: str,
    lookback_hours: int = 36,  # half-day redundancy
) -> Optional[MetaCheckReport]:
    """
    Get the last meta check report record within the lookback period
    """
    lookback_time = timezone.now() - timedelta(hours=lookback_hours)

    last_record = (
        MetaCheckReport.objects.filter(
            cluster=cluster_domain,
            ip=ip,
            port=port,
            subtype=subtype,
            create_at__gte=lookback_time,
            state=current_state,
        )
        .order_by("-create_at")
        .first()
    )

    return last_record


def calculate_failed_days(current_state: str, last_record: Optional[MetaCheckReport]) -> int:
    """
    Calculate consecutive failed days based on current state and last record
    """
    if current_state == ReportStateType.NORMAL.value:
        return 0

    if last_record:
        return last_record.failed_days + 1

    return 1


def create_meta_check_report(
    cluster: Cluster,
    ip: Optional[str],
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
        machine_type: Machine type string
        creator: Creator name

    Returns:
        Created MetaCheckReport object
    """
    report = get_last_record(cluster.immute_domain, ip, port, subtype, state)
    failed_days = calculate_failed_days(state, report)

    if not report:
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
    else:  # If there's existing record for the (domain, ip, port, subtype), we simply overwrite this record
        report.msg = msg
        report.state = state
        report.failed_days = failed_days
        report.create_at = timezone.now()
        report.save(update_fields=["msg", "state", "failed_days", "create_at", "update_at"])

    logger.info(
        _(
            "meta_check: {} check report for {} {}:{} - state={}, failed_days={}, machine_type={}, creator={}".format(
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
        _("meta_check: deleted {} old {} records (older than {} days) for cluster_types={}").format(
            deleted_count, report_sub_type, days, cluster_types if cluster_types else "all"
        )
    )

    return deleted_count
