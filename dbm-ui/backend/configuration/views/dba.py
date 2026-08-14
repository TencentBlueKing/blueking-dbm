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
from django.utils.translation import gettext_lazy as _
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.pagination import AuditedLimitOffsetPagination
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.configuration.constants import DBType
from backend.configuration.filters import AppOperateLogFilter
from backend.configuration.handlers.dba import DBAdministratorHandler, decorator_permission_field
from backend.configuration.models.dba import DBAdministrator
from backend.configuration.serializers import (
    AppOperateLogSerializer,
    BatchUpsertDBAdminSerializer,
    DBAComponentSerializer,
    ListDBAdminSerializer,
    ManageBizSerializer,
    UpdateAppTagsSerializer,
    UpsertDBAdminSerializer,
)
from backend.db_meta.models import AppCache, AppOperate, Tag
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.drf_perm.dba import BizDBAPermission, GlobalDBAPermission

SWAGGER_TAG = _("DBA人员")


class DBAdminViewSet(viewsets.SystemViewSet):
    filter_class = None

    def _get_custom_permissions(self):
        if self.action in [
            "list_admins",
            "get_dba_component",
            "app_operate_log",
            "manage_biz",
            "cancel_manage_biz",
            "update_app_tag",
            "batch_upsert_admins",
        ]:
            return []
        if self.action in ["upsert_global_admins"]:
            return [GlobalDBAPermission([ActionEnum.GLOBAL_DBA_ADMIN_EDIT])]
        else:
            return [BizDBAPermission([ActionEnum.DBA_ADMIN_EDIT])]

    @common_swagger_auto_schema(
        operation_summary=_("查询DBA人员列表"), query_serializer=ListDBAdminSerializer, tags=[SWAGGER_TAG]
    )
    @action(methods=["GET"], detail=False, serializer_class=ListDBAdminSerializer)
    @decorator_permission_field()
    def list_admins(self, request, *args, **kwargs):
        validated_data = self.params_validate(self.get_serializer_class())

        db_admins = []
        for biz_dba in DBAdministrator.objects.filter(**validated_data):
            db_admins.append(
                {
                    "db_type": biz_dba.db_type,
                    "db_type_display": DBType.get_choice_label(biz_dba.db_type),
                    "users": biz_dba.users,
                    "is_show": True if biz_dba.db_type != DBType.Cloud.value else False,
                    "updater": biz_dba.updater,
                    "update_at": biz_dba.update_at,
                    "bk_biz_id": biz_dba.bk_biz_id,
                }
            )
        return Response({"data": db_admins})

    @common_swagger_auto_schema(operation_summary=_("更新业务DBA人员"), tags=[SWAGGER_TAG])
    @action(methods=["POST"], detail=False, serializer_class=UpsertDBAdminSerializer)
    def upsert_admins(self, request, *args, **kwargs):
        username = request.user.username
        validated_data = self.params_validate(self.get_serializer_class())
        validated_data["username"] = username
        return Response(DBAdministratorHandler.upsert_biz_admins(**validated_data))

    @common_swagger_auto_schema(operation_summary=_("更新全局DBA人员"), tags=[SWAGGER_TAG])
    @action(methods=["POST"], detail=False, serializer_class=UpsertDBAdminSerializer)
    def upsert_global_admins(self, request, *args, **kwargs):
        username = request.user.username
        validated_data = self.params_validate(self.get_serializer_class())
        validated_data["username"] = username
        return Response(DBAdministratorHandler.upsert_biz_admins(**validated_data))

    @common_swagger_auto_schema(operation_summary=_("获取DBA人员组件信息"), tags=[SWAGGER_TAG])
    @action(methods=["POST"], detail=False, serializer_class=DBAComponentSerializer)
    def get_dba_component(self, request, *args, **kwargs):
        username = request.user.username
        validated_data = self.params_validate(self.get_serializer_class())
        bk_biz_id, db_type = validated_data.get("bk_biz_id"), validated_data.get("db_type")
        return Response(DBAdministratorHandler.get_dba_component_info(username, bk_biz_id, db_type))

    @common_swagger_auto_schema(operation_summary=_("纳管业务"), tags=[SWAGGER_TAG])
    @action(methods=["POST"], detail=False, serializer_class=ManageBizSerializer)
    def manage_biz(self, request, *args, **kwargs):
        username = request.user.username
        validated_data = self.params_validate(self.get_serializer_class())
        bk_biz_id, db_admins = validated_data.get("bk_biz_id"), validated_data.get("db_admins")
        app_code = validated_data.get("app_code")
        return Response(DBAdministratorHandler.manage_biz(bk_biz_id, db_admins, username, app_code))

    @common_swagger_auto_schema(operation_summary=_("取消纳管业务"), tags=[SWAGGER_TAG])
    @action(methods=["POST"], detail=False, serializer_class=ManageBizSerializer)
    def cancel_manage_biz(self, request, *args, **kwargs):
        username = request.user.username
        validated_data = self.params_validate(self.get_serializer_class())
        bk_biz_id = validated_data.get("bk_biz_id")
        return Response(DBAdministratorHandler.cancel_manage_biz(bk_biz_id, username))

    @common_swagger_auto_schema(operation_summary=_("更新业务标签"), tags=[SWAGGER_TAG])
    @action(methods=["POST"], detail=False, serializer_class=UpdateAppTagsSerializer)
    def update_app_tag(self, request, *args, **kwargs):
        username = request.user.username
        validated_data = self.params_validate(self.get_serializer_class())
        bk_biz_id = validated_data.get("bk_biz_id")
        app_instance = AppCache.objects.get(bk_biz_id=bk_biz_id)
        tags = Tag.objects.filter(id__in=validated_data["tags"])
        # 清空旧标签，添加新标签
        app_instance.tags.clear()
        app_instance.tags.add(*tags)
        operate = validated_data["operate"]
        AppOperate.objects.create(
            creator=username,
            bk_biz_id=bk_biz_id,
            operate_type=operate["type"],
            change_before=operate["before"],
            change_after=operate["after"],
        )
        return Response()

    @common_swagger_auto_schema(operation_summary=_("批量更新DBA人员"), tags=[SWAGGER_TAG])
    @action(methods=["POST"], detail=False, serializer_class=BatchUpsertDBAdminSerializer)
    def batch_upsert_admins(self, request, *args, **kwargs):
        username = request.user.username
        validated_data = self.params_validate(self.get_serializer_class())
        update_info = validated_data["update_info"]
        operates = validated_data["operates"]
        return Response(DBAdministratorHandler.batch_upsert_biz_admins(update_info, operates, username))

    @action(
        methods=["GET"],
        detail=False,
        queryset=AppOperate.objects.all().order_by("-create_at"),
        serializer_class=AppOperateLogSerializer,
        filter_class=AppOperateLogFilter,
        pagination_class=AuditedLimitOffsetPagination,
    )
    def app_operate_log(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
