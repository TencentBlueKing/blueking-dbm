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
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Optional, Set

from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from backend.configuration.constants import SystemSettingsEnum
from backend.configuration.models import SystemSettings
from backend.db_meta.models import Cluster
from backend.db_report.enums import MetaCheckSubType, ReportStateType
from backend.db_report.enums.redis_sub_type import RedisCheckSubType
from backend.db_report.models import MetaCheckReport
from backend.db_report.models.redis_check_report import RedisCheckReport

logger = logging.getLogger("root")

REDIS_REPORT_MODE_ADD = "add"
REDIS_REPORT_MODE_UPSERT = "upsert"
REDIS_REPORT_MODE_SET = {REDIS_REPORT_MODE_ADD, REDIS_REPORT_MODE_UPSERT}
REDIS_REPORT_DEFAULT_RETENTION_DAYS = 30


def _known_redis_report_subtypes() -> Set[str]:
    meta_subtypes = {choice[0] for choice in MetaCheckSubType.get_choices()}
    redis_subtypes = {choice[0] for choice in RedisCheckSubType.get_choices()}
    return meta_subtypes | redis_subtypes


def _parse_mode_subtype_set(
    raw_set: Any,
    *,
    mode_name: str,
    known_subtypes: Set[str],
) -> Set[str]:
    if raw_set is None:
        return set()
    if not isinstance(raw_set, list):
        logger.warning("redis_report_mode: %s must be list, got %s", mode_name, type(raw_set).__name__)
        return set()

    valid_subtypes = set()
    invalid_subtypes = set()
    for subtype in raw_set:
        subtype = str(subtype).strip()
        if subtype in known_subtypes:
            valid_subtypes.add(subtype)
        else:
            invalid_subtypes.add(subtype)

    if invalid_subtypes:
        logger.warning(
            "redis_report_mode: invalid subtypes for %s ignored: %s",
            mode_name,
            sorted(invalid_subtypes),
        )
    return valid_subtypes


@dataclass
class RedisReportModeConfig:
    default_mode: str = REDIS_REPORT_MODE_ADD
    upsert_subtypes: Set[str] = field(default_factory=set)
    add_subtypes: Set[str] = field(default_factory=set)
    retention_days: int = REDIS_REPORT_DEFAULT_RETENTION_DAYS

    @classmethod
    def from_settings(cls) -> "RedisReportModeConfig":
        raw_config = SystemSettings.get_setting_value(SystemSettingsEnum.REDIS_REPORT_ADDING_MODE.value, default={})
        if not isinstance(raw_config, dict):
            if raw_config is not None:
                logger.warning("redis_report_mode: config must be dict, got %s", type(raw_config).__name__)
            return cls()

        default_mode = str(raw_config.get("default_mode", REDIS_REPORT_MODE_ADD)).strip().lower()
        if default_mode not in REDIS_REPORT_MODE_SET:
            logger.warning(
                "redis_report_mode: invalid default_mode=%s, fallback to %s",
                default_mode,
                REDIS_REPORT_MODE_ADD,
            )
            default_mode = REDIS_REPORT_MODE_ADD

        known_subtypes = _known_redis_report_subtypes()
        upsert_subtypes = _parse_mode_subtype_set(
            raw_config.get("upsert", []), mode_name="upsert", known_subtypes=known_subtypes
        )
        add_subtypes = _parse_mode_subtype_set(
            raw_config.get("add", []), mode_name="add", known_subtypes=known_subtypes
        )

        overlap_subtypes = upsert_subtypes & add_subtypes
        if overlap_subtypes:
            logger.warning(
                "redis_report_mode: subtypes configured in both upsert and add; upsert wins for %s",
                sorted(overlap_subtypes),
            )

        retention_days = raw_config.get("retention_days", REDIS_REPORT_DEFAULT_RETENTION_DAYS)
        try:
            retention_days = int(retention_days)
        except (TypeError, ValueError):
            retention_days = REDIS_REPORT_DEFAULT_RETENTION_DAYS

        if retention_days < 1:
            logger.warning(
                "redis_report_mode: invalid retention_days=%s, fallback to %s",
                retention_days,
                REDIS_REPORT_DEFAULT_RETENTION_DAYS,
            )
            retention_days = REDIS_REPORT_DEFAULT_RETENTION_DAYS

        return cls(
            default_mode=default_mode,
            upsert_subtypes=upsert_subtypes,
            add_subtypes=add_subtypes,
            retention_days=retention_days,
        )


def _resolve_write_mode(subtype_value: str, mode_config: RedisReportModeConfig) -> str:
    """Pure function: resolve write mode for a given subtype using pre-loaded config."""
    if subtype_value in mode_config.upsert_subtypes:
        return REDIS_REPORT_MODE_UPSERT
    if subtype_value in mode_config.add_subtypes:
        return REDIS_REPORT_MODE_ADD
    return mode_config.default_mode


class RedisReportWriter:
    """Loads report-mode config once on init and exposes write methods that reuse it."""

    def __init__(self):
        self._mode_config = RedisReportModeConfig.from_settings()
        self.retention_days: int = self._mode_config.retention_days

    def write_meta_report(
        self,
        cluster: Cluster,
        ip: Optional[str],
        port: Optional[int],
        subtype: MetaCheckSubType,
        msg: str,
        state: ReportStateType,
        machine_type: str = "",
        creator: str = "dba",
    ) -> MetaCheckReport:
        subtype_value = getattr(subtype, "value", subtype)
        mode = _resolve_write_mode(subtype_value, self._mode_config)
        report = get_last_record(cluster.immute_domain, ip, port, subtype, state)
        failed_days = calculate_failed_days(state, report)

        if mode == REDIS_REPORT_MODE_ADD or not report:
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
        else:
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

    def write_redis_report(
        self,
        *,
        cluster_id: int,
        subtype: str,
        cluster: str,
        cluster_type: str,
        bk_biz_id: int,
        bk_cloud_id: int,
        report_day: int,
        creator: str,
        state: str,
        msg: str,
        shard: str = "",
        instance: str = "",
    ) -> RedisCheckReport:
        mode = _resolve_write_mode(subtype, self._mode_config)
        kwargs = dict(
            cluster_id=cluster_id,
            subtype=subtype,
            cluster=cluster,
            cluster_type=cluster_type,
            bk_biz_id=bk_biz_id,
            bk_cloud_id=bk_cloud_id,
            report_day=report_day,
            creator=creator,
            state=state,
            msg=msg,
            shard=shard,
            instance=instance,
        )
        if mode == REDIS_REPORT_MODE_UPSERT:
            return RedisCheckReport.upsert_by_cluster_subtype(**kwargs)
        return RedisCheckReport.create_by_cluster_subtype(**kwargs)


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
