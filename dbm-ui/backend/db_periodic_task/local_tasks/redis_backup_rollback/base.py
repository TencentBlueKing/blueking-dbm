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
from dataclasses import dataclass, field
from datetime import timedelta
from enum import StrEnum
from typing import List, Optional, Set, Tuple

from django.utils import timezone as django_timezone
from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterPhase, DestroyedStatus, InstanceInnerRole
from backend.db_meta.models import Cluster, StorageInstance
from backend.db_report.enums import RedisRollbackExerciseTaskStage as TaskStage
from backend.db_report.models import RedisRollbackExerciseReport as Report
from backend.db_services.redis.rollback.handlers import DataStructureHandler
from backend.db_services.redis.rollback.models import TbTendisRollbackTasks
from backend.ticket.builders.common.base import ClusterType, IpSource
from backend.ticket.constants import TICKET_RUNNING_STATUS_SET, TicketType
from backend.ticket.models import ClusterOperateRecord, SystemSettings, Ticket
from backend.utils.redis import RedisConn
from backend.utils.time import datetime2str, str2datetime

logger = logging.getLogger("root")


def _fmt_task_msg(message: str) -> str:
    """Format task message with timestamp prefix [yyyy-mm-dd hh:mm:ss]"""
    timestamp = django_timezone.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"[{timestamp}] {message}"


# Candidates queue configurations
REDIS_CANDIDATES_QUEUE_KEY = "redis_rollback_exercise:candidates_queue"
REDIS_CANDIDATES_LOCK_KEY = "redis_rollback_exercise:candidates_lock"
REDIS_LOCK_TIMEOUT = 600  # 10 minutes
RPUSH_BATCH_SIZE = 500


class RedisRollbackExerciseMode(StrEnum):
    SPECIFIED = "specified"
    RANDOM = "random"


@dataclass
class RedisRollbackExerciseConfig:
    """
    Configuration of Redis rollback exericse
    """

    # Meta Configs
    enabled: bool = False
    mode: RedisRollbackExerciseMode = RedisRollbackExerciseMode.RANDOM
    bk_biz_id: int = 0  # The biz where the drill ticket locates

    # Mode - Specifed
    specified_domains: Optional[List[str]] = None  # Customed targets [clusters]

    # Mode - Random
    batch_size: int = 2000  # Count of clusters to exercise each week
    bizs_high_priority: Optional[List[int]] = None  # Customed bizs with high priority
    clusters_ignored: Optional[List[int]] = None  # Customed clusters(id) to ignore
    bizs_ignored: Optional[List[int]] = None  # Customed bizs to ignore
    cluster_types: List[str] = field(
        default_factory=lambda: [
            ClusterType.TendisTwemproxyRedisInstance.value,  # TendisCache 集群
            ClusterType.TwemproxyTendisSSDInstance.value,  # TendisSSD 集群
            ClusterType.TendisRedisInstance.value,  # Redis 主从
            ClusterType.TendisPredixyRedisCluster.value,
            ClusterType.TendisPredixyTendisplusCluster.value,
        ]
    )  # Customed ClusterTypes to exercise

    # Weighted selection: probability multipliers (how many times more likely to be selected)
    # Combined effect is multiplicative, e.g., high_priority + failed = 2.0 * 3.0 = 6x more likely
    weight_multiplier_high_priority_biz: float = 2.0  # 2x more likely than default
    weight_multiplier_previously_failed: float = 3.0  # 3x more likely than default
    weight_multiplier_not_exercised: float = 2.0  # 2x more likely for clusters not exercised recently
    not_exercised_days_threshold: int = 180  # Days threshold for "not exercised" status

    # Extra
    max_instances: int = 10  # Each round
    rollback_days: List[int] = field(default_factory=lambda: [7, 5, 3, 2, 1])
    polling_interval: int = 10  # sec
    polling_timeout: int = 3600  # sec


class RedisRollbackExercise:
    """
    Redis rollback exercise task generator
    """

    def __init__(self):
        self.config = self._init_config()

    def _init_config(self) -> RedisRollbackExerciseConfig:
        """Initialize configuration from system settings"""
        config_dict = SystemSettings.get_setting_value("REDIS_ROLLBACK_EXERCISE", {})
        config = RedisRollbackExerciseConfig(**config_dict) if config_dict else RedisRollbackExerciseConfig()
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
        - Apply resources
        - Create `redis_data_structure` flow to rollback each instance
        - Each rollback flow requires 1 machine with spec equal to instance selected
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

            report = self._create_report(cluster, instance)

            try:
                is_valid, backup_info, days_used, fail_reason = self._validate_instance(
                    backup_check_instance.machine.ip,
                    backup_check_instance.port,
                    cluster.id,
                    cluster.cluster_type,
                    rollback_days=self.config.rollback_days,
                )

                if is_valid:
                    report.backup_info = json.dumps(backup_info, indent=2, ensure_ascii=False)
                    report.save(update_fields=["backup_info", "update_at"])

                    valid_instances.append(
                        {
                            "cluster": cluster,
                            "instance": instance,
                            "backup_info": backup_info,
                            "days_used": days_used,
                            "report": report,
                        }
                    )
                else:
                    report.mark(
                        TaskStage.SKIPPED,
                        task_message=_fmt_task_msg(_("Validation failed: {}").format(fail_reason)),
                    )

            except Exception as e:
                logger.exception(_("Error validating instance {} {}").format(instance.ip_port, str(e)))
                report.mark(
                    TaskStage.SKIPPED,
                    task_message=_fmt_task_msg(_("Exception during validation: {}").format(str(e))),
                )
                continue

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
                return self._get_specified_instances(), []
            case RedisRollbackExerciseMode.RANDOM:
                return self._consume_from_queue(num)

    def _validate_instance(
        self, instance_ip: str, instance_port: int, cluster_id: int, cluster_type: str, rollback_days: List[int]
    ) -> tuple:
        """
        Validate if instance is suitable for rollback exercise

        Validations:
        1. Check if instance has valid backup
        2. Check if cluster has no existing temp instance (not destroyed) in tb_tendis_rollback_tasks
        3. Check if cluster has no undone conflicting ticket

        Returns:
            tuple: (is_valid: bool, backup_info: dict or None, days_used: int or None, fail_reason: str or None)
        """
        # 1. Backup check
        has_backup, backup_info, days_used = self._instance_has_backup(
            instance_ip=instance_ip,
            instance_port=instance_port,
            cluster_id=cluster_id,
            cluster_type=cluster_type,
            rollback_days=rollback_days,
        )
        if not has_backup:
            fail_reason = _("Instance {}:{} - No valid backup found across rollback days {}").format(
                instance_ip, instance_port, rollback_days
            )
            return False, None, None, fail_reason

        # 2. Temp instance check
        existing_temp_instances = TbTendisRollbackTasks.objects.filter(
            prod_cluster_id=cluster_id,
            destroyed_status__in=[DestroyedStatus.NOT_DESTROYED, DestroyedStatus.DESTROYING],
        )
        if existing_temp_instances.exists():
            fail_reason = _("Cluster {} has existing temp instances (not destroyed)").format(cluster_id)
            return False, None, None, fail_reason

        # 3. Undone ticket check
        conflicting_ticket_type = [
            TicketType.REDIS_ROLLBACK_EXERCISE,
            TicketType.REDIS_DATA_STRUCTURE,
            TicketType.REDIS_DATA_STRUCTURE_TASK_DELETE,
        ]
        undone_record = (
            ClusterOperateRecord.objects.filter(
                cluster_id=cluster_id,
                ticket__ticket_type__in=conflicting_ticket_type,
                ticket__status__in=TICKET_RUNNING_STATUS_SET,
            )
            .select_related("ticket")
            .first()
        )
        if undone_record:
            fail_reason = _("Cluster {} has undone {} ticket {}").format(
                cluster_id, undone_record.ticket.ticket_type, undone_record.ticket.id
            )
            return False, None, None, fail_reason

        return True, backup_info, days_used, None

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
            backup_info = item["backup_info"]
            report: Report = item["report"]

            recovery_time_point = str2datetime(backup_info["uptime"]) + timedelta(minutes=30)

            logger.info(_("instance: {}").format(instance))

            # Prepare instance info for ticket
            instance_info = {
                "cluster_id": cluster.id,
                "instance_ip": instance.machine.ip,
                "instance_port": instance.port,
                "recovery_time_point": datetime2str(recovery_time_point),
                "report_id": report.id,  # Link to report record for status updates
                "resource_spec": {
                    "redis": {
                        "count": 1,
                        "spec_id": instance.machine.spec_id,
                    }
                },
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
                    },
                    "ip_source": IpSource.RESOURCE_POOL.value,
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

        queryset = Cluster.objects.all()

        if self.config.clusters_ignored:
            queryset = queryset.exclude(id__in=self.config.clusters_ignored)

        if self.config.bizs_ignored:
            queryset = queryset.exclude(bk_biz_id__in=self.config.bizs_ignored)

        if self.config.cluster_types:
            queryset = queryset.filter(cluster_type__in=self.config.cluster_types)

        queryset = queryset.filter(phase=ClusterPhase.ONLINE.value)

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

    def _get_specified_instances(self) -> List[dict]:
        result = []
        for domain in self.config.specified_domains:
            cluster = Cluster.objects.get(immute_domain=domain)
            slave_instance = (
                cluster.storageinstance_set.filter(instance_inner_role=InstanceInnerRole.SLAVE).order_by("?").first()
            )
            master_instance = slave_instance.as_receiver.get().ejector
            logger.info(
                _("Selected slave {} for backup check and its paired master {} for rollback from cluster {}").format(
                    slave_instance.ip_port, master_instance.ip_port, cluster.immute_domain
                )
            )
            result.append({"cluster": cluster, "instance": master_instance, "backup_check_instance": slave_instance})
        return result

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
                cluster_id = eval(candidate_data)
                cluster = Cluster.objects.get(id=cluster_id)
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
        self, instance_ip: str, instance_port: int, cluster_id: int, cluster_type: str, rollback_days: List[int]
    ) -> tuple:
        """
        Check if instance has valid backups by querying from bklog

        Returns:
            tuple: (has_backup: bool, backup_info: dict or None, days_used: int or None)
        """
        logger.debug(
            _("Checking backup records for instance {}:{} (type: {})").format(instance_ip, instance_port, cluster_type)
        )
        sorted_days = sorted(rollback_days)
        handler = DataStructureHandler(cluster_id=cluster_id)
        for days_before in sorted_days:
            try:
                rollback_time = django_timezone.now() - timedelta(days=days_before)
                backup_log = handler.query_latest_backup_log(
                    rollback_time=rollback_time,
                    host_ip=instance_ip,
                    port=instance_port,
                )

                if backup_log and backup_log.get("status") == "to_backup_system_success":
                    logger.info(
                        _("Found valid backup for instance {}:{} at {} days before, backup time: {}").format(
                            instance_ip, instance_port, days_before, backup_log.get("uptime")
                        )
                    )
                    return True, backup_log, days_before
                else:
                    logger.debug(
                        _("No valid backup found for instance {}:{} at {} days before").format(
                            instance_ip, instance_port, days_before
                        )
                    )

            except Exception as e:
                logger.warning(
                    _("Error querying backup for instance {}:{} at {} days before: {}").format(
                        instance_ip, instance_port, days_before, str(e)
                    )
                )
                continue

        logger.warning(
            _("No valid backup found for instance {}:{} across all rollback days {}").format(
                instance_ip, instance_port, sorted_days
            )
        )
        return False, None, None
