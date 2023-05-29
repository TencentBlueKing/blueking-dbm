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
from django.utils.translation import ugettext as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.iam_app.handlers.drf_perm import ViewBusinessIAMPermission

from .apis import dts_tasks_operate, dts_tasks_restart, dts_tasks_retry, get_dts_history_jobs, get_dts_job_tasks
from .serializers import DtsJobTasksSLZ, DtsTaskIDsSLZ, DtsTaskOperateSLZ, TendisDtsHistoryJobSLZ

REDIS_DTS_TAG = "db_ts"


class TendisDtsJobViewSet(viewsets.AuditedModelViewSet):
    def _get_custom_permissions(self):
        return [ViewBusinessIAMPermission()]

    @common_swagger_auto_schema(
        operation_summary=_("获取DTS历史任务以及其对应task cnt"),
        responses={status.HTTP_200_OK: TendisDtsHistoryJobSLZ},
        tags=[REDIS_DTS_TAG],
    )
    @action(methods=["POST"], detail=False, url_path="history_jobs", serializer_class=TendisDtsHistoryJobSLZ)
    def historyjobs(self, request, *args, **kwargs):
        slz = self.get_serializer(data=request.data)
        slz.is_valid(raise_exception=True)
        return Response(get_dts_history_jobs(slz.data))

    @common_swagger_auto_schema(
        operation_summary=_("获取迁移任务task列表,失败的排在前面"),
        request_body=DtsJobTasksSLZ,
        tags=[REDIS_DTS_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=DtsJobTasksSLZ, url_path="job_tasks")
    def get_dts_job_tasks(self, request, *args, **kwargs):
        slz = self.get_serializer(data=request.data)
        slz.is_valid(raise_exception=True)
        return Response(get_dts_job_tasks(slz.data))

    @common_swagger_auto_schema(
        operation_summary=_("dts task操作,目前支持 同步完成(syncStopTodo)、强制终止(ForceKillTaskTodo) 两个操作"),
        request_body=DtsTaskOperateSLZ,
        tags=[REDIS_DTS_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=DtsTaskOperateSLZ, url_path="tasks_operate")
    def dts_tasks_operate(self, request, *args, **kwargs):
        slz = self.get_serializer(data=request.data)
        slz.is_valid(raise_exception=True)
        return Response(dts_tasks_operate(slz.data))

    @common_swagger_auto_schema(
        operation_summary=_("dts tasks重新开始"),
        request_body=DtsTaskIDsSLZ,
        tags=[REDIS_DTS_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=DtsTaskIDsSLZ, url_path="tasks_restart")
    def dts_tasks_restart(self, request, *args, **kwargs):
        slz = self.get_serializer(data=request.data)
        slz.is_valid(raise_exception=True)
        return Response(dts_tasks_restart(slz.data))

    @common_swagger_auto_schema(
        operation_summary=_("dts tasks重试当前步骤"),
        request_body=DtsTaskIDsSLZ,
        tags=[REDIS_DTS_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=DtsTaskIDsSLZ, url_path="tasks_retry")
    def dts_tasks_retry(self, request, *args, **kwargs):
        slz = self.get_serializer(data=request.data)
        slz.is_valid(raise_exception=True)
        return Response(dts_tasks_retry(slz.data))
