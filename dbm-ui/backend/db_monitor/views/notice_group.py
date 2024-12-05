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
from collections import Counter

from django.db.models import OuterRef, Q, Subquery
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.pagination import AuditedLimitOffsetPagination
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.configuration.constants import PLAT_BIZ_ID
from backend.core.notify import NotifyAdapter
from backend.db_monitor import serializers
from backend.db_monitor.models import MonitorPolicy, NoticeGroup
from backend.db_monitor.serializers import NoticeGroupSerializer
from backend.iam_app.dataclass import ResourceEnum
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.drf_perm.monitor import NotifyGroupPermission
from backend.iam_app.handlers.permission import Permission

SWAGGER_TAG = _("监控告警组")


@method_decorator(
    name="list",
    decorator=common_swagger_auto_schema(operation_summary=_("查询监控告警组列表"), tags=[SWAGGER_TAG]),
)
@method_decorator(
    name="create",
    decorator=common_swagger_auto_schema(
        operation_summary=_("新建监控告警组"), tags=[SWAGGER_TAG], request_body=serializers.NoticeGroupCreateSerializer()
    ),
)
@method_decorator(
    name="retrieve",
    decorator=common_swagger_auto_schema(operation_summary=_("获取监控告警组"), tags=[SWAGGER_TAG]),
)
@method_decorator(
    name="update",
    decorator=common_swagger_auto_schema(
        operation_summary=_("更新监控告警组"), tags=[SWAGGER_TAG], request_body=serializers.NoticeGroupUpdateSerializer()
    ),
)
@method_decorator(
    name="destroy",
    decorator=common_swagger_auto_schema(operation_summary=_("删除监控告警组"), tags=[SWAGGER_TAG]),
)
class MonitorNoticeGroupViewSet(viewsets.AuditedModelViewSet):
    """
    监控告警组视图
    """

    queryset = NoticeGroup.objects.all().order_by("-update_at")
    serializer_class = NoticeGroupSerializer
    pagination_class = AuditedLimitOffsetPagination

    def get_action_permission_map(self):
        return {
            (
                "list",
                "create",
                "destroy",
                "update",
                "partial_update",
            ): [NotifyGroupPermission(view_action=self.action)],
            (
                "get_msg_type",
                "list_group_name",
                "list_default_group",
            ): [],
        }

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["group_used"] = {}
        if "X-Requested-With" in self.request.META:
            # 仅在实际API调用时执行查库逻辑。/swagger/文档API忽略查库
            notify_groups = MonitorPolicy.objects.exclude(notify_groups=[]).values_list("notify_groups", flat=True)
            context["group_used"] = dict(Counter([item for group in notify_groups for item in group]))
        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action in ["list", "list_group_name", "list_default_group"]:
            # 1. 在指定业务和平台业务的告警组中过滤
            bk_biz_id = self.request.query_params.get("bk_biz_id", PLAT_BIZ_ID)
            queryset = queryset.filter(bk_biz_id__in=(PLAT_BIZ_ID, bk_biz_id))

            # 2. 指定告警组名字查询
            name = self.request.query_params.get("name", "")
            if name:
                subquery = queryset.filter(name__icontains=name, db_type=OuterRef("db_type")).order_by("-bk_biz_id")
            else:
                # 优先获取业务下的告警组，没有则有则返回平台告警组
                subquery = queryset.filter(db_type=OuterRef("db_type")).order_by("-bk_biz_id")
            queryset = queryset.filter(bk_biz_id=Subquery(subquery.values("bk_biz_id")[:1])).order_by("-update_at")

            # 3. 获取业务下指定 db 类型的告警组，如果业务
            db_type = self.request.query_params.get("db_type")
            if db_type:
                db_type_group = queryset.filter(db_type=db_type).order_by("bk_biz_id").first()
                group_id = getattr(db_type_group, "id", 0)
                queryset = queryset.filter(Q(id=group_id) | Q(db_type=""))

        return queryset

    @Permission.decorator_permission_field(
        id_field=lambda d: d["id"],
        data_field=lambda d: d["results"],
        actions=ActionEnum.get_actions_by_resource(ResourceEnum.NOTIFY_GROUP.id),
        resource_meta=ResourceEnum.NOTIFY_GROUP,
    )
    @Permission.decorator_external_permission_field(
        param_field=lambda d: d["bk_biz_id"],
        actions=[ActionEnum.NOTIFY_GROUP_CREATE],
        resource_meta=ResourceEnum.BUSINESS,
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @common_swagger_auto_schema(operation_summary=_("查询通知类型"), tags=[SWAGGER_TAG])
    @action(methods=["GET"], detail=False)
    def get_msg_type(self, request, *args, **kwargs):
        return Response(NotifyAdapter.get_support_msg_types())

    @common_swagger_auto_schema(operation_summary=_("查询告警组名称"), tags=[SWAGGER_TAG])
    @action(methods=["GET"], detail=False)
    def list_group_name(self, request, *args, **kwargs):
        group_name_infos = list(self.get_queryset().values("id", "name"))
        return Response(group_name_infos)

    @common_swagger_auto_schema(operation_summary=_("获取默认告警组名称"), tags=[SWAGGER_TAG])
    @action(methods=["GET"], detail=False, pagination_class=None)
    def list_default_group(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        default_groups = list(queryset.exclude(db_type="").values("id", "name", "db_type"))
        default_group_map = {group.pop("db_type"): group for group in default_groups}
        return Response(default_group_map)
