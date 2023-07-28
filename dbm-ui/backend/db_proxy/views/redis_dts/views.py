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
from django.utils.translation import ugettext_lazy as _
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_proxy.constants import SWAGGER_TAG
from backend.db_proxy.views.redis_dts.serializers import (
    DtsDistributeLockSerializer,
    DtsJobSrcIPRunningTasksSerializer,
    DtsJobTasksSerializer,
    DtsJobToScheduleTasksSerializer,
    DtsLast30DaysToExecTasksSerializer,
    DtsLast30DaysToScheduleJobsSerializer,
    DtsServerMaxSyncPortSerializer,
    DtsServerMigatingTasksSerializer,
    DtsTaskByTaskIDSerializer,
    DtsTasksUpdateSerializer,
    IsDtsserverInBlacklistSerializer,
)
from backend.db_proxy.views.views import BaseProxyPassViewSet
from backend.db_services.redis_dts.apis import (
    dts_distribute_trylock,
    dts_distribute_unlock,
    dts_tasks_updates,
    get_dts_job_detail,
    get_dts_job_tasks,
    get_dts_server_max_sync_port,
    get_dts_server_migrating_tasks,
    get_dts_task_by_id,
    get_job_src_ip_running_tasks,
    get_job_to_schedule_tasks,
    get_last_30days_to_exec_tasks,
    get_last_30days_to_schedule_jobs,
    is_dtsserver_in_blacklist,
)
from backend.utils.time import datetime2str, strptime


class DtsApiProxyPassViewSet(BaseProxyPassViewSet):
    """
    DTS API 代理
    """

    @common_swagger_auto_schema(
        operation_summary=_("dtsserver是否在黑名单中"),
        request_body=IsDtsserverInBlacklistSerializer,
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=IsDtsserverInBlacklistSerializer,
        url_path="redis_dts/is_dtsserver_in_blacklist",
    )
    def is_dtsserver_in_blacklist(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response({"in": is_dtsserver_in_blacklist(validated_data)})

    @common_swagger_auto_schema(
        operation_summary=_("获取dts任务详情"),
        request_body=DtsJobTasksSerializer,
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=DtsJobTasksSerializer, url_path="redis_dts/job_detail")
    def get_dts_job_detail(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(get_dts_job_detail(validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("获取迁移任务task列表,失败的排在前面"),
        request_body=DtsJobTasksSerializer,
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=DtsJobTasksSerializer, url_path="redis_dts/job_tasks")
    def get_dts_job_tasks(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(get_dts_job_tasks(validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("dts 分布式锁,trylock,成功返回True,失败返回False"),
        request_body=DtsDistributeLockSerializer,
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=DtsDistributeLockSerializer,
        url_path="redis_dts/distribute_trylock",
    )
    def dts_distribute_trylock(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(dts_distribute_trylock(validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("dts 分布式锁,unlock"),
        request_body=DtsDistributeLockSerializer,
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=DtsDistributeLockSerializer,
        url_path="redis_dts/distribute_unlock",
    )
    def dts_distribute_unlock(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return dts_distribute_unlock(validated_data)

    @common_swagger_auto_schema(
        operation_summary=_("获取dts server迁移中的任务"),
        request_body=DtsServerMigatingTasksSerializer,
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=DtsServerMigatingTasksSerializer,
        url_path="redis_dts/dts_server_migrating_tasks",
    )
    def get_dts_server_migrating_tasks(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(get_dts_server_migrating_tasks(validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("获取DtsServer上syncPort最大的task"),
        request_body=DtsServerMaxSyncPortSerializer,
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=DtsServerMaxSyncPortSerializer,
        url_path="redis_dts/dts_server_max_sync_port",
    )
    def get_dts_server_max_sync_port(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(get_dts_server_max_sync_port(validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("获取最近30天内task_type类型的等待执行的tasks"),
        request_body=DtsLast30DaysToExecTasksSerializer,
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=DtsLast30DaysToExecTasksSerializer,
        url_path="redis_dts/last_30_days_to_exec_tasks",
    )
    def get_last_30_days_to_exec_tasks(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(get_last_30days_to_exec_tasks(validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("获取最近30天内的等待调度的jobs"),
        request_body=DtsLast30DaysToScheduleJobsSerializer,
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=DtsLast30DaysToScheduleJobsSerializer,
        url_path="redis_dts/last_30_days_to_schedule_jobs",
    )
    def get_last_30_days_to_schedule_jobs(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(get_last_30days_to_schedule_jobs(validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("获取一个job的所有待调度的tasks"),
        request_body=DtsJobToScheduleTasksSerializer,
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=DtsJobToScheduleTasksSerializer,
        url_path="redis_dts/job_to_schedule_tasks",
    )
    def get_job_to_schedule_tasks(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(get_job_to_schedule_tasks(validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("获取一个job的所有待调度的tasks"),
        request_body=DtsJobSrcIPRunningTasksSerializer,
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=DtsJobSrcIPRunningTasksSerializer,
        url_path="redis_dts/job_src_ip_running_tasks",
    )
    def get_job_src_ip_running_tasks(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(get_job_src_ip_running_tasks(validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("获取一个job的所有待调度的tasks"),
        request_body=DtsTaskByTaskIDSerializer,
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=DtsTaskByTaskIDSerializer,
        url_path="redis_dts/task_by_task_id",
    )
    def get_task_by_task_id(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(get_dts_task_by_id(validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("批量更新dts_tasks"),
        request_body=DtsTasksUpdateSerializer,
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"], detail=False, serializer_class=DtsTasksUpdateSerializer, url_path="redis_dts/tasks_update"
    )
    def update_tasks(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response({"rows_affected": dts_tasks_updates(validated_data)})
