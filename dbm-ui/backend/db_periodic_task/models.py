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

import json
import logging
from datetime import timedelta

from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django_celery_beat.models import PeriodicTask
from django_celery_beat.schedulers import ModelEntry

from backend.bk_web import constants
from backend.bk_web.models import AuditedModel
from backend.db_meta.enums import ClusterType
from backend.db_periodic_task.constants import PeriodicTaskType

logger = logging.getLogger("root")


class PeriodicTaskManager(models.Manager):
    pass


class DBPeriodicTask(AuditedModel):
    name = models.CharField(_("周期任务名称"), max_length=constants.LEN_LONG, unique=True)
    task = models.ForeignKey(PeriodicTask, verbose_name=_("celery 周期任务实例"), on_delete=models.CASCADE)
    task_type = models.CharField(_("任务类型"), choices=PeriodicTaskType.get_choices(), max_length=constants.LEN_SHORT)
    is_frozen = models.BooleanField(_("是否冻结"), help_text=_("人工冻结此任务，将不受更新影响"), default=False)

    objects = PeriodicTaskManager()

    class Meta:
        verbose_name_plural = verbose_name = _("周期任务(PeriodicTask)")
        ordering = ["-id"]

    def __str__(self):
        return self.name

    @classmethod
    @transaction.atomic
    def delete_legacy_periodic_task(cls, tasks, task_type):
        # 本地周期任务，且不再注册，说明是历史废弃任务，需删除
        legacy_tasks = DBPeriodicTask.objects.filter(task_type=task_type).exclude(name__in=tasks)
        celery_task_ids = legacy_tasks.values_list("task_id", flat=True)
        PeriodicTask.objects.filter(id__in=celery_task_ids).delete()
        legacy_tasks.delete()

    @classmethod
    def create_or_update_periodic_task(cls, name, task, run_every, task_type, args=None, kwargs=None):
        """
        创建/更新任务
        """

        # 转换执行周期
        model_schedule, model_field = ModelEntry.to_model_schedule(run_every)
        # 转换执行参数
        _args = json.dumps(args or [])
        _kwargs = json.dumps(kwargs or {})

        try:
            db_task = DBPeriodicTask.objects.get(name=name)
        except DBPeriodicTask.DoesNotExist:
            # 新建周期任务
            celery_task = PeriodicTask.objects.create(
                name=name, task=task, args=_args, kwargs=_kwargs, **{model_field: model_schedule}
            )
            DBPeriodicTask.objects.create(name=name, task=celery_task, task_type=task_type)
        else:
            # 未冻结的情况，需要更新执行周期和执行参数
            if not db_task.is_frozen:
                celery_task = db_task.task
                setattr(celery_task, model_field, model_schedule)
                celery_task.args = _args
                celery_task.kwargs = _kwargs
                celery_task.save(update_fields=[model_field, "args", "kwargs"])


class TaskStatus:
    # 已生成任务
    GENERATED = "generated"
    # 已申请资源
    RESOURCE_APPLIED = "resource_applied"
    # 资源申请失败
    RESOURCE_APPLIED_FAILED = "resource_applied_failed"
    # 提交任务成功
    COMMIT_SUCCESS = "commit_success"
    # 提交任务失败
    COMMIT_FAILED = "commit_failed"
    # 部署mysql成功
    DEPLOY_SUCCESS = "deploy_success"
    # 演练恢复成功
    RECOVER_SUCCESS = "recover_success"
    # 资源归还成功
    RESOURCE_RETURN_SUCCESS = "resource_return_success"


class MySQLBackupRecoverTask(AuditedModel):
    """
    MySQL备份定期回档演练
    """

    bk_biz_id = models.IntegerField(_("演练业务ID"), default=0)
    cluster_id = models.IntegerField(_("备份来源集群ID"), default=0)
    cluster_domain = models.CharField(_("备份来源域名"), max_length=constants.LEN_LONG, default="")
    cluster_type = models.CharField(max_length=64, choices=ClusterType.get_choices(), default="")
    backup_id = models.CharField(_("备份ID"), max_length=constants.LEN_LONG, default="")
    backup_begin_time = models.DateTimeField(_("备份开始时间"), default=None)
    backup_end_time = models.DateTimeField(_("备份结束时间"), default=None)
    backup_total_size = models.IntegerField(_("备份总大小"), default=0)
    backup_type = models.CharField(_("备份类型"), max_length=constants.LEN_SHORT, default="")
    backup_tool = models.CharField(_("备份工具"), max_length=constants.LEN_SHORT, default="")
    time_zone = models.CharField(_("时区"), max_length=constants.LEN_SHORT, default="")
    # 关联单据id
    recover_start_time = models.DateTimeField(_("备份恢复开始时间"), default=timezone.now)
    recover_end_time = models.DateTimeField(_("备份恢复结束时间"), default=timezone.now)
    task_id = models.CharField(_("关联的任务ID"), max_length=constants.LEN_LONG, default="")
    task_status = models.CharField(_("任务状态"), max_length=constants.LEN_SHORT, default="")
    task_info = models.TextField(_("任务信息"), default="")

    @classmethod
    def get_all_practiced_biz_ids(cls):
        """
        获取已经回档过的所有业务ID
        """
        return list(
            MySQLBackupRecoverTask.objects.filter(
                task_status__in=[TaskStatus.RECOVER_SUCCESS, TaskStatus.RESOURCE_RETURN_SUCCESS]
            )
            .values_list("bk_biz_id", flat=True)
            .distinct()
        )

    @classmethod
    def get_all_practiced_cluster_ids(cls):
        """
        获取已经成功回档过的所有集群ID
        """
        return list(
            MySQLBackupRecoverTask.objects.filter(
                task_status__in=[TaskStatus.RECOVER_SUCCESS, TaskStatus.RESOURCE_RETURN_SUCCESS]
            )
            .values_list("cluster_id", flat=True)
            .distinct()
        )

    @classmethod
    def get_recent_24h_task_cluster_ids(cls):
        """
        获取最近24小时内发起任务集群ID列表
        """
        recent_time = timezone.now() - timedelta(hours=24)
        return list(
            MySQLBackupRecoverTask.objects.filter(
                create_at__gte=recent_time,
            )
            .values_list("cluster_id", flat=True)
            .distinct()
        )
