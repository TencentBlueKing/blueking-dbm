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

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django_celery_beat.models import PeriodicTask
from django.db import transaction

from backend.bk_web import constants
from backend.bk_web.models import AuditedModel
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
        verbose_name = _("周期任务 PeriodicTask")
        verbose_name_plural = _("周期任务 PeriodicTask")
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
