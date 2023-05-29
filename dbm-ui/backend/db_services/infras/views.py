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
from backend.db_services.infras import serializers
from backend.exceptions import ValidationError

from ...configuration.constants import DBType
from ...db_meta.enums import ClusterType
from ..dbbase.constants import IpSource
from .host import list_cap_specs_cache, list_cap_specs_ssd, list_cap_specs_tendisplus, list_cities, list_host_specs

SWAGGER_TAG = "infras"


class DBTypeViewSet(viewsets.SystemViewSet):
    @common_swagger_auto_schema(
        operation_summary=_("查询集群类型"),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False)
    def list_db_types(self, requests, *args, **kwargs):
        db_types = [{"id": db_type[0], "name": db_type[1]} for db_type in DBType.get_choices()]
        return Response(db_types)


class LogicalCityViewSet(viewsets.SystemViewSet):
    @common_swagger_auto_schema(
        operation_summary=_("查询服务器资源的城市信息"),
        responses={status.HTTP_200_OK: serializers.CitySLZ(label=_("城市信息"), many=True)},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False)
    def list_cities(self, requests, *args, **kwargs):
        serializer = serializers.CitySLZ(list_cities(), many=True)
        return Response(serializer.data)


class HostSpecViewSet(viewsets.SystemViewSet):
    serializer_class = None

    @common_swagger_auto_schema(
        operation_summary=_("服务器规格列表"),
        responses={status.HTTP_200_OK: serializers.HostSpecSLZ(label=_("服务器规格信息"), many=True)},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False)
    def list_host_specs(self, request, *args, **kwargs):
        serializer = serializers.HostSpecSLZ(list_host_specs(), many=True)
        return Response(serializer.data)


class CapSpecViewSet(viewsets.SystemViewSet):
    serializer_class = serializers.QueryCapSpecSLZ

    @common_swagger_auto_schema(
        operation_summary=_("容量规格列表"),
        request_body=serializers.QueryCapSpecSLZ(),
        responses={status.HTTP_200_OK: serializers.CapSpecSLZ(label=_("申请容量规格信息"), many=True)},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False)
    def list_cap_specs(self, request, *args, **kwargs):
        """申请容量下拉框"""

        params = self.params_validate(self.get_serializer_class())

        # 计算出cpu/mem/disk/group
        cpu, mem, disk, group = None, None, None, None
        if params["ip_source"] == IpSource.MANUAL_INPUT:
            master = params["nodes"]["master"]
            slave = params["nodes"]["slave"]

            # 判空直接返回空，或者返回一个默认选项
            if not (master and slave):
                return Response([])

            # 取最小机器数为一组
            group = min(len(master), len(slave))

            # 在机器规格保持一致的情况下，任取一台
            bk_cpu = master[0]["bk_cpu"]
            bk_mem = master[0]["bk_mem"]
            bk_disk = master[0]["bk_disk"]

            try:
                cpu = int(bk_cpu)
                mem = int(bk_mem)
                disk = int(bk_disk)
            except TypeError:
                raise ValidationError(_("主机{}配置异常，无法获取到合法的cpu({})或内存({})").format(master[0]["ip"], bk_cpu, bk_mem))

        cluster_type = params.get("cluster_type")

        # 区分架构生成规格选项
        if cluster_type in [
            ClusterType.TendisTwemproxyRedisInstance,
        ]:
            cap_specs = list_cap_specs_cache(params["ip_source"], cpu, mem, disk, group)
        elif cluster_type in [ClusterType.TendisTwemproxyTendisplusIns, ClusterType.TendisPredixyTendisplusCluster]:
            cap_specs = list_cap_specs_tendisplus(params["ip_source"], cpu, mem, disk, group)
        elif cluster_type in [
            ClusterType.TwemproxyTendisSSDInstance,
        ]:
            cap_specs = list_cap_specs_ssd(params["ip_source"], cpu, mem, disk, group)
        else:
            raise ValidationError(_("暂不支持该集群类型: {}".format(cluster_type)))

        serializer = serializers.CapSpecSLZ(cap_specs, many=True)

        return Response(serializer.data)
