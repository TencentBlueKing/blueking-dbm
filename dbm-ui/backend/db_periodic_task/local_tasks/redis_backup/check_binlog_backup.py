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
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

from django.db.models import Prefetch, Q
from django.utils import timezone

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import Cluster, StorageInstance, StorageInstanceTuple
from backend.db_report.enums import RedisBackupCheckSubType, ReportStateType
from backend.db_report.portrait.redis_dimensions import RedisPortraitDimensionCode
from backend.db_report.portrait.redis_ingest import ingest_daily_cluster_rows
from backend.db_services.redis.util import is_tendisplus_instance_type, is_tendisssd_instance_type
from backend.flow.consts import DEFAULT_DB_MODULE_ID, ConfigTypeEnum

from .bklog_query import (
    fetch_cluster_backup_logs,
    fetch_instance_backup_logs,
    fetch_ip_backup_logs,
    find_and_verify_failed_tasks,
)
from .config import RedisBackupCheckConfig
from .report_op import RedisBackupCheckBatchOps, RedisBackupClusterReport

logger = logging.getLogger("root")

BINLOG_DOMAIN_BATCH_SIZE = 5

BINLOG_CLUSTER_TYPES = [
    ClusterType.TendisPredixyTendisplusCluster,
    ClusterType.TwemproxyTendisSSDInstance,
]


def _extract_binlog_index(file_name: str, tendis_type: str) -> int:
    """Extract the numeric sequence index from a binlog filename.

    TendisPlus: binlog-{ip}-{port}-{kvstore}-{INDEX}-{timestamp}.log.zst
    TendisSSD:  binlog-{ip}-{port}-{INDEX}-{timestamp}.log.zst
    """
    parts = file_name.split("-")
    if is_tendisplus_instance_type(tendis_type):
        return int(parts[4])
    if is_tendisssd_instance_type(tendis_type):
        return int(parts[3])
    raise ValueError(f"unsupported tendis type for binlog index extraction: {tendis_type}")


def _extract_binlog_timestamp(file_name: str, tendis_type: str) -> Optional[datetime]:
    """Extract the binlog file rotation timestamp (its content cutoff time).

    The trailing component of the filename is ``YYYYMMDDHHMMSS`` in local
    time. The index of that component differs by tendis type because
    TendisPlus filenames carry an extra ``kvstore`` field. Mirror the
    layout documented on ``_extract_binlog_index`` above:

        TendisSSD:  binlog-{ip}-{port}-{idx}-{ts}.log.zst        -> parts[4]
        TendisPlus: binlog-{ip}-{port}-{kv}-{idx}-{ts}.log.zst   -> parts[5]

    Examples:
        TendisSSD:  binlog-1.2.3.4-30000-0014018-20251216171048.log.zst
        TendisPlus: binlog-1.2.3.4-30000-5-0022670-20251216171459.log.zst

    Returns a naive ``datetime`` representing local time, or ``None`` on
    parse failure.  Callers treat unparseable entries as "not yesterday"
    so that they are excluded from gap analysis (fail-safe: never causes
    a false positive).
    """
    parts = file_name.split("-")
    try:
        if is_tendisplus_instance_type(tendis_type):
            ts_str = parts[5].split(".")[0]
        elif is_tendisssd_instance_type(tendis_type):
            ts_str = parts[4].split(".")[0]
        else:
            return None
        return datetime.strptime(ts_str, "%Y%m%d%H%M%S")
    except (IndexError, ValueError):
        return None


def _find_missing_binlogs(
    all_terminal_entries: list[dict],
    success_entries: list[dict],
    tendis_type: str,
    buffer_success_entries: Optional[list[dict]] = None,
) -> list[int]:
    """Find all binlog indexes that are not successfully backed up.

    Detects:
    - Failed uploads: indexes present in terminal entries but absent from success
    - Interior gaps: indexes between the observed min/max that appear in no entry

    *buffer_success_entries* (optional) are successful uploads whose
    binlog content time falls in one of the buffer hours (leading
    day-before-yesterday last hour, or trailing today first hour).
    Their indexes can fill GAPS -- indexes that would otherwise be
    flagged as interior gaps in yesterday's range -- but they do NOT
    override known FAILURES (indexes present in ``all_terminal_entries``
    but absent from ``success_entries``), because a failed upload in
    yesterday and a buffer-day file with a colliding index are
    different binlog files.

    Returns a sorted list of missing indexes, or [-1] on parse error.
    """
    if not all_terminal_entries:
        return []

    try:
        all_indexes = sorted({_extract_binlog_index(e["file_name"], tendis_type) for e in all_terminal_entries})
    except (IndexError, ValueError, KeyError) as e:
        logger.error("Failed to parse binlog filenames: %s", e)
        return [-1]

    success_indexes: set[int] = set()
    for e in success_entries:
        try:
            success_indexes.add(_extract_binlog_index(e["file_name"], tendis_type))
        except (IndexError, ValueError, KeyError):
            pass

    missing: set[int] = set()

    missing.update(set(all_indexes) - success_indexes)

    if len(all_indexes) >= 2:
        for i in range(len(all_indexes) - 1):
            gap_start = all_indexes[i] + 1
            gap_end = all_indexes[i + 1]
            if gap_end > gap_start:
                missing.update(range(gap_start, gap_end))

    if buffer_success_entries:
        buffer_indexes: set[int] = set()
        for e in buffer_success_entries:
            try:
                buffer_indexes.add(_extract_binlog_index(e["file_name"], tendis_type))
            except (IndexError, ValueError, KeyError):
                pass
        all_terminal_set = set(all_indexes)
        fillable = buffer_indexes - all_terminal_set
        missing -= fillable

    return sorted(missing)


def _compress_ranges(gaps: list[int]) -> list[tuple[int, int]]:
    """Compress a sorted list of integers into (start, end) ranges.

    [42, 43, 44, 78] -> [(42, 44), (78, 78)]
    """
    if not gaps:
        return []
    sorted_gaps = sorted(gaps)
    ranges: list[tuple[int, int]] = []
    start = end = sorted_gaps[0]
    for val in sorted_gaps[1:]:
        if val == end + 1:
            end = val
        else:
            ranges.append((start, end))
            start = end = val
    ranges.append((start, end))
    return ranges


def _format_ranges(ranges: list[tuple[int, int]], max_display: int = 10) -> str:
    """Format compressed ranges for display, capped at *max_display* entries.

    [(42, 44), (78, 78)] -> "42-44, 78"
    """
    parts: list[str] = []
    for start, end in ranges[:max_display]:
        parts.append(f"{start}-{end}" if start != end else str(start))
    text = ", ".join(parts)
    if len(ranges) > max_display:
        text += f" ...and {len(ranges) - max_display} more"
    return text


def _get_cluster_config(domain_name: str, db_version: str, conf_type: str, namespace: str, bk_biz_id: str) -> Any:
    data = DBConfigApi.query_conf_item(
        params={
            "bk_biz_id": bk_biz_id,
            "level_name": LevelName.CLUSTER,
            "level_value": domain_name,
            "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
            "conf_file": db_version,
            "conf_type": conf_type,
            "namespace": namespace,
            "format": FormatType.MAP,
        }
    )
    return data["content"]


@dataclass(frozen=True)
class AnalysisWindow:
    """Yesterday's wall-clock day as a half-open interval ``[start, end)``"""

    start: datetime
    end: datetime

    def contains(self, ts: Optional[datetime]) -> bool:
        if ts is None:
            return False
        return self.start <= ts < self.end


class CheckBinlogBackupTask:
    """Binlog backup check for TendisPlus and TendisSSD clusters.

    Validates that every slave instance has binlog backup logs in BKLog
    for yesterday, and that the binlog sequence numbers are continuous.
    TendisPlus instances are checked per-kvstore.
    """

    def __init__(self):
        self.subtype = RedisBackupCheckSubType.BinlogBackup.value

    def start(self) -> tuple[int, int, int, int]:
        config = RedisBackupCheckConfig.from_settings()
        batch_ops = RedisBackupCheckBatchOps(self.subtype)
        batch_ops.delete_old_records(config.retention_days)
        batch_ops.delete_today_records()

        cluster_ids = list(self._get_cluster_ids(config))
        start_time, end_time, analysis_window = self._yesterday_time_range()
        cluster_state_total = {
            ReportStateType.NORMAL.value: 0,
            ReportStateType.WARNING.value: 0,
            ReportStateType.ABNORMAL.value: 0,
        }

        total_num = 0
        for batch_start in range(0, len(cluster_ids), BINLOG_DOMAIN_BATCH_SIZE):
            batch_ids = cluster_ids[batch_start : batch_start + BINLOG_DOMAIN_BATCH_SIZE]
            batch_clusters = list(self._get_cluster_queryset(batch_ids))

            for cluster in batch_clusters:
                total_num += 1
                rows = self._check_cluster_with_retry(
                    cluster,
                    start_time,
                    end_time,
                    config,
                    analysis_window=analysis_window,
                )
                if rows:
                    cluster_state_total[rows[0].state] += 1
                    ingest_daily_cluster_rows(
                        rows,
                        dimension=RedisPortraitDimensionCode.RELIABILITY,
                        prefix="[binlog]",
                    )
                for row in rows:
                    batch_ops.append(row)

            batch_ops.bulk_create()

        logger.info(
            "CheckBinlogBackupTask total=%s states=%s",
            total_num,
            cluster_state_total,
        )
        return (
            total_num,
            cluster_state_total[ReportStateType.NORMAL.value],
            cluster_state_total[ReportStateType.WARNING.value],
            cluster_state_total[ReportStateType.ABNORMAL.value],
        )

    @staticmethod
    def _base_filter(config: RedisBackupCheckConfig):
        return Q(cluster_type__in=[ct.value for ct in BINLOG_CLUSTER_TYPES]) & Q(
            create_at__lt=timezone.now() - timedelta(days=config.min_cluster_age_days)
        )

    @staticmethod
    def _get_cluster_ids(config: RedisBackupCheckConfig):
        return Cluster.objects.filter(CheckBinlogBackupTask._base_filter(config)).values_list("id", flat=True)

    @staticmethod
    def _get_cluster_queryset(ids):
        ejector_prefetch = Prefetch(
            "as_ejector",
            queryset=StorageInstanceTuple.objects.select_related("receiver"),
            to_attr="ejector_tuples",
        )
        storage_prefetch = Prefetch(
            "storageinstance_set",
            queryset=StorageInstance.objects.filter(instance_role=InstanceRole.REDIS_MASTER.value)
            .select_related("machine")
            .prefetch_related(ejector_prefetch),
            to_attr="storages",
        )
        return Cluster.objects.filter(id__in=ids).prefetch_related(storage_prefetch)

    def _check_cluster_with_retry(
        self,
        cluster: Cluster,
        start_time,
        end_time,
        config: RedisBackupCheckConfig,
        max_retries: int = 3,
        *,
        analysis_window: Optional[AnalysisWindow] = None,
    ):
        last_error = None
        for attempt in range(max_retries):
            try:
                return self._check_cluster(
                    cluster,
                    start_time,
                    end_time,
                    config,
                    analysis_window=analysis_window,
                )
            except Exception as e:
                logger.error(
                    "CheckBinlogBackupTask cluster=%s attempt=%d/%d error: %s",
                    cluster.immute_domain,
                    attempt + 1,
                    max_retries,
                    e,
                )
                last_error = e
                time.sleep(attempt * 3 + 1)
        report = RedisBackupClusterReport(cluster, self.subtype)
        return report.make_error_record(f"system error after {max_retries} retries: {last_error}")

    def _check_cluster(
        self,
        cluster: Cluster,
        start_time,
        end_time,
        config: RedisBackupCheckConfig,
        *,
        analysis_window: Optional[AnalysisWindow] = None,
    ):
        report = RedisBackupClusterReport(cluster, self.subtype)

        if cluster.bk_cloud_id not in config.target_bk_cloud_ids:
            return report.make_skip_record(f"skipped: bk_cloud_id={cluster.bk_cloud_id} (not in target list)")

        if cluster.immute_domain in config.ignore_domains:
            return report.make_skip_record("skipped: domain in ignore list")

        kvstorecount = None
        if is_tendisplus_instance_type(cluster.cluster_type):
            try:
                cluster_conf = _get_cluster_config(
                    cluster.immute_domain,
                    cluster.major_version,
                    ConfigTypeEnum.DBConf,
                    cluster.cluster_type,
                    str(cluster.bk_biz_id),
                )
                kvstorecount = int(cluster_conf["kvstorecount"])
            except Exception as e:
                logger.error(
                    "CheckBinlogBackupTask cluster=%s failed to get kvstorecount: %s",
                    cluster.immute_domain,
                    e,
                )
                return report.make_error_record(f"failed to get kvstorecount: {e}")

        slave_instances, recently_switched = self._collect_slave_instances(cluster, config)
        if not slave_instances:
            return report.make_skip_record(
                f"no eligible slave instances (all created < {config.min_instance_age_hours}h ago)"
            )

        instance_logs = self._fetch_logs_tiered(start_time, end_time, cluster.immute_domain, slave_instances)

        for instance in slave_instances:
            ip, port = instance.split(IP_PORT_DIVIDER)
            try:
                self._check_instance(
                    report,
                    instance_logs.get(instance, []),
                    cluster,
                    instance,
                    ip,
                    port,
                    kvstorecount,
                    recently_switched=recently_switched.get(instance),
                    analysis_window=analysis_window,
                )
            except Exception as e:
                logger.error(
                    "CheckBinlogBackupTask cluster=%s instance=%s error: %s",
                    cluster.immute_domain,
                    instance,
                    e,
                )
                report.append(ReportStateType.ABNORMAL.value, instance, f"check error: {e}")

        return report.make_records()

    def _fetch_logs_tiered(self, start_time, end_time, domain, slave_instances):
        """Tiered BKLog fetch: cluster -> per-IP -> per-instance.

        Tries the broadest query first.  If results are truncated by
        ES ``max_result_window``, narrows scope progressively.
        """
        collector = "redis_binlog_backup_result"

        cluster_logs, truncated = fetch_cluster_backup_logs(collector, start_time, end_time, domain)
        logger.info("cluster=%s fetched %d logs (truncated=%s)", domain, len(cluster_logs), truncated)

        if not truncated:
            result: dict[str, list[dict]] = {}
            for instance in slave_instances:
                ip, port = instance.split(IP_PORT_DIVIDER)
                result[instance] = [
                    e for e in cluster_logs if e["redis_ip"] == ip and str(e["redis_port"]) == str(port)
                ]
            return result

        result = {}
        ip_to_instances: dict[str, list[str]] = {}
        for instance in slave_instances:
            ip = instance.split(IP_PORT_DIVIDER)[0]
            ip_to_instances.setdefault(ip, []).append(instance)

        for ip, ip_instances in ip_to_instances.items():
            ip_logs, ip_truncated = fetch_ip_backup_logs(collector, start_time, end_time, domain, ip)

            if not ip_truncated:
                for instance in ip_instances:
                    _, port = instance.split(IP_PORT_DIVIDER)
                    result[instance] = [e for e in ip_logs if str(e["redis_port"]) == str(port)]
            else:
                for instance in ip_instances:
                    _, port = instance.split(IP_PORT_DIVIDER)
                    result[instance] = fetch_instance_backup_logs(collector, start_time, end_time, domain, ip, port)

        return result

    def _check_instance(
        self,
        report,
        bklogs,
        cluster,
        instance,
        ip,
        port,
        kvstorecount,
        *,
        recently_switched=None,
        analysis_window: Optional[AnalysisWindow] = None,
    ):
        # The "no logs found" check is done against the raw query window
        # (pre-filter): if BKLog returned nothing at all for this instance
        # within the leading 1h buffer + yesterday + trailing 1h buffer
        # window, that itself is a strong abnormal signal regardless of
        # content-time semantics.
        if not bklogs:
            if recently_switched is not None:
                report.append(
                    ReportStateType.WARNING.value,
                    instance,
                    f"no logs found (possible recent master-slave switch, {recently_switched}h ago)",
                )
            else:
                report.append(ReportStateType.ABNORMAL.value, instance, "no logs found")
            return

        # Failed-task verification runs against the full window so that
        # success entries arriving in either buffer hour can still
        # promote a corresponding ``to_backup_system_start`` whose
        # content time belongs to yesterday.
        api_confirmed = find_and_verify_failed_tasks(bklogs)

        # Filter to entries whose binlog content time falls in
        # yesterday's wall-clock day.  Today's first-hour entries
        # (caught by the trailing 1h buffer) AND day-before-yesterday's
        # last-hour entries (caught by the leading 1h buffer) are
        # excluded so that gap detection never uses them as min/max
        # boundaries -- avoiding day-boundary false positives where a
        # late-uploaded neighbouring-day seq looks like an interior gap
        # next to a real yesterday seq.  The excluded entries will be
        # re-checked on the appropriate day's run.
        #
        # Timezone contract: both operands compared via
        # ``analysis_window.contains`` are NAIVE local time.
        # ``_extract_binlog_timestamp`` returns naive local per the
        # backup-agent filename convention (YYYYMMDDHHMMSS in the local
        # tz of the source host); ``analysis_window`` carries naive
        # local bounds stripped from Django timezone-aware
        # ``localtime()``.  They are directly comparable only because
        # both are local wall-clock.  If a newly provisioned instance
        # ever emits UTC timestamps in filenames, this comparison would
        # silently mis-classify buffer-window entries -- revisit this
        # contract then.
        if analysis_window is not None:
            yesterday_logs = [
                e
                for e in bklogs
                if analysis_window.contains(_extract_binlog_timestamp(e.get("file_name", ""), cluster.cluster_type))
            ]
        else:
            yesterday_logs = bklogs

        _TERMINAL = ("to_backup_system_success", "to_backup_system_failed")
        all_terminal = [e for e in yesterday_logs if e.get("backup_status") in _TERMINAL]
        success_entries = [e for e in yesterday_logs if e.get("backup_status") == "to_backup_system_success"]

        api_promoted = [
            e
            for e in yesterday_logs
            if e.get("backup_status") == "to_backup_system_start" and e.get("task_id", "") in api_confirmed
        ]
        if api_promoted:
            all_terminal.extend(api_promoted)
            success_entries.extend(api_promoted)
            logger.info(
                "Instance %s: %d entries promoted to success via backup system API",
                instance,
                len(api_promoted),
            )

        # Buffer entries: in the BKLog query window but outside yesterday's
        # wall-clock day (content time falls in the leading or trailing
        # buffer hour).  Successful buffer uploads can fill what would
        # otherwise look like interior gaps in yesterday's index range
        # -- e.g. a binlog whose content time slipped into the leading
        # buffer hour but whose index sits between two yesterday seqs.
        # They never override a known yesterday-side failure (handled by
        # `_find_missing_binlogs`).
        yesterday_ids = {id(e) for e in yesterday_logs}
        buffer_logs = [e for e in bklogs if id(e) not in yesterday_ids]
        buffer_success_entries = [
            e
            for e in buffer_logs
            if e.get("backup_status") == "to_backup_system_success"
            or (e.get("backup_status") == "to_backup_system_start" and e.get("task_id", "") in api_confirmed)
        ]

        all_files = {e.get("file_name", "") for e in all_terminal}
        success_files = {e.get("file_name", "") for e in success_entries}
        total = len(all_files)
        success_count = len(success_files)

        if total == 0:
            report.append(ReportStateType.WARNING.value, instance, "no terminal binlog status found")
            return

        if success_count == 0:
            report.append(
                ReportStateType.WARNING.value,
                instance,
                f"all {total} binlog uploads failed",
            )
            return

        if is_tendisplus_instance_type(cluster.cluster_type) and kvstorecount:
            kv_issues: list[str] = []
            for kv_idx in range(kvstorecount):
                kvstore_filter = f"{ip}-{port}-{kv_idx}-"
                kv_terminal = [e for e in all_terminal if kvstore_filter in e.get("file_name", "")]
                kv_success = [e for e in success_entries if kvstore_filter in e.get("file_name", "")]
                kv_buffer = [e for e in buffer_success_entries if kvstore_filter in e.get("file_name", "")]

                if not kv_terminal:
                    continue
                if not kv_success:
                    kv_issues.append(f"kv{kv_idx}(all upload failed)")
                    continue

                missing = _find_missing_binlogs(
                    kv_terminal,
                    kv_success,
                    cluster.cluster_type,
                    buffer_success_entries=kv_buffer,
                )
                if missing:
                    kv_issues.append(f"kv{kv_idx}({_format_ranges(_compress_ranges(missing))})")

            if not kv_issues:
                report.append(ReportStateType.NORMAL.value, instance, "ok")
                return

            parts = [f"{kvstorecount} kvstores", f"{success_count}/{total} uploaded"]
            if success_count < total:
                parts.append(f"{total - success_count} upload failed")
            parts.append(f"seq gaps: {', '.join(kv_issues)}")
            report.append(ReportStateType.WARNING.value, instance, ", ".join(parts))

        elif is_tendisssd_instance_type(cluster.cluster_type):
            missing = _find_missing_binlogs(
                all_terminal,
                success_entries,
                cluster.cluster_type,
                buffer_success_entries=buffer_success_entries,
            )

            if not missing:
                report.append(ReportStateType.NORMAL.value, instance, "ok")
                return

            parts = [f"{success_count}/{total} uploaded"]
            if success_count < total:
                parts.append(f"{total - success_count} upload failed")
            ranges = _compress_ranges(missing)
            parts.append(f"{len(missing)} seq gaps ({_format_ranges(ranges)})")
            report.append(ReportStateType.WARNING.value, instance, ", ".join(parts))

    @staticmethod
    def _collect_slave_instances(cluster: Cluster, config: RedisBackupCheckConfig) -> tuple[list[str], dict[str, int]]:
        """Return (slave_instances, recently_switched).

        Populates *recently_switched* with slave addresses whose
        StorageInstanceTuple was created within min_instance_age_hours,
        mapping to the tuple age in hours.
        """
        slave_instances = []
        recently_switched: dict[str, int] = {}
        now = timezone.now()
        for master_obj in cluster.storages:
            if not getattr(master_obj, "ejector_tuples", None):
                logger.warning(
                    "CheckBinlogBackupTask cluster=%s master %s:%s has no ejector tuples, skipped",
                    cluster.immute_domain,
                    master_obj.machine.ip,
                    master_obj.port,
                )
                continue
            tuple_obj = master_obj.ejector_tuples[0]
            slave_obj = tuple_obj.receiver
            if (now - slave_obj.create_at) < timedelta(hours=config.min_instance_age_hours):
                continue
            slave_addr = f"{slave_obj.machine.ip}{IP_PORT_DIVIDER}{slave_obj.port}"
            slave_instances.append(slave_addr)
            tuple_age = now - tuple_obj.create_at
            if tuple_age < timedelta(hours=config.min_instance_age_hours):
                recently_switched[slave_addr] = int(tuple_age.total_seconds() // 3600)
        return slave_instances, recently_switched

    @staticmethod
    def _yesterday_time_range():
        """Compute the BKLog query window and the gap-analysis bounds.

        Returns ``(query_start, query_end, analysis_window)``:

        - ``query_start``/``query_end``: aware UTC bounds for the BKLog
          ES query.  Window is ``[yesterday 00:00 - 1h, today 00:00 + 1h)``
          local time.  The symmetric 1h buffers are intentional:

          * The trailing buffer captures binlogs whose **content**
            belongs to yesterday but whose upload completed slightly
            after midnight (slow uploads, backup-system retries, ES
            ingestion delay).
          * The leading buffer captures the mirror case at the start of
            yesterday -- binlogs whose content belongs to
            day-before-yesterday but whose upload arrived just after
            yesterday 00:00.  Including them lets cross-day failed-task
            promotion match ``to_backup_system_start`` ↔
            ``to_backup_system_success`` pairs that straddle the
            day-before-yesterday/yesterday boundary.
        - ``analysis_window``: naive-local ``AnalysisWindow`` bounding
          yesterday's wall-clock day (``[yesterday 00:00, today 00:00)``).
          Used downstream to drop entries whose content time falls in
          either buffer hour from yesterday's gap detection -- those
          entries belong to a neighbouring day and would otherwise
          create phantom min/max boundaries.  They will be re-checked
          on the appropriate day's run.
        """
        local_now = timezone.localtime()
        local_today_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        local_yesterday_start = local_today_start - timedelta(days=1)
        query_start = local_yesterday_start.astimezone(tz=timezone.utc) - timedelta(hours=1)
        query_end = local_today_start.astimezone(tz=timezone.utc) + timedelta(hours=1)
        analysis_window = AnalysisWindow(
            start=local_yesterday_start.replace(tzinfo=None),
            end=local_today_start.replace(tzinfo=None),
        )
        return query_start, query_end, analysis_window
