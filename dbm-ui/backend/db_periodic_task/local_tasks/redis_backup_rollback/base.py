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
import random
from dataclasses import dataclass, field
from datetime import timedelta
from enum import StrEnum
from typing import List, Optional

from django.utils import timezone as django_timezone
from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterPhase, DestroyedStatus, InstanceInnerRole
from backend.db_meta.models import Cluster, StorageInstance
from backend.db_services.redis.rollback.handlers import DataStructureHandler
from backend.db_services.redis.rollback.models import TbTendisRollbackTasks
from backend.ticket.builders.common.base import IpSource
from backend.ticket.constants import TICKET_RUNNING_STATUS_SET, TicketType
from backend.ticket.models import ClusterOperateRecord, SystemSettings, Ticket
from backend.utils.redis import RedisConn

logger = logging.getLogger("root")

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
    switch: bool = False
    mode: RedisRollbackExerciseMode = RedisRollbackExerciseMode.RANDOM
    bk_biz_id: int = 0  # The biz where the drill ticket locates

    # Mode - Specifed
    specified_domains: Optional[List[str]] = None  # Customed targets [clusters]

    # Mode - Random
    batch_size: int = 2000  # Count of clusters to exercise each week
    bizs_high_priority: Optional[List[int]] = None  # Customed bizs with high priority
    clusters_ignored: Optional[List[int]] = None  # Customed clusters(id) to ignore
    bizs_ignored: Optional[List[int]] = None  # Customed bizs to ignore
    cluster_types: Optional[List[str]] = None  # Customed ClusterTypes to exercise

    # Extra
    max_instances: int = 10  # Each round
    rollback_days: List[int] = field(default_factory=lambda: [20, 10, 5])
    polling_interval: int = 10  # sec
    polling_timeout: int = 3600  # sec


class RedisRollbackExercise:
    """
    Redis rollback exercise task generator
    """

    def _init_config(self) -> RedisRollbackExerciseConfig:
        """Initialize configuration from system settings"""
        config_dict = SystemSettings.get_setting_value("REDIS_ROLLBACK_EXERCISE", {})
        config = RedisRollbackExerciseConfig(**config_dict) if config_dict else RedisRollbackExerciseConfig()
        logger.info(_("Redis rollback exercise settings: {}").format(config))
        return config

    def __init__(self):
        self.config = self._init_config()

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
            logger.debug(_("Excluding clusters: {}").format(self.config.clusters_ignored))

        if self.config.bizs_ignored:
            queryset = queryset.exclude(bk_biz_id__in=self.config.bizs_ignored)
            logger.debug(_("Excluding bizs: {}").format(self.config.bizs_ignored))

        if self.config.cluster_types:
            queryset = queryset.filter(cluster_type__in=self.config.cluster_types)
            logger.debug(_("Including cluster types: {}").format(self.config.cluster_types))

        queryset = queryset.filter(phase=ClusterPhase.ONLINE.value)

        total_candidates = queryset.count()
        logger.info(_("Found {} total candidate clusters").format(total_candidates))
        if total_candidates <= self.config.batch_size:
            candidate_ids = list(queryset.only("id").values_list("id", flat=True))
        else:
            all_ids = list(queryset.only("id").values_list("id", flat=True))
            candidate_ids = random.sample(all_ids, self.config.batch_size)

        logger.info(
            _("Selected {} candidate clusters (batch_size: {})").format(
                len(candidate_ids),
                self.config.batch_size,
            )
        )

        return candidate_ids

    def init_candidates_queue(self) -> bool:
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
            return False

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
                return True

            # Push candidates into Redis queue using pipeline for efficiency
            pipeline = RedisConn.pipeline()

            for i in range(0, len(candidate_ids), RPUSH_BATCH_SIZE):
                batch = candidate_ids[i : i + RPUSH_BATCH_SIZE]
                pipeline.rpush(REDIS_CANDIDATES_QUEUE_KEY, *batch)

            pipeline.execute()

            logger.info(_("Successfully loaded {} candidates into queue using pipeline").format(len(candidate_ids)))

            return True

        except Exception as e:
            logger.exception(_("Error initializing candidates queue: {}").format(str(e)))
            return False

        finally:
            # Release lock
            RedisConn.delete(REDIS_CANDIDATES_LOCK_KEY)
            logger.debug(_("Released lock for candidates queue"))

    def __get_specified_instances(self) -> List[dict]:
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

    def __get_random_instances(self, num: int) -> List[dict]:
        result = []
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
                    logger.warning(_("Cluster {} is offline, skipping").format(cluster.immute_domain))
                    continue

                slave_instance = (
                    cluster.storageinstance_set.filter(instance_inner_role=InstanceInnerRole.SLAVE)
                    .order_by("?")
                    .first()
                )
                if not slave_instance:
                    logger.warning(_("Cluster {} has no slave instance, skipping").format(cluster.immute_domain))
                    continue
                master_instance = slave_instance.as_receiver.get().ejector

                logger.info(
                    _(
                        (
                            "Selected slave {} for backup check and its paired master {} for rollback from cluster {}"
                        ).format(slave_instance.ip_port, master_instance.ip_port, cluster.immute_domain)
                    )
                )

                result.append(
                    {"cluster": cluster, "instance": master_instance, "backup_check_instance": slave_instance}
                )

            except Cluster.DoesNotExist:
                logger.warning(_("Cluster {} not found, skipping").format(cluster_id))
                continue
            except Exception as e:
                logger.warning(_("Error processing candidate {}: {}, skipping").format(candidate_data, str(e)))
                continue

        logger.info(_("Successfully collected {} candidate instances from queue").format(len(result)))
        return result

    def _pick_target_instances(self, num: int) -> List[dict]:
        """
        Pick target instances for rollback exercise

        Returns:
            List[dict]: List of selected instances with cluster info
            Format: [{"cluster": Cluster, "instance": StorageInstance}, ...]
        """
        match self.config.mode:
            case RedisRollbackExerciseMode.SPECIFIED:
                return self.__get_specified_instances()
            case RedisRollbackExerciseMode.RANDOM:
                return self.__get_random_instances(num)

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
        sorted_days = sorted(rollback_days, reverse=True)
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

    def _validate_instance(
        self, instance_ip: str, instance_port: int, cluster_id: int, cluster_type: str, rollback_days: List[int]
    ) -> tuple:
        """
        Validate if instance is suitable for rollback exercise

        Validations:
        1. Check if instance has valid backup
        2. Check if cluster has no existing temp instance (not destroyed) in tb_tendis_rollback_tasks
        """
        has_backup, backup_info, days_used = self._instance_has_backup(
            instance_ip=instance_ip,
            instance_port=instance_port,
            cluster_id=cluster_id,
            cluster_type=cluster_type,
            rollback_days=rollback_days,
        )
        if not has_backup:
            return False, None, None

        existing_temp_instances = TbTendisRollbackTasks.objects.filter(
            prod_cluster_id=cluster_id,
            destroyed_status__in=[DestroyedStatus.NOT_DESTROYED, DestroyedStatus.DESTROYING],
        )
        if existing_temp_instances.exists():
            logger.warning(
                _("Instance {}:{} validation failed: cluster {} has existing temp instances (not destroyed)").format(
                    instance_ip, instance_port, cluster_id
                )
            )
            return False, None, None

        undone_record = (
            ClusterOperateRecord.objects.filter(
                cluster_id=cluster_id,
                ticket__ticket_type=TicketType.REDIS_ROLLBACK_EXERCISE,
                ticket__status__in=TICKET_RUNNING_STATUS_SET,
            )
            .select_related("ticket")
            .first()
        )
        if undone_record:
            logger.warning(
                _("Instance {}:{} validation failed: cluster {} has undone rollback exercise ticket {}").format(
                    instance_ip, instance_port, cluster_id, undone_record.ticket.id
                )
            )
            return False, None, None

        logger.info(
            _("Instance {}:{} passed all validations with backup at {} days before").format(
                instance_ip, instance_port, days_used
            )
        )
        return True, backup_info, days_used

    def _create_drill_ticket(self, valid_instances: List[dict]):
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

            logger.info(_("instance: {}").format(instance))

            # Prepare instance info for ticket
            instance_info = {
                "cluster_id": cluster.id,
                "instance_ip": instance.machine.ip,
                "instance_port": instance.port,
                "recovery_time_point": backup_info.get("uptime", "") + timedelta(minutes=30),
                "task_id": 0,  # Link to task record for status updates, currently dry-run
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
                instance = item["instance"]
                logger.info(
                    _("  - Instance {} from cluster {}").format(instance.ip_port, item["cluster"].immute_domain)
                )

        except Exception as e:
            logger.exception(_("Failed to create drill ticket: {}").format(str(e)))

    def start(self):
        """
        Generate Redis rollback exercise tasks

        Main workflow:
        1. Pick n target instances
        2. For each instance, check if backup exists before rollback days
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

        if not self.config.switch:
            logger.info(_("Redis rollback exercise is disabled, exiting..."))
            return

        selected_instances = self._pick_target_instances(self.config.max_instances)
        if not selected_instances:
            logger.info(_("No instances selected for exercise"))
            return

        logger.info(_("Selected {} instances for exercise").format(len(selected_instances)))
        valid_instances = []

        for item in selected_instances:
            cluster = item["cluster"]
            instance: StorageInstance = item["instance"]  # Master instance for rollback
            backup_check_instance: StorageInstance = item.get(
                "backup_check_instance", instance
            )  # Slave for backup check

            try:
                is_valid, backup_info, days_used = self._validate_instance(
                    backup_check_instance.machine.ip,
                    backup_check_instance.port,
                    cluster.id,
                    cluster.cluster_type,
                    rollback_days=self.config.rollback_days,
                )

                if is_valid:
                    valid_instances.append(
                        {
                            "cluster": cluster,
                            "instance": instance,  # Master instance for rollback
                            "backup_info": backup_info,
                            "days_used": days_used,
                        }
                    )
                    logger.info(
                        _("Slave {} passed validation with backup at {} days, will use master {} for rollback").format(
                            backup_check_instance.ip_port, days_used, instance.ip_port
                        )
                    )
                else:
                    logger.warning(
                        _("Slave {} failed validation (no backup or existing temp instance), skipping cluster").format(
                            backup_check_instance.ip_port
                        )
                    )
                    logger.info(
                        _(
                            "Dry-run: changing state to SKIPPED for master instance({}) due to validation failure"
                        ).format(instance.ip_port)
                    )

            except Exception as e:
                logger.exception(_("Error validating instance {} {}").format(instance.ip_port, str(e)))
                logger.info(
                    _("Dry-run: changing state to SKIPPED for instance({}) due to exception").format(instance.ip_port)
                )
                continue

        if not valid_instances:
            logger.info(_("No instances with valid backup found"))
            return

        logger.info(_("Found {} instances with valid backup: {}").format(len(valid_instances), valid_instances))

        try:
            self._create_drill_ticket(valid_instances)
        except Exception as e:
            logger.exception(_("Failed to create drill ticket: {}").format(str(e)))
            logger.info(_("Dry-run: Mark tasks as GENERATE_TICKET_FAILED"))
