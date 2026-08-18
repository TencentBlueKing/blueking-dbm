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
from celery.schedules import crontab
from django.utils.translation import gettext_lazy as _
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.configuration.constants import DAILY_TODO_REMIND_DEFAULT, SystemSettingsEnum
from backend.configuration.models.system import SystemSettings
from backend.configuration.serializers import TodoRemindSerializer
from backend.configuration.tasks.todo_remind_tasks import send_todo_remind
from backend.db_periodic_task.constants import PeriodicTaskType
from backend.db_periodic_task.models import DBPeriodicTask
from backend.iam_app.handlers.drf_perm.base import ResourceActionPermission
from backend.iam_app.handlers.permission import ActionEnum

SWAGGER_TAG = _("每日代办提醒")


class TodoRemindViewSet(viewsets.SystemViewSet):
    serializer_class = TodoRemindSerializer
    action_permission_map = {
        ("get_todo_remind_conf",): [],
        ("update_todo_remind_conf",): [ResourceActionPermission([ActionEnum.PLATFORM_TODO_REMIND_MANAGE])],
    }

    @common_swagger_auto_schema(operation_summary=_("查询代办提醒配置"), tags=[SWAGGER_TAG])
    @action(methods=["GET"], detail=False)
    def get_todo_remind_conf(self, request, *args, **kwargs):
        todo_remind_conf = SystemSettings.get_setting_value(
            SystemSettingsEnum.DBM_DAILY_TODO_REMIND, default=DAILY_TODO_REMIND_DEFAULT
        )
        return Response(todo_remind_conf)

    @common_swagger_auto_schema(operation_summary=_("新增代办提醒配置"), tags=[SWAGGER_TAG])
    @action(methods=["POST"], detail=False, serializer_class=TodoRemindSerializer)
    def update_todo_remind_conf(self, request, *args, **kwargs):
        username = request.user.username

        validated_data = self.params_validate(self.get_serializer_class())
        SystemSettings.objects.update_or_create(
            defaults={
                "value": validated_data,
                "type": "dict",
                "creator": username,
                "updater": username,
            },
            key=SystemSettingsEnum.DBM_DAILY_TODO_REMIND.value,
        )
        # 获取轮值通知定时任务
        notice_task = DBPeriodicTask.create_or_update_periodic_task(
            name=f"dbm_periodic_{send_todo_remind.__name__}",
            task=f"{send_todo_remind.__module__}.{send_todo_remind.__name__}",
            run_every=crontab(**validated_data["remind_time"]),
            task_type=PeriodicTaskType.LOCAL.value,
        )
        # 打开/关闭 定时任务
        notice_task.task.enabled = validated_data["is_enable"]
        notice_task.task.save(update_fields=["enabled"])
        return Response()
