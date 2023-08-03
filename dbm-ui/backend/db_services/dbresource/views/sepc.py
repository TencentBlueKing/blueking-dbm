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
import math

from django.db.models import F, Q
from django.utils.translation import ugettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.models import AuditedModel
from backend.bk_web.pagination import AuditedLimitOffsetPagination
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_meta.enums import InstanceRole, MachineType
from backend.db_meta.models import Cluster, Machine, ProxyInstance, StorageInstance
from backend.db_meta.models.spec import Spec
from backend.db_services.dbresource.constants import CLUSTER_TYPE__SPEC_FILTER, SWAGGER_TAG
from backend.db_services.dbresource.exceptions import SpecFilterClassDoesNotExistException, SpecOperateException
from backend.db_services.dbresource.filters import SpecListFilter
from backend.db_services.dbresource.serializers import (
    DeleteSpecSerializer,
    FilterClusterSpecResponseSerializer,
    FilterClusterSpecSerializer,
    QueryQPSRangeResponseSerializer,
    QueryQPSRangeSerializer,
    RecommendResponseSpecSerializer,
    RecommendSpecSerializer,
    SpecSerializer,
    VerifyDuplicatedSpecNameSerializer,
)
from backend.iam_app.handlers.drf_perm import GlobalManageIAMPermission


class DBSpecViewSet(viewsets.AuditedModelViewSet):
    """
    资源池规格类型视图
    """

    queryset = Spec.objects.all()
    pagination_class = AuditedLimitOffsetPagination
    serializer_class = SpecSerializer
    filter_class = SpecListFilter

    def _get_custom_permissions(self):
        if self.action in [
            DBSpecViewSet.list.__name__,
            DBSpecViewSet.recommend_spec.__name__,
            DBSpecViewSet.query_qps_range.__name__,
            DBSpecViewSet.filter_cluster_spec.__name__,
        ]:
            return []

        return [GlobalManageIAMPermission()]

    def _remove_spec_fields(self, machine_type, data):
        """移除无需的字段"""
        remove_fields = []
        if machine_type != MachineType.ES_DATANODE:
            remove_fields.append("instance_num")

        # TODO: 后续可增加其他特定字段排除

        for d in data:
            for field in remove_fields:
                d.pop(field)

    @common_swagger_auto_schema(
        operation_summary=_("新建规格"),
        tags=[SWAGGER_TAG],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("规格详情"),
        tags=[SWAGGER_TAG],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("更新规格"),
        tags=[SWAGGER_TAG],
    )
    def update(self, request, *args, **kwargs):
        # 如果被引用，则只允许更新机器规格
        spec_id = int(kwargs.pop("pk"))
        update_data = dict(request.data)
        if Machine.is_refer_spec([spec_id]):
            spec = Spec.objects.get(spec_id=spec_id)
            for key in update_data:
                # 如果是可更新字段或不存在字段，则忽略
                if key in ["desc", "spec_name", *AuditedModel.AUDITED_FIELDS] or key not in spec.__dict__:
                    continue
                # 如果更新机型字段，则只允许拓展机型
                elif key == "device_class":
                    if update_data[key] == []:
                        continue
                    if set(update_data[key]).issuperset(set(spec.device_class)) and spec.device_class != []:
                        continue
                    else:
                        raise SpecOperateException(_("规格: {}已经被引用，只允许拓展机型").format(spec_id))
                # 对正在被引用的规格的配置字段更改，抛出异常
                elif update_data[key] != spec.__dict__[key]:
                    raise SpecOperateException(_("规格: {}已经被引用，无法修改配置！(只允许拓展机型和修改描述)").format(spec.spec_name))

        return super().update(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("查询规格列表"),
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        spec_ids = [spec["spec_id"] for spec in resp.data["results"]]
        # 为规格添加是否引用字段
        already_refer_spec_ids = list(Machine.objects.filter(spec_id__in=spec_ids).values_list("spec_id", flat=True))
        for spec_data in resp.data["results"]:
            spec_data["is_refer"] = spec_data["spec_id"] in already_refer_spec_ids

        return resp

    @common_swagger_auto_schema(
        operation_summary=_("删除规格"),
        tags=[SWAGGER_TAG],
    )
    def destroy(self, request, *args, **kwargs):
        spec_id = int(kwargs.pop("pk"))
        if Machine.is_refer_spec([spec_id]):
            raise SpecOperateException(_("规格: {}已经被引用，无法被删除").format(spec_id))

        super().destroy(request, *args, **kwargs)
        return Response()

    @common_swagger_auto_schema(
        operation_summary=_("校验是否存在同名规格"),
        request_body=VerifyDuplicatedSpecNameSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=VerifyDuplicatedSpecNameSerializer)
    def verify_duplicated_spec_name(self, request, *args, **kwargs):
        params = self.params_validate(self.get_serializer_class())
        verify_spec_id = params.pop("spec_id", -1)
        # 如果存在同名规格，并且不是对自己更新，则认为规格重复
        spec = Spec.objects.filter(**params)
        is_duplicated = spec.exists() and (spec.first().spec_id != verify_spec_id)
        return Response(is_duplicated)

    @common_swagger_auto_schema(
        operation_summary=_("批量删除规格"),
        request_body=DeleteSpecSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["DELETE"], detail=False, serializer_class=DeleteSpecSerializer)
    def batch_delete(self, request, *args, **kwargs):
        spec_ids = self.params_validate(self.get_serializer_class())["spec_ids"]
        if Machine.is_refer_spec(spec_ids):
            raise SpecOperateException(_("规格: {}已经被引用，无法删除！").format(spec_ids))
        return Response(Spec.objects.filter(spec_id__in=spec_ids).delete())

    @common_swagger_auto_schema(
        operation_summary=_("获取推荐规格"),
        query_serializer=RecommendSpecSerializer(),
        responses={status.HTTP_200_OK: RecommendResponseSpecSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["GET"],
        detail=False,
        serializer_class=RecommendSpecSerializer,
        filter_class=None,
        pagination_class=None,
    )
    def recommend_spec(self, request):
        data = self.params_validate(self.get_serializer_class())
        if data["role"] == InstanceRole.INFLUXDB:
            # 如果是influxdb，则直接通过id查询即可，并设置cluster为空
            cluster = None
            filter_params = Q(role=data["role"]) & Q(id=data["instance_id"])
        else:
            cluster = Cluster.objects.get(id=data["cluster_id"])
            filter_params = Q(cluster=cluster) & Q(role=data["role"])

        # 根据角色获取StorageInstance关联的规格
        storage_spec_ids = (
            StorageInstance.objects.annotate(role=F("instance_role"))
            .filter(filter_params)
            .values_list("machine__spec_id", flat=True)
        )

        # 根据角色获取ProxyInstance关联的规格
        proxy_spec_ids = (
            ProxyInstance.objects.annotate(role=F("access_layer"))
            .filter(filter_params)
            .values_list("machine__spec_id", flat=True)
        )

        # 根据spider角色获取接入层关联的规格
        spider_spec_ids = (
            ProxyInstance.objects.prefetch_related("tendbclusterspiderext")
            .filter(cluster=cluster, tendbclusterspiderext__spider_role=data["role"])
            .values_list("machine__spec_id", flat=True)
        )

        spec_data = SpecSerializer(
            Spec.objects.filter(spec_id__in=[*storage_spec_ids, *proxy_spec_ids, *spider_spec_ids]), many=True
        ).data

        return Response(spec_data)

    @common_swagger_auto_schema(
        operation_summary=_("获取qps的范围"),
        query_serializer=QueryQPSRangeSerializer(),
        responses={status.HTTP_200_OK: QueryQPSRangeResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["GET"],
        detail=False,
        serializer_class=QueryQPSRangeSerializer,
        filter_class=None,
        pagination_class=None,
    )
    def query_qps_range(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        specs = Spec.objects.filter(
            spec_machine_type=data["spec_machine_type"], spec_cluster_type=data["spec_cluster_type"]
        )
        if not specs.exists():
            raise SpecFilterClassDoesNotExistException(
                _("集群: {}后端没有配置任何规格，请前往规格页面配置").format(data["spec_cluster_type"])
            )

        # 获取每个规格的qps的最小值和最大值
        qps_min_max_map = {
            spec.qps["min"]
            * math.ceil(data["capacity"] / spec.capacity): spec.qps["max"]
            * math.ceil(data["capacity"] / spec.capacity)
            for spec in specs
        }
        # 获取总qps的range
        return Response({"min": min(qps_min_max_map.keys()), "max": max(qps_min_max_map.values())})

    @common_swagger_auto_schema(
        operation_summary=_("筛选集群部署规格方案"),
        request_body=FilterClusterSpecSerializer(),
        responses={status.HTTP_200_OK: FilterClusterSpecResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=FilterClusterSpecSerializer,
        filter_class=None,
        pagination_class=None,
    )
    def filter_cluster_spec(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        try:
            specs = CLUSTER_TYPE__SPEC_FILTER[data["spec_cluster_type"]](**data).get_target_specs()
        except KeyError:
            raise SpecFilterClassDoesNotExistException(_("集群:{}的规格筛选类不存在，请实现相应接口").format(data["spec_cluster_type"]))

        return Response(specs)
