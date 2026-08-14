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
from collections import defaultdict
from datetime import timedelta

from django.db.models import Prefetch, Q
from django.utils import timezone

from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import Cluster, StorageInstance, StorageInstanceTuple
from backend.db_report.enums import RedisBackupCheckSubType, ReportStateType
from backend.db_report.portrait.redis_dimensions import RedisPortraitDimensionCode
from backend.db_report.portrait.redis_ingest import ingest_abnormal_cluster_rows

from .bklog_query import DOMAIN_BATCH_SIZE, batch_fetch_backup_logs, find_and_verify_failed_tasks
from .config import RedisBackupCheckConfig
from .report_op import RedisBackupCheckBatchOps, RedisBackupClusterReport

logger = logging.getLogger("root")

FULL_BACKUP_CLUSTER_TYPES = [
    ClusterType.TendisRedisInstance,
    ClusterType.TendisTwemproxyRedisInstance,
    ClusterType.TendisPredixyRedisCluster,
    ClusterType.TendisPredixyTendisplusCluster,
    ClusterType.TwemproxyTendisSSDInstance,
]


def _parse_backup_hour(time_str: str) -> int | None:
    """Extract the hour from a backup timestamp string.

    Handles Go time.Time JSON formats like "2024-01-15T05:30:00+08:00"
    and "2024-01-15 05:30:00".
    """
    if not time_str or len(time_str) < 13:
        return None
    try:
        return int(time_str[11:13])
    except (ValueError, IndexError):
        return None


def _map_to_schedule_slot(hour: int, sorted_schedule: list[int]) -> int:
    """Map a backup hour to its triggering schedule slot.

    A backup completing at hour H was triggered by the most recent
    schedule hour <= H (with midnight wrap-around).
    """
    for sh in reversed(sorted_schedule):
        if hour >= sh:
            return sh
    return sorted_schedule[-1]


def _find_missing_slots(backup_times: list[str], schedule_hours: list[int]) -> list[int]:
    """Return schedule hours not covered by any backup timestamp."""
    sorted_hours = sorted(schedule_hours)
    covered: set[int] = set()
    for time_str in backup_times:
        hour = _parse_backup_hour(time_str)
        if hour is not None:
            covered.add(_map_to_schedule_slot(hour, sorted_hours))
    return [h for h in sorted_hours if h not in covered]


def _find_off_schedule_backups(
    backup_times: list[str],
    schedule_hours: list[int],
    max_deviation_hours: float,
) -> list[tuple[str, int, int]]:
    """Return (time_str, actual_hour, mapped_slot) for backups deviating beyond threshold."""
    sorted_hours = sorted(schedule_hours)
    off_schedule = []
    for time_str in backup_times:
        hour = _parse_backup_hour(time_str)
        if hour is None:
            continue
        slot = _map_to_schedule_slot(hour, sorted_hours)
        deviation = (hour - slot) % 24
        if deviation > max_deviation_hours:
            off_schedule.append((time_str, hour, slot))
    return off_schedule


def _format_hours(hours: list[int]) -> str:
    return ", ".join(f"{h:02d}:00" for h in hours)


class CheckFullBackupTask:
    """Full backup check: verify every cluster has the expected number of
    successful full backups in yesterday's BKLog records.

    Backup schedule (default cron: 0 5,13,21 * * *):
    - redis cache: 3 backups/day at 05:00, 13:00, 21:00
    - ssd / plus:  1 backup/day  at 05:00 (13:00/21:00 skipped by dbmon)
    - Default backup target is slave; if slave backup is insufficient
      but master meets the threshold, report as WARNING.
    """

    def __init__(self):
        self.subtype = RedisBackupCheckSubType.FullBackup.value

    def start(self) -> tuple[int, int, int, int]:
        config = RedisBackupCheckConfig.from_settings()
        batch_ops = RedisBackupCheckBatchOps(self.subtype)
        batch_ops.delete_old_records(config.retention_days)
        batch_ops.delete_today_records()

        cluster_ids = list(self._get_cluster_ids(config))
        start_time, end_time = self._yesterday_time_range()
        cluster_state_total = {
            ReportStateType.NORMAL.value: 0,
            ReportStateType.WARNING.value: 0,
            ReportStateType.ABNORMAL.value: 0,
        }

        total_num = 0
        for batch_start in range(0, len(cluster_ids), DOMAIN_BATCH_SIZE):
            batch_ids = cluster_ids[batch_start : batch_start + DOMAIN_BATCH_SIZE]
            batch_clusters = list(self._get_cluster_queryset(batch_ids))
            domains = [c.immute_domain for c in batch_clusters]
            domain_logs = batch_fetch_backup_logs("redis_fullbackup_result", start_time, end_time, domains)

            for cluster in batch_clusters:
                total_num += 1
                bklogs = domain_logs.get(cluster.immute_domain, [])
                rows = self._check_cluster_with_retry(cluster, bklogs, config)
                if rows:
                    cluster_state_total[rows[0].state] += 1
                    ingest_abnormal_cluster_rows(
                        rows,
                        dimension=RedisPortraitDimensionCode.RELIABILITY,
                        prefix="[全备]",
                    )
                for row in rows:
                    batch_ops.append(row)

            batch_ops.bulk_create()

        logger.info(
            "CheckFullBackupTask total=%s states=%s",
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
        return Q(cluster_type__in=[ct.value for ct in FULL_BACKUP_CLUSTER_TYPES]) & Q(
            create_at__lt=timezone.now() - timedelta(days=config.min_cluster_age_days)
        )

    @staticmethod
    def _get_cluster_ids(config: RedisBackupCheckConfig):
        return Cluster.objects.filter(CheckFullBackupTask._base_filter(config)).values_list("id", flat=True)

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
        bklogs: list[dict],
        config: RedisBackupCheckConfig,
        max_retries: int = 3,
    ):
        last_error = None
        for attempt in range(max_retries):
            try:
                return self._check_cluster(cluster, bklogs, config)
            except Exception as e:
                logger.error(
                    "CheckFullBackupTask cluster=%s attempt=%d/%d error: %s",
                    cluster.immute_domain,
                    attempt + 1,
                    max_retries,
                    e,
                )
                last_error = e
                time.sleep(attempt * 3 + 1)
        report = RedisBackupClusterReport(cluster, self.subtype)
        return report.make_error_record(f"system error after {max_retries} retries: {last_error}")

    def _check_cluster(self, cluster: Cluster, bklogs: list[dict], config: RedisBackupCheckConfig):
        report = RedisBackupClusterReport(cluster, self.subtype)

        if cluster.bk_cloud_id not in config.target_bk_cloud_ids:
            return report.make_skip_record(f"skipped: bk_cloud_id={cluster.bk_cloud_id} (not in target list)")

        if cluster.immute_domain in config.ignore_domains:
            return report.make_skip_record("skipped: domain in ignore list")

        slave_instances, master_instances, slave_to_master, recently_switched = self._collect_instance_pairs(
            cluster, config
        )
        if not slave_instances:
            return report.make_skip_record(
                f"no eligible instances (all created < {config.min_instance_age_hours}h ago)"
            )

        if not bklogs:
            return report.make_error_record("no full backup logs found for this cluster")

        all_instances = slave_instances + master_instances
        (
            success_count,
            success_times,
            seen_instances,
            inst_errors,
            api_promoted_per_inst,
        ) = self._process_bklog_entries(report, bklogs, all_instances)

        schedule_hours = config.get_full_backup_schedule(cluster.cluster_type)
        expect_count = len(schedule_hours)
        schedule_str = _format_hours(schedule_hours)

        for slave_inst in slave_instances:
            master_inst = slave_to_master.get(slave_inst)
            self._evaluate_slave(
                report,
                slave_inst,
                master_inst,
                success_count,
                success_times,
                seen_instances,
                inst_errors,
                schedule_hours,
                expect_count,
                schedule_str,
                config.max_schedule_deviation_hours,
                recently_switched=recently_switched.get(slave_inst),
                api_promoted_count=api_promoted_per_inst.get(slave_inst, 0),
            )

        return report.make_records()

    def _process_bklog_entries(
        self,
        report: RedisBackupClusterReport,
        bklogs: list[dict],
        tracked_instances: list[str],
    ) -> tuple[dict[str, int], dict[str, list[str]], set[str], dict[str, list[str]], dict[str, int]]:
        """Classify BKLog entries: count successes, collect errors, cross-check with backup API."""
        success_count: dict[str, int] = {inst: 0 for inst in tracked_instances}
        success_times: dict[str, list[str]] = {inst: [] for inst in tracked_instances}
        seen_instances: set[str] = set()
        inst_errors: dict[str, list[str]] = defaultdict(list)

        api_confirmed = find_and_verify_failed_tasks(bklogs)
        bklog_success_task_ids = {
            e["task_id"] for e in bklogs if e.get("backup_status") == "to_backup_system_success" and e.get("task_id")
        }
        api_promoted_per_inst: dict[str, int] = defaultdict(int)

        for entry in bklogs:
            status = entry.get("backup_status", "")
            task_id = entry.get("task_id", "")
            inst_addr = f"{entry.get('redis_ip', '')}{IP_PORT_DIVIDER}{entry.get('redis_port', '')}"
            seen_instances.add(inst_addr)

            if status == "to_backup_system_success":
                if inst_addr in success_count:
                    success_count[inst_addr] += 1
                    success_times[inst_addr].append(entry.get("uptime", ""))
            elif status in ("to_backup_system_failed", "to_backup_system_start"):
                if status == "to_backup_system_failed" and task_id in bklog_success_task_ids:
                    continue
                if task_id in api_confirmed:
                    if inst_addr in success_count:
                        success_count[inst_addr] += 1
                        success_times[inst_addr].append(entry.get("uptime", ""))
                        api_promoted_per_inst[inst_addr] += 1
                elif status == "to_backup_system_failed":
                    err_msg = entry.get("backup_status_info", "upload failed")
                    if err_msg not in inst_errors[inst_addr]:
                        inst_errors[inst_addr].append(err_msg)
                # to_backup_system_start entries not confirmed by the API are in-flight
                # uploads -- not an error; they are intentionally left unreported.

        if api_promoted_per_inst:
            total_promoted = sum(api_promoted_per_inst.values())
            logger.info(
                "CheckFullBackupTask cluster=%s: %d entries across %d instances promoted to success via backup system API",
                report.cluster.immute_domain,
                total_promoted,
                len(api_promoted_per_inst),
            )

        return success_count, success_times, seen_instances, inst_errors, api_promoted_per_inst

    @staticmethod
    def _evaluate_slave(
        report: RedisBackupClusterReport,
        slave_inst: str,
        master_inst: str | None,
        success_count: dict[str, int],
        success_times: dict[str, list[str]],
        seen_instances: set[str],
        inst_errors: dict[str, list[str]],
        schedule_hours: list[int],
        expect_count: int,
        schedule_str: str,
        max_deviation_hours: float,
        recently_switched: int | None = None,
        api_promoted_count: int = 0,
    ):
        """Evaluate a single slave instance and append the result to the report.

        *recently_switched*: if not None, the master-slave tuple age in hours,
        indicating a recent role switch that may explain missing backups.
        """
        slave_count = success_count[slave_inst]
        master_count = success_count.get(master_inst, 0) if master_inst else 0

        if slave_count >= expect_count:
            if slave_count == expect_count:
                off_sched = _find_off_schedule_backups(
                    success_times[slave_inst],
                    schedule_hours,
                    max_deviation_hours,
                )
                if off_sched:
                    off_detail = ", ".join(f"{t}(slot {s:02d}:00)" for t, _, s in off_sched)
                    report.append(
                        ReportStateType.ABNORMAL.value,
                        slave_inst,
                        f"{slave_count}/{expect_count} backups but {len(off_sched)} off-schedule: {off_detail}",
                    )
                    return
            ok_msg = "ok"
            if api_promoted_count > 0:
                ok_msg = f"ok ({api_promoted_count} via backup system double-check)"
            report.append(ReportStateType.NORMAL.value, slave_inst, ok_msg)
            return

        if master_count >= expect_count:
            slave_missing = _find_missing_slots(success_times[slave_inst], schedule_hours)
            report.append(
                ReportStateType.WARNING.value,
                slave_inst,
                f"slave {slave_count}/{expect_count}, missing {_format_hours(slave_missing)}; "
                f"covered by master ({master_count}/{expect_count})",
            )
            return

        missing = _find_missing_slots(success_times[slave_inst], schedule_hours)
        best_count = max(slave_count, master_count)
        no_log = slave_inst not in seen_instances and (master_inst is None or master_inst not in seen_instances)
        errors = list(inst_errors.get(slave_inst, []))
        if master_inst:
            for e in inst_errors.get(master_inst, []):
                if e not in errors:
                    errors.append(e)
        detail = ""
        if recently_switched is not None:
            detail += f"possible recent master-slave switch ({recently_switched}h ago); "
        if errors:
            detail += f"errors({'; '.join(errors)}); "
        detail += f"{best_count}/{expect_count} backups (expected at {schedule_str}), "
        if no_log:
            detail += "no log found, "
        detail += f"missing {_format_hours(missing)}"
        if recently_switched is not None or not no_log:
            state = ReportStateType.WARNING.value
        else:
            state = ReportStateType.ABNORMAL.value
        report.append(state, slave_inst, detail)

    @staticmethod
    def _collect_instance_pairs(cluster: Cluster, config: RedisBackupCheckConfig):
        """Return (slave_instances, master_instances, slave_to_master_map, recently_switched).

        Skips instances younger than config.min_instance_age_hours.
        Populates *recently_switched* with slave addresses whose
        StorageInstanceTuple was created within min_instance_age_hours,
        mapping to the tuple age in hours.
        """
        slave_instances = []
        master_instances = []
        slave_to_master: dict[str, str] = {}
        recently_switched: dict[str, int] = {}
        now = timezone.now()

        for master_obj in cluster.storages:
            if not getattr(master_obj, "ejector_tuples", None):
                logger.warning(
                    "CheckFullBackupTask cluster=%s master %s:%s has no ejector tuples, skipped",
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
            master_addr = f"{master_obj.machine.ip}{IP_PORT_DIVIDER}{master_obj.port}"
            slave_instances.append(slave_addr)
            master_instances.append(master_addr)
            slave_to_master[slave_addr] = master_addr

            tuple_age = now - tuple_obj.create_at
            if tuple_age < timedelta(hours=config.min_instance_age_hours):
                recently_switched[slave_addr] = int(tuple_age.total_seconds() // 3600)

        return slave_instances, master_instances, slave_to_master, recently_switched

    @staticmethod
    def _yesterday_time_range():
        local_now = timezone.localtime()
        yesterday = local_now - timedelta(days=1)
        start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(tz=timezone.utc)
        end = yesterday.replace(hour=23, minute=59, second=59, microsecond=0).astimezone(tz=timezone.utc)
        return start, end
