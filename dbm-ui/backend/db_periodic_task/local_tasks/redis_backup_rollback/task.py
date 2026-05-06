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

from celery.schedules import crontab
from django.utils import timezone as django_timezone
from django.utils.translation import gettext as _

from backend.db_periodic_task.local_tasks.register import register_periodic_task
from backend.db_report.enums import RedisRollbackExerciseTaskStage as TaskStage
from backend.db_report.models import RedisRollbackExerciseReport as Report
from backend.flow.consts import StateType
from backend.flow.models import FlowTree
from backend.flow.signal.redis_rollback_exercise_handler import wakeup_redis_rollback_runner_by_child

from .base import RedisRollbackExercise

logger = logging.getLogger("root")


@register_periodic_task(run_every=crontab(day_of_week="0", hour="12", minute="0"))
def init_redis_rollback_candidates():
    """
    Init candidates to exericise each week
    """
    RedisRollbackExercise().init_candidates_queue()


@register_periodic_task(run_every=crontab(day_of_week="1-5", hour="9-17", minute="*/10"))
def redis_rollback_exercise():
    """
    Generate Redis rollback exercise tasks
    """
    RedisRollbackExercise().start()


@register_periodic_task(run_every=crontab(minute="0"))
def repair_stuck_redis_rollback_exercise():
    """
    Best-effort safety net for stuck rollback exercise reports.
    """
    exercise_cfg = RedisRollbackExercise().config
    polling_timeout = exercise_cfg.polling_timeout
    overdue_cutoff = django_timezone.now() - timedelta(seconds=polling_timeout)
    long_overdue_cutoff = django_timezone.now() - timedelta(seconds=polling_timeout * 3)

    reports = Report.objects.filter(
        task_stage__in=[TaskStage.ROLLBACK_STARTED, TaskStage.ROLLBACK_SUCCEEDED], update_at__lt=overdue_cutoff
    )

    recovered = 0
    for report in reports:
        child_root_id = report.delete_flow_obj_id or report.rollback_flow_obj_id
        if not child_root_id:
            continue

        try:
            child_flow_tree = FlowTree.objects.get(root_id=child_root_id)
        except FlowTree.DoesNotExist:
            if report.update_at < long_overdue_cutoff:
                logger.warning(
                    _("Redis rollback report {} has no child FlowTree and exceeds 3*timeout").format(report.id)
                )
            continue

        if child_flow_tree.status in [StateType.FINISHED, StateType.FAILED, StateType.REVOKED]:
            recovered += wakeup_redis_rollback_runner_by_child(
                child_root_id=child_root_id, child_state=child_flow_tree.status, trigger="periodic_safety_net"
            )
        elif report.update_at < long_overdue_cutoff:
            logger.warning(
                _("Redis rollback report {} still in stage {} with child flow {} state {} (>3*timeout)").format(
                    report.id, report.task_stage, child_root_id, child_flow_tree.status
                )
            )

    if recovered:
        logger.info(_("Recovered {} stuck redis rollback runner(s)").format(recovered))
