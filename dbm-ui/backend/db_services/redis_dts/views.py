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
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.iam_app.handlers.drf_perm import ViewBusinessIAMPermission

from .apis import dts_job_disconnct_sync, dts_job_tasks_failed_retry, get_dts_history_jobs, get_dts_job_tasks
from .serializers import DtsJobTasksSLZ, TendisDtsHistoryJobSLZ

RESOURCE_TAG = "db_services/redis/dts"


class TendisDtsJobViewSet(viewsets.AuditedModelViewSet):
    def _get_custom_permissions(self):
        return [ViewBusinessIAMPermission()]

    @common_swagger_auto_schema(
        operation_summary=_("获取DTS历史任务以及其对应task cnt"),
        responses={status.HTTP_200_OK: TendisDtsHistoryJobSLZ},
        tags=[RESOURCE_TAG],
    )
    @action(methods=["POST"], detail=False, url_path="history_jobs", serializer_class=TendisDtsHistoryJobSLZ)
    def historyjobs(self, request, *args, **kwargs):
        slz_data = self.params_validate(self.get_serializer_class())
        slz_data.update(user=request.user.username)
        return Response(get_dts_history_jobs(slz_data))

    @common_swagger_auto_schema(
        operation_summary=_("获取迁移任务task列表,失败的排在前面"),
        request_body=DtsJobTasksSLZ,
        tags=[RESOURCE_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=DtsJobTasksSLZ, url_path="job_tasks")
    def get_dts_job_tasks(self, request, *args, **kwargs):
        slz_data = self.params_validate(self.get_serializer_class())
        return Response(get_dts_job_tasks(slz_data))

    @common_swagger_auto_schema(
        operation_summary=_("dts job断开同步"),
        request_body=DtsJobTasksSLZ,
        tags=[RESOURCE_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=DtsJobTasksSLZ, url_path="job_disconnect_sync")
    def dts_job_disconnect_sync(self, request, *args, **kwargs):
        slz = self.get_serializer(data=request.data)
        slz.is_valid(raise_exception=True)
        return Response(dts_job_disconnct_sync(slz.data))

    @common_swagger_auto_schema(
        operation_summary=_("dts job 失败重试"),
        request_body=DtsJobTasksSLZ,
        tags=[RESOURCE_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=DtsJobTasksSLZ, url_path="job_task_failed_retry")
    def dts_job_tasks_failed_retry(self, request, *args, **kwargs):
        slz = self.get_serializer(data=request.data)
        slz.is_valid(raise_exception=True)
        return Response(dts_job_tasks_failed_retry(slz.data))
