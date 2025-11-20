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
from datetime import timedelta
from typing import List

from django.utils import timezone as django_timezone
from django.utils.translation import gettext as _

from backend.db_meta.enums import InstanceInnerRole
from backend.db_meta.models import Cluster, StorageInstance
from backend.db_services.redis.rollback.handlers import DataStructureHandler
from backend.ticket.builders.common.base import IpSource
from backend.ticket.constants import TicketType
from backend.ticket.models import SystemSettings, Ticket

from .config import RedisRollbackExerciseConfig, RedisRollbackExerciseMode

logger = logging.getLogger("root")


def probabilistic_selection(machines, weights, check_counts, n, decay_factor=1.0):
    scores = []
    for i, machine in enumerate(machines):
        base_score = max(0.1, 1 / (1 + check_counts[i] * decay_factor))
        final_score = weights[i] * base_score
        scores.append(final_score)

    selected = random.choices(population=machines, weights=scores, k=n)
    return selected


def pick_target_instances(config: RedisRollbackExerciseConfig, num: int) -> List[dict]:
    """
    Pick target instances for rollback exercise

    TODO: Strategy:
    0. Collect biz_ids into [HIGH, MEDIUM, LOW] classes
        - LOW: biz that has exercised within 48h or is in process
        - MEDIUM: biz that has exercising records but not in 48h
        - HIGH: biz that has never exerised before
        - extra: should filter out biz/cluster with blacklist
    1. Pick 2*num clusters from HIGH -> MEDUM -> LOW bizs
    2. Pick 1 master instance from each cluster selected
    3. Validations
        - Backup Check: make sure instance has backup before look back days
    4. Keep the instances passing the validations as `valid_instances`(no more than `num`)

    Returns:
        List[dict]: List of selected instances with cluster info
        Format: [{"cluster": Cluster, "instance": StorageInstance}, ...]
    """
    result = []
    match config.mode:
        case RedisRollbackExerciseMode.MIXED:
            raise NotImplementedError
        case RedisRollbackExerciseMode.SPECIFIED:
            for domains in config.targets.values():
                for domain in domains:
                    cluster = Cluster.objects.get(immute_domain=domain)
                    instance = (
                        cluster.storageinstance_set.filter(instance_inner_role=InstanceInnerRole.MASTER)
                        .order_by("?")
                        .first()
                    )
                    logger.info(
                        _("Selected instance {} from cluster {}").format(instance.ip_port, cluster.immute_domain)
                    )
                    result.append({"cluster": cluster, "instance": instance})
        case RedisRollbackExerciseMode.RANDOM:
            raise NotImplementedError

    return result


def instance_has_backup(
    instance_ip: str, instance_port: int, cluster_id: int, cluster_type: str, days_before: int = 20
) -> tuple:
    """
    Check if instance has valid backups by querying from bklog

    Returns:
        tuple: (has_backup: bool, backup_info: dict or None)
    """

    logger.debug(
        _("Checking backup records for instance {}:{} (type: {})").format(instance_ip, instance_port, cluster_type)
    )

    try:
        handler = DataStructureHandler(cluster_id=cluster_id)
        rollback_time = django_timezone.now() - timedelta(days=days_before)
        backup_log = handler.query_latest_backup_log(
            rollback_time=rollback_time,
            host_ip=instance_ip,
            port=instance_port,
        )

        if backup_log and backup_log.get("status") == "to_backup_system_success":
            logger.info(
                _("Found valid backup for instance {}:{}, backup time: {}").format(
                    instance_ip, instance_port, backup_log.get("start_time")
                )
            )

            return True, backup_log
        else:
            logger.warning(_("No valid backup found for instance {}:{}").format(instance_ip, instance_port))
            return False, None

    except Exception as e:
        logger.exception(_("Error querying backup for instance {}:{} {}").format(instance_ip, instance_port, str(e)))
        return False, None


def create_drill_ticket(config: RedisRollbackExerciseConfig, valid_instances: List[dict]):
    """
    Create REDIS_ROLLBACK_EXERCISE drill ticket with selected instances
    """
    logger.info(_("Creating drill ticket for {} instances").format(len(valid_instances)))

    # Prepare infos for each instance
    infos = []
    task_records = []

    for item in valid_instances:
        cluster = item["cluster"]
        instance: StorageInstance = item["instance"]
        backup_info = item["backup_info"]

        logger.info("instance:", instance)

        # Prepare instance info for ticket
        instance_info = {
            "cluster_id": cluster.id,
            "instance_ip": instance.machine.ip,
            "instance_port": instance.port,
            "recovery_time_point": backup_info.get("start_time", "") + timedelta(minutes=30),
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
            bk_biz_id=config.bk_biz_id,
            details={
                "infos": infos,
                "drill_config": {
                    "polling_interval": config.polling_interval,
                    "polling_timeout": config.polling_timeout,
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
            logger.info(_("  - Instance {} from cluster {}").format(instance.ip_port, item["cluster"].immute_domain))

    except Exception as e:
        logger.exception(
            _("Failed to create drill ticket: {}, marking these records as failed: {}").format(str(e), task_records)
        )


def init_config() -> RedisRollbackExerciseConfig:
    config_dict = SystemSettings.get_setting_value("REDIS_ROLLBACK_EXERCISE", {})
    config = RedisRollbackExerciseConfig(**config_dict) if config_dict else RedisRollbackExerciseConfig()
    logger.info(_("Redis rollback exercise settings: {}").format(config))
    return config


def gen_rollback_task():
    """
    Generate Redis rollback exercise tasks

    Main workflow:
    1. Pick n target instances
    2. For each instance, check if 20-day-earlier backup exists
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

    config = init_config()
    if not config.switch:
        logger.info(_("Redis rollback exercise is disabled, exiting..."))
        return

    selected_instances = pick_target_instances(config, config.max_instances)
    if not selected_instances:
        logger.info(_("No instances selected for exercise"))
        return

    logger.info(_("Selected {} instances for exercise").format(len(selected_instances)))
    valid_instances = []
    for item in selected_instances:
        cluster = item["cluster"]
        instance: StorageInstance = item["instance"]

        try:
            has_backup, backup_info = instance_has_backup(
                instance.machine.ip,
                instance.port,
                cluster.id,
                cluster.cluster_type,
                days_before=config.rollback_days,
            )

            if has_backup:
                valid_instances.append(
                    {
                        "cluster": cluster,
                        "instance": instance,
                        "backup_info": backup_info,
                    }
                )
                logger.info(_("Instance {} has valid backup within 20 days").format(instance.ip_port))
            else:
                logger.warning(_("Instance {} has no valid backup within 20 days, skipping").format(instance.ip_port))
                logger.info(
                    _("Dry-run: changing state to SKIPPED for instance({}) for no backup applicable").format(
                        instance.ip_port
                    )
                )

        except Exception as e:
            logger.exception(_("Error checking backup for instance {} {}").format(instance.ip_port, str(e)))
            logger.info(
                _("Dry-run: changing state to SKIPPED for instance({}) due to exception").format(instance.ip_port)
            )
            continue

    if not valid_instances:
        logger.info(_("No instances with valid backup found"))
        return

    logger.info(_("Found {} instances with valid backup: {}").format(len(valid_instances), valid_instances))

    try:
        create_drill_ticket(config, valid_instances)
    except Exception as e:
        logger.exception(_("Failed to create drill ticket: {}").format(str(e)))
        logger.info(_("Dry-run: Mark tasks as GENERATE_TICKET_FAILED"))
