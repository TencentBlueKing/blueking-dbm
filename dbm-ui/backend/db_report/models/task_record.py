"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _

from backend.bk_web.models import AuditedModel


class TaskRecord(AuditedModel):
    """TaskRecord 用于记录周期任务的执行记录"""

    id = models.BigAutoField(primary_key=True, verbose_name=_("主键"))
    db_type = models.CharField(max_length=128, verbose_name=_("数据库类型"), default="")
    task_name = models.CharField(max_length=255, verbose_name=_("任务名称"), default="")
    task_type = models.CharField(max_length=128, verbose_name=_("任务类型"), default="")
    task_status = models.CharField(max_length=128, verbose_name=_("任务状态"), default="")
    task_result = models.TextField(verbose_name=_("任务结果"), default="")
    start_time = models.DateTimeField(verbose_name=_("任务开始时间"), auto_now=True)
    end_time = models.DateTimeField(verbose_name=_("任务结束时间"), default=None)
    task_duration = models.IntegerField(default=0, verbose_name=_("任务时长"))
    cluster_num = models.IntegerField(default=0, verbose_name=_("集群数量"))
    cluster_success_num = models.IntegerField(default=0, verbose_name=_("集群成功数量"))
    cluster_skip_num = models.IntegerField(default=0, verbose_name=_("集群跳过数量"))
    cluster_warning_num = models.IntegerField(default=0, verbose_name=_("集群警告数量"))
    cluster_failed_num = models.IntegerField(default=0, verbose_name=_("集群失败数量"))

    class Meta:
        indexes = [
            models.Index(fields=["db_type", "task_name", "create_at"]),
        ]
