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
from backend.bk_web.pagination import AuditedLimitOffsetPagination
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.mysql.dumper.filters import DumperConfigListFilter
from backend.db_services.mysql.dumper.handlers import DumperHandler
from backend.db_services.mysql.dumper.models import DumperSubscribeConfig
from backend.db_services.mysql.dumper.serializers import (
    DumperSubscribeConfigSerializer,
    GetDumperConfigRunningTasksResponseSerializer,
    GetDumperConfigRunningTasksSerializer,
    VerifyDuplicateNamsSerializer,
)
from backend.iam_app.dataclass import ResourceEnum
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.drf_perm.base import DBManagePermission, ResourceActionPermission
from backend.iam_app.handlers.permission import Permission

SWAGGER_TAG = "dumper"


class DumperConfigViewSet(viewsets.AuditedModelViewSet):
    pagination_class = AuditedLimitOffsetPagination
    queryset = DumperSubscribeConfig.objects.all()
    serializer_class = DumperSubscribeConfigSerializer
    filter_class = DumperConfigListFilter

    def get_action_permission_map(self):
        return {
            ("retrieve",): [
                ResourceActionPermission(
                    [ActionEnum.DUMPER_CONFIG_VIEW], ResourceEnum.DUMPER_SUBSCRIBE_CONFIG, self.inst_getter
                )
            ],
            ("update", "partial_update",): [
                ResourceActionPermission(
                    [ActionEnum.DUMPER_CONFIG_UPDATE], ResourceEnum.DUMPER_SUBSCRIBE_CONFIG, self.inst_getter
                )
            ],
            ("destroy",): [
                ResourceActionPermission(
                    [ActionEnum.DUMPER_CONFIG_DESTROY], ResourceEnum.DUMPER_SUBSCRIBE_CONFIG, self.inst_getter
                )
            ],
        }

    def get_default_permission_class(self):
        return [DBManagePermission()]

    def inst_getter(self, request, view):
        return [view.kwargs["pk"]]

    def get_queryset(self):
        return self.queryset.filter(bk_biz_id=self.kwargs.get("bk_biz_id"))

    @common_swagger_auto_schema(
        operation_summary=_("查询数据订阅配置列表"),
        tags=[SWAGGER_TAG],
    )
    @Permission.decorator_permission_field(
        id_field=lambda d: d["id"],
        data_field=lambda d: d["results"],
        actions=ActionEnum.get_actions_by_resource(ResourceEnum.DUMPER_SUBSCRIBE_CONFIG.id),
        resource_meta=ResourceEnum.DUMPER_SUBSCRIBE_CONFIG,
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("数据订阅配置详情"),
        tags=[SWAGGER_TAG],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("数据订阅配置删除"),
        tags=[SWAGGER_TAG],
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("数据订阅配置更新"),
        tags=[SWAGGER_TAG],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("数据订阅配置部分更新"),
        tags=[SWAGGER_TAG],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("校验订阅配置是否重名"),
        query_serializer=VerifyDuplicateNamsSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=VerifyDuplicateNamsSerializer, filter_class=None)
    def verify_duplicate_name(self, request, *args, **kwargs):
        name = self.params_validate(self.get_serializer_class())["name"]
        is_duplicate = self.queryset.filter(bk_biz_id=kwargs["bk_biz_id"], name=name).count() != 0
        return Response(is_duplicate)

    @common_swagger_auto_schema(
        operation_summary=_("查询dumper配置正在运行的任务"),
        query_serializer=GetDumperConfigRunningTasksSerializer(),
        responses={status.HTTP_200_OK: GetDumperConfigRunningTasksResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=GetDumperConfigRunningTasksSerializer, filter_class=None)
    def get_running_tasks(self, request, *args, **kwargs):
        config_id = self.params_validate(self.get_serializer_class())["dumper_config_id"]
        return Response(DumperHandler.get_dumper_config_running_tasks(config_id=config_id))
