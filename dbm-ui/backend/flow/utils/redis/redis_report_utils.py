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
from typing import Any, Dict, List, Optional, Set, Tuple

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
META_REPORT_WRITE_CHUNK = 500
META_CHECK_CLUSTER_PAGE_SIZE = 300
META_REPORT_LOOKBACK_HOURS = 36


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


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def _chunked(items: List, size: int):
    chunk_size = max(int(size or 1), 1)
    for start in range(0, len(items), chunk_size):
        yield items[start : start + chunk_size]


def _meta_report_lookup_key(
    cluster_domain: str,
    ip: Optional[str],
    port: Optional[int],
    subtype: Any,
    state: Any,
) -> Tuple[str, Optional[str], Optional[int], str, str]:
    return (cluster_domain, ip, port, _enum_value(subtype), _enum_value(state))


def _prefetch_meta_last_records(
    rows: List[Dict],
    *,
    lookback_hours: int = META_REPORT_LOOKBACK_HOURS,
) -> Dict[Tuple[str, Optional[str], Optional[int], str, str], MetaCheckReport]:
    if not rows:
        return {}

    cutoff = timezone.now() - timedelta(hours=lookback_hours)
    cluster_domains = sorted({row["cluster"].immute_domain for row in rows})
    subtypes = sorted({_enum_value(row["subtype"]) for row in rows})
    states = sorted({_enum_value(row["state"]) for row in rows})

    latest_by_key: Dict[Tuple[str, Optional[str], Optional[int], str, str], MetaCheckReport] = {}
    for domain_chunk in _chunked(cluster_domains, META_REPORT_WRITE_CHUNK):
        existing_rows = MetaCheckReport.objects.filter(
            cluster__in=domain_chunk,
            subtype__in=subtypes,
            state__in=states,
            create_at__gte=cutoff,
        ).order_by("cluster", "ip", "port", "subtype", "state", "-create_at")
        for existing in existing_rows:
            key = _meta_report_lookup_key(
                existing.cluster,
                existing.ip,
                existing.port,
                existing.subtype,
                existing.state,
            )
            latest_by_key.setdefault(key, existing)
    return latest_by_key


def _build_meta_report_instance(row: Dict, failed_days: int) -> MetaCheckReport:
    cluster = row["cluster"]
    now = timezone.now()
    state = _enum_value(row["state"])
    subtype = row["subtype"]
    creator = row.get("creator", "system")
    return MetaCheckReport(
        bk_biz_id=cluster.bk_biz_id,
        bk_cloud_id=cluster.bk_cloud_id,
        ip=row.get("ip"),
        port=row.get("port"),
        cluster=cluster.immute_domain,
        cluster_type=cluster.cluster_type,
        state=state,
        msg=row["msg"],
        subtype=subtype,
        failed_days=failed_days,
        machine_type=row.get("machine_type", ""),
        creator=creator,
        updater=creator,
        create_at=now,
        update_at=now,
    )


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
        creator: str = "system",
    ) -> MetaCheckReport:
        written = self.write_meta_reports(
            [
                {
                    "cluster": cluster,
                    "ip": ip,
                    "port": port,
                    "subtype": subtype,
                    "msg": msg,
                    "state": state,
                    "machine_type": machine_type,
                    "creator": creator,
                }
            ]
        )
        return written[0]

    def write_meta_reports(self, rows: List[Dict]) -> List[MetaCheckReport]:
        """Write multiple MetaCheckReport rows with batched prefetch and chunked DB writes."""
        if not rows:
            return []

        upsert_rows: List[Dict] = []
        add_rows: List[Dict] = []
        for row in rows:
            subtype_value = _enum_value(row["subtype"])
            mode = _resolve_write_mode(subtype_value, self._mode_config)
            if mode == REDIS_REPORT_MODE_UPSERT:
                upsert_rows.append(row)
            else:
                add_rows.append(row)

        written: List[MetaCheckReport] = []
        if upsert_rows:
            written.extend(self._write_meta_reports_upsert(upsert_rows))
        if add_rows:
            written.extend(self._write_meta_reports_add(add_rows))

        logger.info(
            "meta_check: wrote %d meta reports (upsert=%d, add=%d)",
            len(written),
            len(upsert_rows),
            len(add_rows),
        )
        return written

    def _write_meta_reports_add(self, rows: List[Dict]) -> List[MetaCheckReport]:
        latest_by_key = _prefetch_meta_last_records(rows)
        to_create: List[MetaCheckReport] = []
        for row in rows:
            cluster = row["cluster"]
            key = _meta_report_lookup_key(
                cluster.immute_domain,
                row.get("ip"),
                row.get("port"),
                row["subtype"],
                row["state"],
            )
            failed_days = calculate_failed_days(_enum_value(row["state"]), latest_by_key.get(key))
            report = _build_meta_report_instance(row, failed_days)
            to_create.append(report)
            latest_by_key[key] = report

        written: List[MetaCheckReport] = []
        for chunk in _chunked(to_create, META_REPORT_WRITE_CHUNK):
            MetaCheckReport.objects.bulk_create(chunk)
            written.extend(chunk)
        return written

    def _write_meta_reports_upsert(self, rows: List[Dict]) -> List[MetaCheckReport]:
        latest_by_key = _prefetch_meta_last_records(rows)
        to_update: List[MetaCheckReport] = []
        to_create: List[MetaCheckReport] = []
        now = timezone.now()

        for row in rows:
            cluster = row["cluster"]
            key = _meta_report_lookup_key(
                cluster.immute_domain,
                row.get("ip"),
                row.get("port"),
                row["subtype"],
                row["state"],
            )
            failed_days = calculate_failed_days(_enum_value(row["state"]), latest_by_key.get(key))
            existing = latest_by_key.get(key)
            if existing is None:
                report = _build_meta_report_instance(row, failed_days)
                to_create.append(report)
                latest_by_key[key] = report
                continue

            existing.msg = row["msg"]
            existing.state = _enum_value(row["state"])
            existing.failed_days = failed_days
            existing.create_at = now
            existing.update_at = now
            to_update.append(existing)

        written: List[MetaCheckReport] = []
        if to_update:
            for chunk in _chunked(to_update, META_REPORT_WRITE_CHUNK):
                MetaCheckReport.objects.bulk_update(
                    chunk,
                    fields=["msg", "state", "failed_days", "create_at", "update_at"],
                )
            written.extend(to_update)
        if to_create:
            for chunk in _chunked(to_create, META_REPORT_WRITE_CHUNK):
                MetaCheckReport.objects.bulk_create(chunk)
            written.extend(to_create)
        return written

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

    def write_redis_reports(self, rows: List[Dict]) -> List[RedisCheckReport]:
        """Write multiple RedisCheckReport rows, bulk-creating add-mode rows."""
        if not rows:
            return []

        add_rows = []
        written = []
        for row in rows:
            mode = _resolve_write_mode(row["subtype"], self._mode_config)
            if mode == REDIS_REPORT_MODE_UPSERT:
                written.append(self.write_redis_report(**row))
            else:
                add_rows.append(row)

        if not add_rows:
            return written

        cutoff = timezone.now() - timedelta(hours=36)
        cluster_ids = {row["cluster_id"] for row in add_rows}
        subtypes = {row["subtype"] for row in add_rows}
        instances = {row.get("instance", "") for row in add_rows}
        latest_by_key = {}
        existing_rows = RedisCheckReport.objects.filter(
            cluster_id__in=cluster_ids,
            subtype__in=subtypes,
            instance__in=instances,
            create_at__gte=cutoff,
        ).order_by("cluster_id", "subtype", "instance", "-create_at")
        for existing in existing_rows:
            key = (existing.cluster_id, existing.subtype, existing.instance)
            latest_by_key.setdefault(key, existing)

        to_create = []
        for row in add_rows:
            key = (row["cluster_id"], row["subtype"], row.get("instance", ""))
            defaults = RedisCheckReport._build_defaults(
                cluster=row["cluster"],
                cluster_type=row["cluster_type"],
                bk_biz_id=row["bk_biz_id"],
                bk_cloud_id=row["bk_cloud_id"],
                report_day=row["report_day"],
                creator=row["creator"],
                state=row["state"],
                msg=row["msg"],
                shard=row.get("shard", ""),
                instance=row.get("instance", ""),
            )
            defaults["failed_days"] = RedisCheckReport._resolve_failed_days(
                state=row["state"], existing=latest_by_key.get(key)
            )
            report = RedisCheckReport(cluster_id=row["cluster_id"], subtype=row["subtype"], **defaults)
            to_create.append(report)
            latest_by_key[key] = report

        RedisCheckReport.objects.bulk_create(to_create)
        written.extend(to_create)
        return written


def safe_write_meta_reports(
    writer: RedisReportWriter,
    rows: List[Dict],
    *,
    context: str = "",
) -> bool:
    """Write meta reports; log and return False instead of aborting the caller on DB errors."""
    if not rows:
        return True
    try:
        writer.write_meta_reports(rows)
        return True
    except Exception as e:
        logger.error(
            "meta_check: failed to write %d reports%s: %s",
            len(rows),
            f" ({context})" if context else "",
            e,
            exc_info=True,
        )
        return False


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
