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

from django.core.cache import cache
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django_filters import rest_framework as filters
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.bk_web.viewsets import AuditedModelViewSet
from backend.db_monitor import serializers

from ...configuration.constants import PLAT_BIZ_ID, DBType
from ...db_meta.enums import ClusterType, InstanceRole
from ...db_meta.models import Cluster, DBModule, StorageInstance
from ...iam_app.dataclass import ResourceEnum
from ...iam_app.dataclass.actions import ActionEnum
from ...iam_app.handlers.drf_perm.base import (
    BizDBTypeResourceActionPermission,
    DBManagePermission,
    ResourceActionPermission,
    get_request_key_id,
)
from ...iam_app.handlers.drf_perm.monitor import MonitorPolicyPermission
from ...iam_app.handlers.permission import Permission
from ...ticket.models import Ticket
from .. import constants
from ..models import MonitorPolicy


class MonitorPolicyListFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr="icontains", label=_("策略名"))
    updater = filters.CharFilter(lookup_expr="exact", label=_("更新人"))
    creator = filters.CharFilter(lookup_expr="creator", label=_("创建人"))
    db_type = filters.CharFilter(lookup_expr="exact", label=_("db类型"))
    target_keyword = filters.CharFilter(lookup_expr="icontains", label=_("目标关键字检索"))
    is_enabled = filters.BooleanFilter(label=_("是否启用"))

    bk_biz_id = filters.NumberFilter(method="filter_bk_biz_id", label=_("业务ID"))

    # 如果只需要开区间，可以简化配置，这里的注释留作学习示例
    # (create_at_after, create_at_before): create_at_after=2023-09-05 14:29:00&create_at_before=2023-09-05 14:30:05
    # create_at = filters.DateTimeFromToRangeFilter("create_at")
    # 拆分rangeFilter，支持两端闭区间
    create_at_before = filters.DateTimeFilter(field_name="create_at", lookup_expr="lte")
    create_at_after = filters.DateTimeFilter(field_name="create_at", lookup_expr="gte")

    # 需要利用Q查询
    notify_groups = filters.CharFilter(method="filter_notify_groups", label=_("告警组"))

    def filter_notify_groups(self, queryset, name, value):
        """过滤多个告警组: value=1,2,3"""

        qs = Q()
        for group in map(lambda x: int(x), value.split(",")):
            qs = qs | Q(notify_groups__contains=group)

        return queryset.filter(qs)

    def filter_bk_biz_id(self, queryset, name, value):
        """默认包含平台告警策略"""
        return queryset.filter(bk_biz_id__in=[PLAT_BIZ_ID, value])

    class Meta:
        model = MonitorPolicy
        fields = [
            "bk_biz_id",
            "name",
            "db_type",
            "updater",
            "creator",
            "create_at_before",
            "create_at_after",
            "is_enabled",
            "target_keyword",
            "notify_groups",
        ]


@method_decorator(
    name="list",
    decorator=common_swagger_auto_schema(
        operation_summary=_("获取策略列表"),
        tags=[constants.SWAGGER_TAG],
        responses={status.HTTP_200_OK: serializers.MonitorPolicyListSerializer()},
    ),
)
@method_decorator(
    name="retrieve",
    decorator=common_swagger_auto_schema(
        operation_summary=_("获取策略详情"),
        tags=[constants.SWAGGER_TAG],
        responses={status.HTTP_200_OK: serializers.MonitorPolicySerializer()},
    ),
)
@method_decorator(
    name="update",
    decorator=common_swagger_auto_schema(tags=[constants.SWAGGER_TAG]),
)
@method_decorator(
    name="destroy",
    decorator=common_swagger_auto_schema(operation_summary=_("删除策略"), tags=[constants.SWAGGER_TAG]),
)
@method_decorator(
    name="create",
    decorator=common_swagger_auto_schema(tags=[constants.SWAGGER_TAG]),
)
class MonitorPolicyViewSet(AuditedModelViewSet):
    """监控策略管理"""

    queryset = MonitorPolicy.objects.order_by("-create_at")

    http_method_names = ["get", "post", "delete"]
    filter_class = MonitorPolicyListFilter
    ordering_fields = ("-create_at",)

    @staticmethod
    def instance_getter(key):
        return lambda request, view: [get_request_key_id(request, key)]

    def _get_custom_permissions(self):
        if self.action == "list":
            if not int(self.request.query_params["bk_biz_id"]):
                list_permission = ResourceActionPermission(
                    [ActionEnum.GLOBAL_MONITOR_POLICY_LIST],
                    ResourceEnum.DBTYPE,
                    instance_ids_getter=self.instance_getter("db_type"),
                )
            else:
                list_permission = BizDBTypeResourceActionPermission(
                    [ActionEnum.MONITOR_POLICY_LIST],
                    instance_biz_getter=self.instance_getter("bk_biz_id"),
                    instance_dbtype_getter=self.instance_getter("db_type"),
                )
            return [list_permission]
        elif self.action in ["update_strategy", "destroy", "clone_strategy"]:
            return [MonitorPolicyPermission(view_action=self.action)]
        elif self.action in ["disable", "enable"]:
            return [MonitorPolicyPermission(view_action="enable_disable")]

        return [DBManagePermission()]

    def get_serializer_class(self):
        if self.action == "list":
            return serializers.MonitorPolicyListSerializer
        return serializers.MonitorPolicySerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["events"] = json.loads(cache.get(constants.MONITOR_EVENTS, "{}"))
        return context

    @Permission.decorator_permission_field(
        id_field=lambda d: d["id"],
        data_field=lambda d: d["results"],
        actions=ActionEnum.get_actions_by_resource(ResourceEnum.MONITOR_POLICY.id),
        resource_meta=ResourceEnum.MONITOR_POLICY,
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("启用策略"),
        tags=[constants.SWAGGER_TAG],
        request_body=serializers.MonitorPolicyEmptySerializer(),
    )
    @action(methods=["POST"], detail=True)
    def enable(self, request, *args, **kwargs):
        return Response(self.get_object().enable())

    @common_swagger_auto_schema(
        operation_summary=_("停用策略"),
        tags=[constants.SWAGGER_TAG],
        request_body=serializers.MonitorPolicyEmptySerializer(),
    )
    @action(methods=["POST"], detail=True)
    def disable(self, request, *args, **kwargs):
        return Response(self.get_object().disable())

    @common_swagger_auto_schema(
        operation_summary=_("克隆策略"),
        tags=[constants.SWAGGER_TAG],
        request_body=serializers.MonitorPolicyCloneSerializer(),
    )
    @action(methods=["POST"], detail=False, serializer_class=serializers.MonitorPolicyCloneSerializer)
    def clone_strategy(self, request, *args, **kwargs):
        return Response(MonitorPolicy.clone(self.validated_data, request.user.username))

    @common_swagger_auto_schema(
        operation_summary=_("更新策略"),
        tags=[constants.SWAGGER_TAG],
        request_body=serializers.MonitorPolicyUpdateSerializer(),
    )
    @action(methods=["POST"], detail=True, serializer_class=serializers.MonitorPolicyUpdateSerializer)
    def update_strategy(self, request, *args, **kwargs):
        return Response(self.get_object().update(self.validated_data, request.user.username))

    # @common_swagger_auto_schema(
    #     operation_summary=_("恢复默认策略"),
    #     tags=[constants.SWAGGER_TAG],
    #     request_body=serializers.MonitorPolicyEmptySerializer()
    # )
    # @action(methods=["POST"], detail=True)
    # def reset(self, request, *args, **kwargs):
    #     return Response(self.get_object().reset())

    @common_swagger_auto_schema(
        operation_summary=_("根据db类型查询集群列表"),
        tags=[constants.SWAGGER_TAG],
        query_serializer=serializers.ListClusterSerializer,
    )
    @action(
        methods=["GET"],
        detail=False,
        serializer_class=serializers.ListClusterSerializer,
        pagination_class=None,
        filter_class=None,
    )
    def cluster_list(self, request, *args, **kwargs):
        dbtype = self.validated_data["dbtype"]

        if dbtype == DBType.InfluxDB:
            return Response(
                StorageInstance.objects.filter(instance_role=InstanceRole.INFLUXDB).values_list(
                    "machine__ip", flat=True
                )
            )

        clusters = Cluster.objects.filter(cluster_type__in=ClusterType.db_type_to_cluster_types(dbtype))

        return Response(clusters.values_list("immute_domain", flat=True))

    @common_swagger_auto_schema(
        operation_summary=_("根据db类型查询模块列表"),
        tags=[constants.SWAGGER_TAG],
        query_serializer=serializers.ListModuleSerializer,
    )
    @action(
        methods=["GET"],
        detail=False,
        serializer_class=serializers.ListModuleSerializer,
        pagination_class=None,
        filter_class=None,
    )
    def db_module_list(self, request, *args, **kwargs):
        dbtype = self.validated_data["dbtype"]
        return Response(
            DBModule.objects.filter(cluster_type__in=ClusterType.db_type_to_cluster_types(dbtype)).values(
                "db_module_id", "db_module_name"
            )
        )

    @common_swagger_auto_schema(
        operation_summary=_("告警策略回调（处理套餐、故障自愈）"),
        tags=[constants.SWAGGER_TAG],
        request_body=serializers.AlarmCallBackDataSerializer,
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=serializers.AlarmCallBackDataSerializer,
    )
    def callback(self, request, *args, **kwargs):
        # 监控回调需要使用 Bearer Token 进行验证
        bearer_token = request.META.get("HTTP_AUTHORIZATION", "")
        print(f"{bearer_token} bearer_token")
        # if settings.SECRET_KEY not in bearer_token:
        #     raise AuthenticationFailed(_('Bearer token is invalid'))
        return Response(Ticket.create_ticket_from_bk_monitor(self.validated_data))
