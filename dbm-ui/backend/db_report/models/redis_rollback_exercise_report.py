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

from django.db import models
from django.db.models import F, OuterRef, Subquery
from django.utils import timezone
from django.utils.translation import gettext as _

from backend.bk_web import constants
from backend.db_report.enums import REDIS_ROLLBACK_EXER_FAILED_STAGES as FAILED_STAGES
from backend.db_report.enums import RedisRollbackExerciseTaskStage as TaskStage
from backend.db_report.enums import ReportStateType
from backend.db_report.report_basemodel import BaseReportABS

logger = logging.getLogger("root")


class RedisRollbackExerciseReport(BaseReportABS):
    """
    Redis rollback exercise task infos
    Each task record represents a single instance rollback exercise
    """

    # Cluster & Instance Info
    cluster_id = models.IntegerField(_("源集群ID"), default=0)
    cluster_domain = models.CharField(_("源集群域名"), max_length=255, default="")
    cluster_type = models.CharField(_("源集群类型"), max_length=64, default="")
    instance_ip = models.CharField(_("IP"), max_length=64, null=True, blank=True, default="")
    instance_port = models.IntegerField(_("Port"), null=True, blank=True, default=0)
    redis_version = models.CharField(_("实例版本"), max_length=64, default="")

    # Backup Info
    backup_info = models.TextField(_("备份信息"), default="")

    # Timestamps
    task_start_time = models.DateTimeField(_("任务开始时间"), default=timezone.now)
    recover_start_time = models.DateTimeField(_("回档开始时间"), null=True, blank=True)
    recover_end_time = models.DateTimeField(_("回档结束时间"), null=True, blank=True)
    task_end_time = models.DateTimeField(_("任务结束时间"), null=True, blank=True)

    # Task Info
    ticket_id = models.IntegerField(_("关联单据ID"), null=True, default=0)
    rollback_flow_obj_id = models.CharField(_("构造流程ID"), max_length=255, null=True, blank=True)
    delete_flow_obj_id = models.CharField(_("销毁流程ID"), max_length=255, null=True, blank=True)

    # Task execution stage and message
    task_stage = models.CharField(
        _("任务阶段"),
        max_length=constants.LEN_SHORT,
        choices=TaskStage.get_choices(),
        default=TaskStage.TASK_GENERATED,
        help_text=_("当前任务执行阶段"),
    )
    task_message = models.TextField(_("任务日志"), default="")

    class Meta:
        indexes = [
            models.Index(fields=["state", "-create_at"]),  # For view set querying
            models.Index(fields=["task_stage", "-update_at"]),  # For view set querying & candidate calculation
            models.Index(fields=["cluster_id", "-update_at"]),  # For candidate calculation
        ]

    @classmethod
    def get_previously_failed_clusters(cls):
        """
        Get cluster IDs whose most recent report indicates failure.

        Returns:
            Set[int]: Cluster IDs
        """

        # Subquery to get the latest update_at for each cluster
        latest_update_at = (
            cls.objects.filter(cluster_id=OuterRef("cluster_id")).order_by("-update_at").values("update_at")[:1]
        )

        # Filter reports that are both the latest for their cluster AND have failed status
        failed_clusters = (
            cls.objects.annotate(latest_update_at=Subquery(latest_update_at))
            .filter(
                task_stage__in=FAILED_STAGES,
                update_at=F("latest_update_at"),
            )
            .values_list("cluster_id", flat=True)
            .distinct()
        )

        return set(failed_clusters), failed_clusters

    @classmethod
    def get_not_exercised_clusters(cls, cluster_ids: list, days_threshold: int = 180):
        """
        Get cluster IDs that haven't been exercised (with success) in the last N days.

        This includes:
        1. Clusters that have never been exercised (no records at all)
        2. Clusters whose most recent successful exercise was more than N days ago

        Args:
            cluster_ids: List of candidate cluster IDs to check
            days_threshold: Number of days to look back (default 180)

        Returns:
            Set[int]: Cluster IDs that need exercise attention
        """
        cutoff_date = timezone.now() - timedelta(days=days_threshold)

        # Get clusters with successful exercise in the last N days (only check the candidates)
        recently_exercised = (
            cls.objects.filter(
                task_stage=TaskStage.DONE,
                update_at__gte=cutoff_date,
            )
            .values_list("cluster_id", flat=True)
            .distinct()
        )

        return set(cluster_ids) - set(recently_exercised), recently_exercised

    def mark(self, stage: TaskStage = None, task_message: str = None, **kwargs):
        """
        Mark the task with a new state and optionally update task message and extra fields.
        Automatically updates relevant timestamp fields based on state transitions.

        When ``stage`` is None the stage is left unchanged -- useful for
        backfilling ``task_message`` or other fields on an already-terminal report.

        Args:
            stage: The new task execution stage (None to keep current stage).
            task_message: Optional message about the task execution.
            **kwargs: Additional model fields to set (e.g. rollback_flow_obj_id).
        """
        update_fields = ["update_at"]

        if stage is not None:
            self.task_stage = stage
            update_fields.append("task_stage")

            match stage:
                case (
                    TaskStage.SKIPPED
                    | TaskStage.BACKUP_INVALID
                    | TaskStage.TICKET_GEN_FAILED
                    | TaskStage.RESOURCE_APPLI_FAILED
                    | TaskStage.CLEANUP_FAILED
                    | TaskStage.DONE
                ):
                    new_state = ReportStateType.ABNORMAL
                    if stage == TaskStage.DONE:
                        new_state = ReportStateType.NORMAL
                    elif stage == TaskStage.SKIPPED:
                        new_state = ReportStateType.WARNING

                    self.task_end_time = timezone.now()
                    self.state = new_state
                    update_fields.extend(["task_end_time", "state"])

                case TaskStage.TICKET_GENERATED:
                    update_fields.append("ticket_id")

                case TaskStage.ROLLBACK_STARTED:
                    self.recover_start_time = timezone.now()
                    update_fields.append("recover_start_time")

                case TaskStage.ROLLBACK_FAILED:
                    self.recover_end_time = timezone.now()
                    self.task_end_time = timezone.now()
                    self.state = ReportStateType.ABNORMAL
                    update_fields.extend(["recover_end_time", "task_end_time", "state"])

                case TaskStage.SCENE_PRESERVED:
                    # Scene still open: do not set task_end_time.
                    # DBA confirmation later marks ROLLBACK_FAILED/CLEANUP_FAILED and fills it.
                    self.recover_end_time = timezone.now()
                    self.state = ReportStateType.ABNORMAL
                    update_fields.extend(["recover_end_time", "state"])

                case TaskStage.ROLLBACK_SUCCEEDED:
                    self.recover_end_time = timezone.now()
                    update_fields.append("recover_end_time")

                case TaskStage.RESOURCE_APPLI_SUCCEEDED:
                    pass

        if task_message:
            update_fields.append("task_message")
            self.task_message = "".join(
                ch for ch in task_message if ord(ch) <= 0xFFFF
            )  # For MySQL utf8mb3 compatibility

        for field_name, value in kwargs.items():
            setattr(self, field_name, value)
            update_fields.append(field_name)

        self.save(update_fields=update_fields)

        # Trigger AI failure analysis only when transitioning into a failed stage.
        # stage=None updates (e.g. appending the AI block itself) must not re-enqueue.
        if stage is not None and stage in FAILED_STAGES:
            try:
                from backend.db_services.redis.rollback.failure_analysis import enqueue_exercise_failure_analysis

                enqueue_exercise_failure_analysis(self.id)
            except Exception:
                # Analysis must never break the drill flow or candidate generator.
                logger.exception("failed to enqueue redis rollback exercise AI analysis for report %s", self.id)
