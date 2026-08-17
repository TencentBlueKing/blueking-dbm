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

import heapq
import json
import logging
import math
import random
from datetime import timedelta
from enum import StrEnum
from typing import List, Optional, Set, Tuple

from django.utils import timezone as django_timezone
from django.utils.translation import gettext as _

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.db_meta.enums import ClusterPhase, DestroyedStatus, InstanceInnerRole
from backend.db_meta.models import Cluster, StorageInstance
from backend.db_periodic_task.local_tasks.redis_backup.config import RedisBackupCheckConfig
from backend.db_report.enums import RedisRollbackExerciseTaskStage as TaskStage
from backend.db_report.models import RedisRollbackExerciseReport as Report
from backend.db_services.redis.rollback.config import RedisRollbackExerciseConfig, RedisRollbackExerciseMode
from backend.db_services.redis.rollback.handlers import DataStructureHandler
from backend.db_services.redis.rollback.models import TbTendisRollbackTasks
from backend.db_services.redis.util import (
    is_redis_instance_type,
    is_tendisplus_instance_type,
    is_tendisssd_instance_type,
)
from backend.exceptions import AppBaseException
from backend.flow.consts import DEFAULT_DB_MODULE_ID, ConfigTypeEnum
from backend.ticket.builders.common.base import ClusterType
from backend.ticket.constants import TicketType
from backend.ticket.models import ClusterOperateRecord, Ticket
from backend.utils.redis import RedisConn
from backend.utils.time import datetime2str, str2datetime

logger = logging.getLogger("root")


def _fmt_task_msg(message: str) -> str:
    """Format task message with local time prefix [yyyy-mm-dd hh:mm:ss]"""
    timestamp = django_timezone.localtime().strftime("%Y-%m-%d %H:%M:%S")
    return f"[{timestamp}] {message}"


# Candidates queue configurations
REDIS_CANDIDATES_QUEUE_KEY = "redis_rollback_exercise:candidates_queue"
REDIS_CANDIDATES_LOCK_KEY = "redis_rollback_exercise:candidates_lock"
REDIS_LOCK_TIMEOUT = 600  # 10 minutes
RPUSH_BATCH_SIZE = 500


class ValidationFailureKind(StrEnum):
    """Why a candidate failed pre-flight validation.

    BACKUP_INVALID is treated as ABNORMAL on the report (real data-protection issue);
    ENV_SKIPPED is treated as SKIPPED -> WARNING (transient/environmental).
    ENV_SUPPRESSED is logged only because it is expected busy-cluster noise.
    """

    BACKUP_INVALID = "backup_invalid"
    ENV_SKIPPED = "env_skipped"
    ENV_SUPPRESSED = "env_suppressed"


class RedisRollbackExercise:
    """
    Redis rollback exercise task generator
    """

    def __init__(self):
        self.config = self._init_config()

    def _init_config(self) -> RedisRollbackExerciseConfig:
        """Initialize configuration from system settings"""
        config = RedisRollbackExerciseConfig.from_settings()
        logger.info(_("Redis rollback exercise settings: {}").format(config))
        return config

    def start(self):
        """
        Generate Redis rollback exercise tasks

        Main workflow:
        1. Pop no more than n target instances from candidates queue
        2. For each instance, check if backup rollback days ago exists
        3. Create a REDIS_ROLLBACK_EXERCISE drill ticket with selected instances

        The drill ticket will:
        - Apply resources inside the inner flow
        - Create `redis_data_structure` flow to rollback each instance
        - Each rollback flow requires 1 redis-pool machine with disk/mem >= source instance
        - Monitor rollback flow states
        - Destroy temp instances via `redis_data_structure_task_delete` flow
        - Return the resources
        """
        logger.info(_("Starting Redis rollback exercise task generation"))

        if not self.config.enabled:
            logger.info(_("Redis rollback exercise is disabled, exiting..."))
            return

        # Pick targets first
        selected_instances, skipped_clusters = self._pick_target_instances(self.config.max_instances)

        # Record skipped clusters
        for cluster, reason in skipped_clusters:
            report = self._create_report(cluster)
            report.mark(TaskStage.SKIPPED, _fmt_task_msg(reason))

        if not selected_instances:
            logger.info(_("No instances selected for exercise"))
            return

        logger.info(_("Selected {} instances for exercise").format(len(selected_instances)))
        valid_instances = []

        # Validations
        for item in selected_instances:
            cluster = item["cluster"]
            instance: StorageInstance = item["instance"]  # Master instance as target for rollback
            backup_check_instance: StorageInstance = item.get(
                "backup_check_instance", instance
            )  # Slave for backup check

            try:
                (
                    is_valid,
                    full_backup,
                    days_used,
                    recovery_time_point,
                    binlog_summary,
                    fail_reason,
                    failure_kind,
                ) = self._validate_instance(
                    backup_check_instance.machine.ip,
                    backup_check_instance.port,
                    cluster,
                    rollback_days=self.config.rollback_days,
                    backup_check_instance=backup_check_instance,
                )
            except AppBaseException as e:
                logger.exception(_("Backup validation error for instance {} {}").format(instance.ip_port, str(e)))
                report = self._create_report(cluster, instance)
                report.mark(
                    TaskStage.BACKUP_INVALID,
                    task_message=_fmt_task_msg(_("Backup validation error: {}").format(str(e))),
                )
                continue
            except Exception as e:
                logger.exception(_("Error validating instance {} {}").format(instance.ip_port, str(e)))
                report = self._create_report(cluster, instance)
                report.mark(
                    TaskStage.SKIPPED,
                    task_message=_fmt_task_msg(_("Exception during validation: {}").format(str(e))),
                )
                continue

            if is_valid:
                report = self._create_report(cluster, instance)
                report.backup_info = json.dumps(
                    {
                        "full_backup": full_backup,
                        "binlog_summary": binlog_summary,
                        "recovery_time_point": datetime2str(recovery_time_point),
                        "tendis_type": self._resolve_tendis_type(cluster.cluster_type),
                        "kvstorecount": (
                            self._get_kvstorecount(cluster)
                            if is_tendisplus_instance_type(cluster.cluster_type)
                            else None
                        ),
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                report.save(update_fields=["backup_info", "update_at"])

                valid_instances.append(
                    {
                        "cluster": cluster,
                        "instance": instance,
                        "full_backup": full_backup,
                        "days_used": days_used,
                        "recovery_time_point": recovery_time_point,
                        "binlog_summary": binlog_summary,
                        "report": report,
                    }
                )
                continue

            if failure_kind == ValidationFailureKind.ENV_SUPPRESSED:
                logger.info(_("Validation skipped without report: {}").format(fail_reason))
                continue

            report = self._create_report(cluster, instance)
            stage = (
                TaskStage.BACKUP_INVALID if failure_kind == ValidationFailureKind.BACKUP_INVALID else TaskStage.SKIPPED
            )
            report.mark(
                stage,
                task_message=_fmt_task_msg(_("Validation failed: {}").format(fail_reason)),
            )

        if not valid_instances:
            logger.info(_("No instances with valid backup found"))
            return

        logger.info(_("Found {} instances with valid backup: {}").format(len(valid_instances), valid_instances))

        # Generate exercise ticket
        try:
            self._create_ticket(valid_instances)
        except Exception as e:
            logger.exception(_("Failed to create exercise ticket: {}").format(str(e)))
            for item in valid_instances:
                report: Report = item["report"]
                report.mark(TaskStage.TICKET_GEN_FAILED, task_message=_fmt_task_msg(str(e)))

    def init_candidates_queue(self):
        """
        Initialize the candidates queue in Redis

        Workflow:
        1. Acquire lock on the Redis key
        2. Clear the existing Redis queue
        3. Calculate new candidates
        4. Load new candidates into the queue
        5. Release lock

        Returns:
            bool: True if successful, False otherwise
        """
        logger.info(_("Initializing candidates queue"))
        lock_acquired = RedisConn.set(
            REDIS_CANDIDATES_LOCK_KEY, "locked", nx=True, ex=REDIS_LOCK_TIMEOUT  # Expire after timeout
        )

        if not lock_acquired:
            logger.warning(_("Failed to acquire lock for candidates queue initialization"))
            return

        try:
            # Clear existing queue
            old_count = RedisConn.llen(REDIS_CANDIDATES_QUEUE_KEY)
            if old_count > 0:
                RedisConn.delete(REDIS_CANDIDATES_QUEUE_KEY)
                logger.info(_("Cleared {} old candidates from queue").format(old_count))

            # Calculate new candidates
            candidate_ids = self._calculate_candidates()

            if not candidate_ids:
                logger.warning(_("No candidate clusters found"))
                return

            # Push candidates into Redis queue using pipeline for efficiency
            pipeline = RedisConn.pipeline()

            for i in range(0, len(candidate_ids), RPUSH_BATCH_SIZE):
                batch = candidate_ids[i : i + RPUSH_BATCH_SIZE]
                pipeline.rpush(REDIS_CANDIDATES_QUEUE_KEY, *batch)

            pipeline.execute()

            logger.info(_("Successfully loaded {} candidates into queue using pipeline").format(len(candidate_ids)))

            return

        except Exception as e:
            logger.exception(_("Error initializing candidates queue: {}").format(str(e)))
            return

        finally:
            # Release lock
            RedisConn.delete(REDIS_CANDIDATES_LOCK_KEY)
            logger.debug(_("Released lock for candidates queue"))

    def _pick_target_instances(self, num: int) -> Tuple[List[dict], List[tuple]]:
        """
        Pick target instances for rollback exercise

        Returns:
            List[dict]: List of selected instances with cluster info
            Format: [{"cluster": Cluster, "instance": StorageInstance}, ...]
        """
        match self.config.mode:
            case RedisRollbackExerciseMode.SPECIFIED:
                return self._get_specified_instances(num)
            case RedisRollbackExerciseMode.RANDOM:
                return self._consume_from_queue(num)

    def _validate_instance(
        self,
        instance_ip: str,
        instance_port: int,
        cluster: Cluster,
        rollback_days: List[int],
        backup_check_instance: Optional[StorageInstance] = None,
    ) -> tuple:
        """
        Validate if instance is suitable for rollback exercise.

        Validations:
        1. No existing temp instance (not destroyed) in tb_tendis_rollback_tasks
        2. No undone conflicting ticket
        3. Backup availability (full backup + binlog when applicable)
        4. Recent master-slave switch downgrades missing backup to skipped

        Returns:
            tuple: (is_valid, full_backup_log, days_used, recovery_time_point,
                    binlog_summary, fail_reason, failure_kind)

            ``failure_kind`` is a ``ValidationFailureKind`` (or None when valid):
            - BACKUP_INVALID -> caller should mark report as BACKUP_INVALID (ABNORMAL)
            - ENV_SKIPPED    -> caller should mark report as SKIPPED (WARNING)
            - ENV_SUPPRESSED -> caller should log only, without report noise
        """
        cluster_id = cluster.id

        # 1. Temp instance check
        existing_temp_instances = TbTendisRollbackTasks.objects.filter(
            prod_cluster_id=cluster_id,
            destroyed_status__in=[DestroyedStatus.NOT_DESTROYED, DestroyedStatus.DESTROYING],
        )
        if existing_temp_instances.exists():
            fail_reason = _("Cluster {} has existing temp instances (not destroyed)").format(cluster_id)
            return False, None, None, None, None, fail_reason, ValidationFailureKind.ENV_SUPPRESSED

        # 2. Undone exclusive ticket check
        exclusive_infos = ClusterOperateRecord.objects.has_exclusive_operations_with_lock(
            TicketType.REDIS_ROLLBACK_EXERCISE,
            cluster_id,
        )
        if exclusive_infos:
            exclusive_tickets = [
                "{}({})".format(info["exclusive_ticket"].ticket_type, info["exclusive_ticket"].id)
                for info in exclusive_infos
            ]
            fail_reason = _("Cluster {} has exclusive active tickets: {}").format(
                cluster_id, ", ".join(exclusive_tickets)
            )
            return False, None, None, None, None, fail_reason, ValidationFailureKind.ENV_SUPPRESSED

        # 3. Backup check (full + binlog when applicable)
        (
            has_backup,
            full_backup,
            days_used,
            recovery_time_point,
            binlog_summary,
            backup_fail_reason,
        ) = self._instance_has_backup(
            instance_ip=instance_ip,
            instance_port=instance_port,
            cluster=cluster,
            rollback_days=rollback_days,
        )
        if not has_backup:
            fail_reason = _("Instance {}:{} - No valid backup across rollback days {}: {}").format(
                instance_ip, instance_port, rollback_days, backup_fail_reason or _("unknown")
            )
            switch_hours = self._recent_master_slave_switch_hours(backup_check_instance)
            if switch_hours is not None:
                fail_reason = _(
                    "{} (possible recent master-slave switch, {}h ago; backup file may be missing)"
                ).format(fail_reason, switch_hours)
                return False, None, None, None, None, fail_reason, ValidationFailureKind.ENV_SKIPPED
            # No recent switch — genuine backup missing.
            return False, None, None, None, None, fail_reason, ValidationFailureKind.BACKUP_INVALID

        return True, full_backup, days_used, recovery_time_point, binlog_summary, None, None

    @staticmethod
    def _recent_master_slave_switch_hours(slave_instance: Optional[StorageInstance]) -> Optional[int]:
        """Return tuple age in hours when the slave was attached after a recent switch."""
        if slave_instance is None:
            return None

        tuple_obj = slave_instance.as_receiver.order_by("-create_at").first()
        if tuple_obj is None:
            return None

        threshold_hours = RedisBackupCheckConfig.from_settings().min_instance_age_hours
        tuple_age = django_timezone.now() - tuple_obj.create_at
        if tuple_age < timedelta(hours=threshold_hours):
            return int(tuple_age.total_seconds() // 3600)
        return None

    def _create_ticket(self, valid_instances: List[dict]):
        """
        Create REDIS_ROLLBACK_EXERCISE drill ticket with selected instances
        """
        logger.info(_("Creating drill ticket for {} instances").format(len(valid_instances)))

        # Prepare infos for each instance
        infos = []

        for item in valid_instances:
            cluster = item["cluster"]
            instance: StorageInstance = item["instance"]
            recovery_time_point = item["recovery_time_point"]
            report: Report = item["report"]

            logger.info(_("instance: {}").format(instance))

            # Prepare instance info for ticket
            instance_info = {
                "cluster_id": cluster.id,
                "instance_ip": instance.machine.ip,
                "instance_port": instance.port,
                "recovery_time_point": datetime2str(recovery_time_point),
                "report_id": report.id,  # Link to report record for status updates
            }
            infos.append(instance_info)

        try:
            ticket = Ticket.create_ticket(
                ticket_type=TicketType.REDIS_ROLLBACK_EXERCISE,
                creator="system",
                remark=_("[自动发起] Redis 回档演练"),
                bk_biz_id=self.config.bk_biz_id,
                details={
                    "infos": infos,
                    "drill_config": {
                        "polling_interval": self.config.polling_interval,
                        "polling_timeout": self.config.polling_timeout,
                        "error_ignorable": self.config.error_ignorable,
                        "preserve_scene_shield_minutes": self.config.preserve_scene_shield_minutes,
                    },
                },
                auto_execute=True,
            )

            logger.info(
                _("Successfully created drill ticket {} for {} instances:").format(ticket.id, len(valid_instances))
            )

            for item in valid_instances:
                report: Report = item["report"]
                report.ticket_id = ticket.id
                report.mark(TaskStage.TICKET_GENERATED)

        except Exception as e:
            logger.exception(_("Failed to create drill ticket: {}").format(str(e)))
            # Mark all reports as TICKET_GEN_FAILED
            for item in valid_instances:
                report: Report = item["report"]
                report.mark(TaskStage.TICKET_GEN_FAILED, task_message=_fmt_task_msg(str(e)))

    def _create_report(self, cluster: Cluster, instance: StorageInstance = None) -> Report:
        """
        Create a Report record for tracking the exercise task

        Args:
            cluster: The cluster being exercised
            instance: The master instance for rollback (optional, can be None for skipped clusters)

        Returns:
            Report: The created report record
        """
        report = Report.objects.create(
            bk_biz_id=cluster.bk_biz_id,
            bk_cloud_id=cluster.bk_cloud_id,
            cluster_id=cluster.id,
            cluster_domain=cluster.immute_domain,
            cluster_type=cluster.cluster_type,
            instance_ip=instance.machine.ip if instance else None,
            instance_port=instance.port if instance else None,
            redis_version=(instance.version or "") if instance else "",
            task_stage=TaskStage.TASK_GENERATED,
            creator="system",
            updater="system",
        )
        return report

    def _rollback_exercise_candidate_queryset(self):
        """
        Build the base Cluster queryset shared by random candidate calculation and
        SPECIFIED-mode biz discovery: applies cluster/biz ignore lists, allowed
        cluster types, and ONLINE phase filtering.
        """
        queryset = Cluster.objects.all()

        if self.config.clusters_ignored:
            queryset = queryset.exclude(id__in=self.config.clusters_ignored)

        if self.config.bizs_ignored:
            queryset = queryset.exclude(bk_biz_id__in=self.config.bizs_ignored)

        if self.config.bk_cloud_ids:
            queryset = queryset.filter(bk_cloud_id__in=self.config.bk_cloud_ids)

        if self.config.cluster_types:
            queryset = queryset.filter(cluster_type__in=self.config.cluster_types)

        return queryset.filter(phase=ClusterPhase.ONLINE.value)

    def _calculate_candidates(self) -> List[int]:
        """
        Filter from Cluster to get candidate cluster IDs

        Strategy:
        1. Skip clusters whose bizs or itself are ignored
        2. Skip clusters not running (only include ONLINE phase)
        3. Skip clusters not in config.cluster_types
        4. Collect up to config.batch_size cluster_ids as candidates

        Returns:
            List[int]: List of candidate cluster IDs
        """
        logger.info(_("Calculating candidate clusters for rollback exercise"))

        queryset = self._rollback_exercise_candidate_queryset()

        total_candidates = queryset.count()
        logger.info(_("Found {} total candidate clusters").format(total_candidates))
        if total_candidates <= self.config.batch_size:
            candidate_ids = list(queryset.only("id").values_list("id", flat=True))
        else:
            all_ids = list(queryset.only("id", "bk_biz_id").values_list("id", "bk_biz_id"))
            random.shuffle(all_ids)  # Mix the order first to avoid database ordering bias
            candidate_ids = self._weighted_random_selection(all_ids, self.config.batch_size)

        logger.info(
            _("Selected {} candidate clusters (batch_size: {})").format(
                len(candidate_ids),
                self.config.batch_size,
            )
        )

        return candidate_ids

    def _weighted_random_selection(self, cluster_id_biz_pairs: List[Tuple[int, int]], count: int) -> List[int]:
        """
        Perform weighted random selection on cluster candidates.

        Weighting strategy (multiplicative):
        - Default weight: 1.0
        - High priority biz: * config.weight_multiplier_high_priority_biz (default 2.0x)
        - Previously failed cluster: * config.weight_multiplier_previously_failed (default 3.0x)
        - Combined: factors are multiplied (e.g., high_priority + failed = 2.0 * 3.0 = 6.0x)

        Args:
            cluster_id_biz_pairs: List of (cluster_id, bk_biz_id) tuples
            count: Number of clusters to select

        Returns:
            List[int]: Selected cluster IDs
        """
        if not cluster_id_biz_pairs:
            return []

        cluster_ids = [pair[0] for pair in cluster_id_biz_pairs]
        cluster_biz_map = {pair[0]: pair[1] for pair in cluster_id_biz_pairs}

        previously_failed_clusters, _q = Report.get_previously_failed_clusters()
        not_exercised_clusters, _q = Report.get_not_exercised_clusters(
            cluster_ids, self.config.not_exercised_days_threshold
        )
        high_priority_bizs: Set[int] = set(self.config.bizs_high_priority or [])

        # Weight = base * high_priority_multiplier * failed_multiplier * not_exercised_multiplier
        weights = [
            1.0
            * (self.config.weight_multiplier_high_priority_biz if cluster_biz_map[cid] in high_priority_bizs else 1.0)
            * (self.config.weight_multiplier_previously_failed if cid in previously_failed_clusters else 1.0)
            * (self.config.weight_multiplier_not_exercised if cid in not_exercised_clusters else 1.0)
            for cid in cluster_ids
        ]

        logger.info(
            _(
                "Weighted selection: {} clusters, {} high priority biz clusters, "
                "{} previously failed clusters, {} not exercised in {} days"
            ).format(
                len(cluster_ids),
                sum(1 for cid in cluster_ids if cluster_biz_map[cid] in high_priority_bizs),
                len(previously_failed_clusters),
                sum(1 for cid in cluster_ids if cid in not_exercised_clusters),
                self.config.not_exercised_days_threshold,
            )
        )

        # Perform weighted random sampling without replacement
        return self._weighted_sample_without_replacement(cluster_ids, weights, count)

    def _weighted_sample_without_replacement(self, items: List[int], weights: List[float], count: int) -> List[int]:
        """
        Perform weighted random sampling without replacement.

        Uses the Efraimidis-Spirakis algorithm (A-Res) which achieves O(n log k)
        complexity instead of O(n * k) from iterative approach.

        Algorithm: For each item, compute key = random() ^ (1/weight), then
        select the top-k items with the highest keys. We use the mathematically
        equivalent form: key = log(random()) / weight for numerical stability.

        Reference: https://utopia.duth.gr/~pefraimi/research/data/2007EncssAlgorithms.pdf

        Args:
            items: List of items to sample from
            weights: Corresponding weights for each item
            count: Number of items to select

        Returns:
            List[int]: Selected items
        """
        if count >= len(items):
            return items[:]

        if count == 0:
            return []

        # Handle zero weights by replacing with tiny positive value
        safe_weights = [w if w > 0 else 1e-10 for w in weights]

        # Efraimidis-Spirakis algorithm: key_i = random() ^ (1/weight_i)
        # Equivalent to: key_i = log(random()) / weight_i (for numerical stability)
        # We want top-k highest keys, which means top-k highest log(random())/weight
        # Since log(random()) is negative, highest = least negative = closest to 0
        keys = [math.log(random.random()) / w for w in safe_weights]

        # Get indices of top-k highest keys (use nlargest for O(n log k) complexity)
        top_k_indices = heapq.nlargest(count, range(len(keys)), key=lambda i: keys[i])

        return [items[i] for i in top_k_indices]

    def _resolve_specified_cluster(self, cluster: Cluster) -> Optional[dict]:
        """
        Resolve the slave/master pair for a cluster in SPECIFIED mode.

        Returns a selection dict ready for ``_pick_target_instances`` consumers, or
        ``None`` when no slave instance is available (caller should record a skip).
        """
        slave_instance = (
            cluster.storageinstance_set.filter(instance_inner_role=InstanceInnerRole.SLAVE).order_by("?").first()
        )
        if not slave_instance:
            return None
        master_instance = slave_instance.as_receiver.get().ejector
        logger.info(
            _("Selected slave {} for backup check and its paired master {} for rollback from cluster {}").format(
                slave_instance.ip_port, master_instance.ip_port, cluster.immute_domain
            )
        )
        return {"cluster": cluster, "instance": master_instance, "backup_check_instance": slave_instance}

    def _get_specified_instances(self, num: int) -> Tuple[List[dict], List[tuple]]:
        """
        Resolve target instances for SPECIFIED mode.

        Behavior depends on ``specified_domains`` and ``specified_bizs``:
        - domains set, bizs unset: exercise every listed domain (legacy behavior).
        - domains set, bizs set: exercise domains whose cluster bk_biz_id is in
          ``specified_bizs``; others are recorded as skipped.
        - domains unset, bizs set: discover ONLINE candidate clusters in
          ``specified_bizs`` (sharing the random-mode candidate filters) and
          weighted-sample up to ``num`` so not-recently-exercised clusters are
          favored.
        - domains unset, bizs unset: nothing to do; warn and return empty.
        """
        result: List[dict] = []
        skipped_clusters: List[tuple] = []
        domains = self.config.specified_domains or []
        bizs: Set[int] = set(self.config.specified_bizs or [])
        bk_cloud_ids: Set[int] = set(self.config.bk_cloud_ids or [])

        if domains:
            for domain in domains:
                cluster = Cluster.objects.get(immute_domain=domain)
                if bizs and cluster.bk_biz_id not in bizs:
                    skip_msg = _("Cluster {} bk_biz_id {} not in specified_bizs {}").format(
                        cluster.immute_domain, cluster.bk_biz_id, sorted(bizs)
                    )
                    skipped_clusters.append((cluster, skip_msg))
                    continue
                if bk_cloud_ids and cluster.bk_cloud_id not in bk_cloud_ids:
                    skip_msg = _("Cluster {} bk_cloud_id {} not in bk_cloud_ids {}").format(
                        cluster.immute_domain, cluster.bk_cloud_id, sorted(bk_cloud_ids)
                    )
                    skipped_clusters.append((cluster, skip_msg))
                    continue
                selection = self._resolve_specified_cluster(cluster)
                if selection is None:
                    skip_msg = _("Cluster {} has no slave instance").format(cluster.immute_domain)
                    skipped_clusters.append((cluster, skip_msg))
                    continue
                result.append(selection)
            return result, skipped_clusters

        if not bizs:
            logger.warning(_("SPECIFIED mode requires specified_domains or specified_bizs; both are empty, skipping"))
            return result, skipped_clusters

        queryset = self._rollback_exercise_candidate_queryset().filter(bk_biz_id__in=bizs)
        all_pairs: List[Tuple[int, int]] = list(queryset.values_list("id", "bk_biz_id"))
        if not all_pairs:
            logger.warning(_("No candidate clusters found in specified_bizs {}").format(sorted(bizs)))
            return result, skipped_clusters

        random.shuffle(all_pairs)  # Mix order first to avoid database ordering bias
        selected_ids = self._weighted_random_selection(all_pairs, min(num, len(all_pairs)))
        logger.info(
            _("Discovered {} clusters in specified_bizs {}, selected {} via weighted sampling").format(
                len(all_pairs), sorted(bizs), len(selected_ids)
            )
        )

        for cluster_id in selected_ids:
            try:
                cluster = Cluster.objects.get(id=cluster_id)
            except Cluster.DoesNotExist:
                logger.warning(_("Cluster {} no longer exists, skipping").format(cluster_id))
                continue
            selection = self._resolve_specified_cluster(cluster)
            if selection is None:
                skip_msg = _("Cluster {} has no slave instance").format(cluster.immute_domain)
                skipped_clusters.append((cluster, skip_msg))
                continue
            result.append(selection)

        return result, skipped_clusters

    def _consume_from_queue(self, num: int) -> Tuple[List[dict], List[tuple]]:
        """
        Pops candidate clusters from queue.

        Returns:
        - result: Selected instances {cluster, instance, backup_instance}
        - skipped_clusters: Clusters skipped for some reasons
        """
        result = []
        skipped_clusters = []
        if RedisConn.exists(REDIS_CANDIDATES_LOCK_KEY):
            logger.warning(_("Candidates queue is locked (being initialized), skipping this round"))
            return result

        queue_length = RedisConn.llen(REDIS_CANDIDATES_QUEUE_KEY)
        if queue_length == 0:
            logger.warning(_("Candidates queue is empty, need to initialize first"))
            return result

        logger.info(_("Candidates queue has {} items, popping up {} items").format(queue_length, num))

        pop_count = min(num, queue_length)

        for _i in range(pop_count):
            candidate_data = RedisConn.lpop(REDIS_CANDIDATES_QUEUE_KEY)

            if not candidate_data:
                break

            try:
                cluster_id = int(candidate_data)
                cluster = Cluster.objects.get(id=cluster_id)
                if self.config.bk_cloud_ids and cluster.bk_cloud_id not in self.config.bk_cloud_ids:
                    skip_msg = _("Cluster {} bk_cloud_id {} not in bk_cloud_ids {}").format(
                        cluster.immute_domain, cluster.bk_cloud_id, sorted(self.config.bk_cloud_ids)
                    )
                    skipped_clusters.append((cluster, skip_msg))
                    continue
                if cluster.phase != ClusterPhase.ONLINE.value:
                    skip_msg = _("Cluster {} is offline (phase: {})").format(cluster.immute_domain, cluster.phase)
                    skipped_clusters.append((cluster, skip_msg))
                    continue

                slave_instance = (
                    cluster.storageinstance_set.filter(instance_inner_role=InstanceInnerRole.SLAVE)
                    .order_by("?")
                    .first()
                )
                if not slave_instance:
                    skip_msg = _("Cluster {} has no slave instance").format(cluster.immute_domain)
                    skipped_clusters.append((cluster, skip_msg))
                    continue
                master_instance = slave_instance.as_receiver.get().ejector

                result.append(
                    {"cluster": cluster, "instance": master_instance, "backup_check_instance": slave_instance}
                )

            except Exception as e:
                logger.warning(_("Error processing candidate {}: {}, skipping").format(candidate_data, str(e)))
                continue

        logger.info(_("Successfully collected {} candidate instances from queue").format(len(result)))
        return result, skipped_clusters

    def _instance_has_backup(
        self,
        instance_ip: str,
        instance_port: int,
        cluster: Cluster,
        rollback_days: List[int],
    ) -> tuple:
        """
        Check if instance has valid backup (full + binlog when applicable) by querying bklog.

        For SSD / Tendisplus we additionally call ``query_binlog_from_bklog`` over the same
        window the rollback flow will later download (see
        ``RedisDataStructureFlow.get_backupfile``); that helper enforces consecutivity and
        the >= 2 binlog-files-per-instance rule, so any missing/duplicate index surfaces
        here as a backup-invalid signal rather than a mid-flow failure.

        Returns:
            tuple: (has_backup, full_backup_log, days_used, recovery_time_point, binlog_summary, fail_reason)
        """
        cluster_id = cluster.id
        cluster_type = cluster.cluster_type
        logger.debug(
            _("Checking backup records for instance {}:{} (type: {})").format(instance_ip, instance_port, cluster_type)
        )

        has_binlog = self._cluster_type_has_binlog(cluster_type)
        tendis_type = self._resolve_tendis_type(cluster_type)
        kvstorecount = self._get_kvstorecount(cluster) if is_tendisplus_instance_type(cluster_type) else None
        offset_minutes = self.config.binlog_replay_minutes if has_binlog else self.config.no_binlog_offset_minutes

        sorted_days = sorted(rollback_days)
        handler = DataStructureHandler(cluster_id=cluster_id)
        last_fail_reason = None

        for days_before in sorted_days:
            rollback_time = django_timezone.now() - timedelta(days=days_before)
            try:
                backup_log = handler.query_latest_backup_log(
                    rollback_time=rollback_time,
                    host_ip=instance_ip,
                    port=instance_port,
                )
            except Exception as e:
                last_fail_reason = _("Full backup query error at {} days before: {}").format(days_before, str(e))
                logger.warning(
                    _("Error querying full backup for instance {}:{} at {} days before: {}").format(
                        instance_ip, instance_port, days_before, str(e)
                    )
                )
                continue

            if not (backup_log and backup_log.get("status") == "to_backup_system_success"):
                last_fail_reason = _("No successful full backup at {} days before").format(days_before)
                logger.debug(
                    _("No valid full backup for instance {}:{} at {} days before").format(
                        instance_ip, instance_port, days_before
                    )
                )
                continue

            logger.info(
                _("Found valid full backup for instance {}:{} at {} days before, backup uptime: {}").format(
                    instance_ip, instance_port, days_before, backup_log.get("uptime")
                )
            )

            recovery_time_point = str2datetime(backup_log["uptime"]) + timedelta(minutes=offset_minutes)

            if not has_binlog:
                return True, backup_log, days_before, recovery_time_point, None, None

            # SSD / Tendisplus: validate binlog over [file_last_mtime, recovery_time_point]
            try:
                binlog_files = handler.query_binlog_from_bklog(
                    start_time=str2datetime(backup_log["file_last_mtime"]),
                    end_time=recovery_time_point,
                    host_ip=instance_ip,
                    port=instance_port,
                    kvstorecount=kvstorecount,
                    tendis_type=tendis_type,
                )
            except AppBaseException as e:
                last_fail_reason = _("Binlog invalid at {} days before: {}").format(days_before, str(e))
                logger.warning(
                    _("Binlog validation failed for {}:{} at {} days before: {}").format(
                        instance_ip, instance_port, days_before, str(e)
                    )
                )
                continue
            except Exception as e:
                last_fail_reason = _("Binlog query error at {} days before: {}").format(days_before, str(e))
                logger.warning(
                    _("Error querying binlog for {}:{} at {} days before: {}").format(
                        instance_ip, instance_port, days_before, str(e)
                    )
                )
                continue

            binlog_summary = self._summarize_binlog(binlog_files)
            return True, backup_log, days_before, recovery_time_point, binlog_summary, None

        logger.warning(
            _("No valid backup found for instance {}:{} across all rollback days {}").format(
                instance_ip, instance_port, sorted_days
            )
        )
        return False, None, None, None, None, last_fail_reason

    @staticmethod
    def _cluster_type_has_binlog(cluster_type: str) -> bool:
        """Whether this cluster type produces binlog (i.e. tendis_type is SSD or Tendisplus)."""
        return is_tendisssd_instance_type(cluster_type) or is_tendisplus_instance_type(cluster_type)

    @staticmethod
    def _resolve_tendis_type(cluster_type: str) -> str:
        """Mirror RedisDataStructureFlow.get_tendis_type_by_cluster_type so binlog query
        receives the same tendis_type the rollback flow will use later."""
        if is_redis_instance_type(cluster_type):
            return ClusterType.RedisInstance.value
        if is_tendisplus_instance_type(cluster_type):
            return ClusterType.TendisplusInstance.value
        if is_tendisssd_instance_type(cluster_type):
            return ClusterType.TendisSSDInstance.value
        raise NotImplementedError("Not supported tendis type: %s" % cluster_type)

    @staticmethod
    def _get_kvstorecount(cluster: Cluster) -> Optional[str]:
        """Fetch tendisplus kvstorecount from DBConfig (mirrors
        RedisDataStructureFlow.__get_cluster_config so binlog completeness check
        runs over the same kvstore set)."""
        try:
            data = DBConfigApi.query_conf_item(
                params={
                    "bk_biz_id": str(cluster.bk_biz_id),
                    "level_name": LevelName.CLUSTER,
                    "level_value": cluster.immute_domain,
                    "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
                    "conf_file": cluster.major_version,
                    "conf_type": ConfigTypeEnum.DBConf,
                    "namespace": cluster.cluster_type,
                    "format": FormatType.MAP,
                }
            )
            return data["content"].get("kvstorecount")
        except Exception as e:
            logger.warning(
                _("Failed to fetch kvstorecount for tendisplus cluster {}: {}").format(cluster.immute_domain, str(e))
            )
            return None

    @staticmethod
    def _summarize_binlog(binlog_files: List[dict]) -> dict:
        """Compact abstraction of binlog list (could be hundreds of files per instance/day)."""
        if not binlog_files:
            return {"count": 0, "total_size_bytes": 0}

        sized = [int(b.get("size") or 0) for b in binlog_files]
        mtimes = [b.get("file_last_mtime") for b in binlog_files if b.get("file_last_mtime")]
        return {
            "count": len(binlog_files),
            "total_size_bytes": sum(sized),
            "earliest_start_time": min(mtimes) if mtimes else None,
            "latest_start_time": max(mtimes) if mtimes else None,
            "first_file": binlog_files[0].get("file_name"),
            "last_file": binlog_files[-1].get("file_name"),
        }
