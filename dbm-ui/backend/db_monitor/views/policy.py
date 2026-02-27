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
from collections import defaultdict

from django.core.cache import cache
from django.db.models import CharField, Q, Value
from django.db.models.functions import Cast, Concat
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django_filters import rest_framework as filters
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from backend import env
from backend.bk_web.pagination import AuditedLimitOffsetPagination
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.bk_web.viewsets import AuditedModelViewSet
from backend.components import BKMonitorV3Api
from backend.configuration.constants import PLAT_BIZ_ID
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster, DBModule, ProxyInstance, StorageInstance
from backend.db_monitor import constants, serializers
from backend.db_monitor.models import MonitorPolicy
from backend.db_monitor.utils import flatten_policy_results
from backend.iam_app.dataclass import ResourceEnum
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.drf_perm.base import (
    BizDBTypeResourceActionPermission,
    DBManagePermission,
    ResourceActionPermission,
    get_request_key_id,
)
from backend.iam_app.handlers.drf_perm.monitor import MonitorPolicyPermission
from backend.iam_app.handlers.permission import Permission
from backend.ticket.models import Ticket


class MonitorPolicyListFilter(filters.FilterSet):
    id = filters.NumberFilter(field_name="id", label=_("ID"))
    name = filters.CharFilter(field_name="name", lookup_expr="icontains", label=_("策略名"))
    updater = filters.CharFilter(lookup_expr="exact", label=_("更新人"))
    creator = filters.CharFilter(lookup_expr="creator", label=_("创建人"))
    db_type = filters.CharFilter(lookup_expr="exact", label=_("db类型"))
    policy_type = filters.CharFilter(lookup_expr="exact", label=_("策略类型"))
    target_keyword = filters.CharFilter(lookup_expr="icontains", label=_("目标关键字检索"))
    target_level = filters.CharFilter(method="filter_target_level", label=_("策略来源"))
    is_enabled = filters.BooleanFilter(label=_("是否启用"))
    is_cover = filters.BooleanFilter(method="filter_is_cover", label=_("是否覆盖"))
    monitor_policy_ids = filters.CharFilter(method="filter_monitor_policy_id", label=_("监控策略ID列表"))
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

    def filter_monitor_policy_id(self, queryset, name, value):
        """过滤多个策略ID: value=1,2,3"""
        return queryset.filter(monitor_policy_id__in=value.split(","))

    def filter_bk_biz_id(self, queryset, name, value):
        """默认包含平台告警策略"""
        return queryset.filter(bk_biz_id__in=[PLAT_BIZ_ID, value])

    def filter_is_cover(self, queryset, name, value):
        """过滤已有业务策略的全局策略"""
        if value:
            parent_ids = queryset.filter(target_level="appid").values_list("parent_id", flat=True)
            return queryset.exclude(id__in=list(set(parent_ids)), parent_id=0)
        return queryset

    def filter_target_level(self, queryset, name, value):
        """策略来源"""
        return queryset.filter(target_level__in=value.split(","))

    class Meta:
        model = MonitorPolicy
        fields = [
            "id",
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
            "policy_type",
            "is_cover",
            "target_level",
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

    pagination_class = AuditedLimitOffsetPagination
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
                permission = ResourceActionPermission(
                    [ActionEnum.GLOBAL_MONITOR_POLICY_LIST],
                    ResourceEnum.DBTYPE,
                    instance_ids_getter=self.instance_getter("db_type"),
                )
            else:
                permission = DBManagePermission()
            return [permission]
        elif self.action == "clone_strategy":
            policy = MonitorPolicy.objects.get(id=self.request.data["parent_id"])
            permission = BizDBTypeResourceActionPermission(
                [ActionEnum.MONITOR_POLICY_CLONE_STRATEGY],
                instance_biz_getter=self.instance_getter("bk_biz_id"),
                instance_dbtype_getter=lambda request, view: [policy.db_type],
            )
            return [permission]
        elif self.action in ["update_strategy", "destroy"]:
            return [MonitorPolicyPermission(view_action=self.action)]
        elif self.action in ["disable", "enable"]:
            return [MonitorPolicyPermission(view_action="enable_disable")]
        elif self.action in ["callback"]:
            return []
        return [DBManagePermission()]

    @classmethod
    def _get_login_exempt_view_func(cls):
        # 需要豁免的接口方法与名字
        return {"post": [cls.callback.__name__], "put": [], "get": [], "delete": []}

    def get_serializer_class(self):
        if self.action == "list":
            return serializers.MonitorPolicyListSerializer
        return serializers.MonitorPolicySerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["events"] = json.loads(cache.get(constants.MONITOR_EVENTS, "{}"))
        return context

    @Permission.decorator_external_permission_field(
        param_field=lambda d: {ResourceEnum.DBTYPE.id: d["db_type"], ResourceEnum.BUSINESS.id: d["bk_biz_id"]},
        actions=[ActionEnum.MONITOR_POLICY_CLONE_STRATEGY],
        resource_meta=[ResourceEnum.DBTYPE, ResourceEnum.BUSINESS],
    )
    @Permission.decorator_permission_field(
        id_field=lambda d: d["id"],
        data_field=flatten_policy_results,
        actions=ActionEnum.get_actions_by_resource(ResourceEnum.MONITOR_POLICY.id),
        resource_meta=ResourceEnum.MONITOR_POLICY,
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if request.query_params.get("bk_biz_id") != "0":
            # 父类id既全局策略id
            parent_ids = set()
            # 业务策略id
            app_ids = set()
            # 除业务和全局策略之外的id
            child_ids = []
            # 全局策略和业务策略的映射
            parent_app_map = defaultdict(list)
            # 全局策略和子策略的映射
            parent_child_map = defaultdict(list)
            # 最后的父策略和子策略的映射
            last_parent_child_map = defaultdict(list)

            result = queryset.values("id", "parent_id", "target_level")
            for res in result:
                id, parent_id, target_level = res["id"], res["parent_id"], res["target_level"]
                parent_ids.add(id if parent_id == 0 else parent_id)
                # 全局策略可以跳过，不需要记录父策略和子策略的关系
                if parent_id == 0:
                    continue
                if target_level == constants.TargetLevel.APP:
                    app_ids.add(id)
                    parent_app_map[parent_id].append(id)
                elif target_level not in [constants.TargetLevel.APP, constants.TargetLevel.PLATFORM]:
                    child_ids.append(id)
                    parent_child_map[parent_id].append(id)

            # 拿到未查到的业务策略，用来覆盖全局策略
            missing_parent_ids = [pid for pid in parent_child_map if pid not in parent_app_map]
            biz_policies = MonitorPolicy.objects.filter(
                parent_id__in=missing_parent_ids,
                target_level=constants.TargetLevel.APP,
                bk_biz_id=request.query_params["bk_biz_id"],
            ).values("id", "parent_id")
            biz_policy_map = {p["parent_id"]: p["id"] for p in biz_policies}

            for parent_id in parent_child_map:
                # 当又有全局策略又有业务策略时， 不返回全局策略
                if parent_id in parent_app_map:
                    # 可能会存在一个全局策略有多个业务策略的非标行为， 所以取第一个就行
                    last_parent_id = parent_app_map[parent_id][0]
                    last_parent_child_map[last_parent_id] = parent_child_map[parent_id]
                    app_ids.remove(last_parent_id)
                # 如果没拿到对应的业务策略则需要获取全局策略对应的业务策略
                elif parent_id in biz_policy_map:
                    last_parent_child_map[biz_policy_map[parent_id]] = parent_child_map[parent_id]
                else:
                    last_parent_child_map[parent_id] = parent_child_map[parent_id]
                parent_ids.remove(parent_id)

            # 最后再把存在业务策略的全局策略去掉
            for parent_id in parent_app_map:
                if parent_id in parent_ids:
                    parent_ids.remove(parent_id)

            first_level_ids = list(parent_ids) + list(app_ids) + list(last_parent_child_map.keys())
            # 拿到所有的需要查询的策略的id
            need_ids = first_level_ids + child_ids
            queryset = MonitorPolicy.objects.filter(id__in=need_ids)
            results = []
            res_data = self.get_serializer(queryset, many=True).data

            def _get_child_data(all_data, ids):
                child_data = []
                for data in all_data:
                    if data["id"] in ids:
                        child_data.append(data)
                return child_data

            for res in res_data:
                if res["id"] in first_level_ids:
                    res["child"] = (
                        _get_child_data(res_data, last_parent_child_map[res["id"]])
                        if last_parent_child_map[res["id"]]
                        else []
                    )
                    results.append(res)

            return Response({"results": results, "count": len(res_data)})

        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

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

    @common_swagger_auto_schema(
        operation_summary=_("批量更新策略告警组"),
        tags=[constants.SWAGGER_TAG],
        request_body=serializers.BatchUpdateMonitorPolicyNotifySerializer(),
    )
    @action(methods=["POST"], detail=False, serializer_class=serializers.BatchUpdateMonitorPolicyNotifySerializer)
    def batch_update_notify_group(self, request, *args, **kwargs):
        notify_groups = self.validated_data["notify_groups"]
        # 更新较慢考虑采用多线程方案
        policy_map = MonitorPolicy.objects.in_bulk(id_list=[info["policy_id"] for info in notify_groups])
        for info in notify_groups:
            policy = policy_map[info["policy_id"]]
            params = {"notify_groups": info["groups"]}
            policy.update(params, username=request.user.username)
        return Response()

    @common_swagger_auto_schema(
        operation_summary=_("全局策略恢复初始值"),
        tags=[constants.SWAGGER_TAG],
        request_body=serializers.MonitorPolicyResetSerializer(),
    )
    @action(methods=["POST"], detail=False, serializer_class=serializers.MonitorPolicyResetSerializer)
    def reset(self, request, *args, **kwargs):
        policy_id = self.validated_data["policy_id"]
        policy = MonitorPolicy.objects.filter(id=policy_id).first()
        db_type = policy.db_type
        name = policy.name
        MonitorPolicy.sync_plat_monitor_policy(db_type=db_type, specified_name=name, force=True)
        return Response()

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
        dbtype = self.validated_data.get("dbtype")
        bk_biz_id = self.validated_data["bk_biz_id"]
        clusters = Cluster.objects.filter(bk_biz_id=bk_biz_id)
        if dbtype:
            clusters = clusters.filter(cluster_type__in=ClusterType.db_type_to_cluster_types(dbtype))

        return Response(clusters.values_list("immute_domain", flat=True))

    @common_swagger_auto_schema(
        operation_summary=_("根据db类型查询实例列表"),
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
    def instance_list(self, request, *args, **kwargs):
        bk_biz_id = self.validated_data["bk_biz_id"]
        storage_instances = (
            StorageInstance.objects.select_related("machine")
            .filter(bk_biz_id=bk_biz_id)
            .annotate(
                instance=Concat(
                    Cast("machine__ip", output_field=CharField()), Value("-"), Cast("port", output_field=CharField())
                )
            )
            .values_list("instance", flat=True)
        )
        proxy_instances = (
            ProxyInstance.objects.select_related("machine")
            .filter(bk_biz_id=bk_biz_id)
            .annotate(
                instance=Concat(
                    Cast("machine__ip", output_field=CharField()), Value("-"), Cast("port", output_field=CharField())
                )
            )
            .values_list("instance", flat=True)
        )
        return Response(list(storage_instances) + list(proxy_instances))

    @common_swagger_auto_schema(
        operation_summary=_("根据db类型查询IP列表"),
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
    def ip_list(self, request, *args, **kwargs):
        bk_biz_id = self.validated_data["bk_biz_id"]
        storage_ips = (
            StorageInstance.objects.select_related("machine")
            .filter(bk_biz_id=bk_biz_id)
            .values_list("machine__ip", flat=True)
        )
        proxy_ips = (
            ProxyInstance.objects.select_related("machine")
            .filter(bk_biz_id=bk_biz_id)
            .values_list("machine__ip", flat=True)
        )
        return Response(list(set(list(storage_ips) + list(proxy_ips))))

    @common_swagger_auto_schema(
        operation_summary=_("根据db类型查询角色列表"),
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
    def instance_role_list(self, request, *args, **kwargs):
        bk_biz_id = self.validated_data["bk_biz_id"]
        storage_roles = StorageInstance.objects.filter(bk_biz_id=bk_biz_id).values_list("instance_role", flat=True)
        proxy_roles = ProxyInstance.objects.filter(bk_biz_id=bk_biz_id).values_list("access_layer", flat=True)
        return Response(list(set(list(storage_roles) + list(proxy_roles))))

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
        bk_biz_id = self.validated_data["bk_biz_id"]
        return Response(
            DBModule.objects.filter(
                cluster_type__in=ClusterType.db_type_to_cluster_types(dbtype), bk_biz_id=bk_biz_id
            ).values("db_module_id", "db_module_name")
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
        permission_classes=[AllowAny],
    )
    def callback(self, request, *args, **kwargs):
        # 监控回调需要使用 Bearer Token 进行验证
        # 从请求头中获取 Authorization 头
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise PermissionError("Missing Authorization header")
        # 提取 Bearer Token
        token = auth_header.split(" ")[1]
        if token != env.BKMONITOR_BEARER_TOKEN:
            raise PermissionError("Bearer token is not valid")
        return Response(Ticket.create_ticket_from_bk_monitor(self.validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("查询监控的策略信息"),
        tags=[constants.SWAGGER_TAG],
        query_serializer=serializers.AlarmStrategySerializer,
    )
    @action(
        methods=["GET"],
        detail=False,
        serializer_class=serializers.AlarmStrategySerializer,
        pagination_class=None,
        filter_class=None,
    )
    def search_alarm_strategy(self, request, *args, **kwargs):
        bk_biz_id = self.validated_data["bk_biz_id"]
        monitor_policy_id = self.validated_data["monitor_policy_id"]

        data = {}

        res = BKMonitorV3Api.search_alarm_strategy(
            {
                "conditions": [{"key": "strategy_id", "value": [monitor_policy_id]}],
                "bk_biz_id": bk_biz_id,
            },
            use_admin=True,
        )

        if res:
            metric_ids = []
            agg_dimension = []
            data["data_source_list"] = []
            strategy_config_list = res.get("strategy_config_list", [])
            for config in strategy_config_list:
                for item in config["items"]:
                    for query_config in item["query_configs"]:
                        data["data_source_list"].append(
                            {
                                "data_source_label": query_config["data_source_label"],
                                "data_type_label": query_config["data_type_label"],
                            }
                        )
                        agg_dimension.extend(query_config.get("agg_dimension", []))
                        metric_ids.append(query_config["metric_id"])

            data["agg_dimension"] = list(set(agg_dimension))
            if metric_ids:
                metric_info = BKMonitorV3Api.metric_list(
                    params={"bk_biz_id": bk_biz_id, "conditions": [{"key": "metric_id", "value": metric_ids}]},
                    use_admin=True,
                )
                data["metric_list"] = metric_info.get("metric_list", [])

        return Response(data)

    @common_swagger_auto_schema(
        operation_summary=_("批量恢复默认"),
        tags=[constants.SWAGGER_TAG],
        request_body=serializers.PatchDestroySerializer,
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=serializers.PatchDestroySerializer,
    )
    def patch_destroy(self, request, *args, **kwargs):
        policy_ids = self.validated_data["ids"]
        for policy in MonitorPolicy.objects.filter(id__in=policy_ids, target_level=constants.TargetLevel.APP):
            policy.delete()
        return Response()
