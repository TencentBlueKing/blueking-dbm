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
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_meta.enums import ClusterType
from backend.db_package.constants import PackageType
from backend.db_package.models import Package
from backend.db_services.version import constants, serializers

SWAGGER_TAG = "version"


class VersionViewSet(viewsets.SystemViewSet):
    @common_swagger_auto_schema(
        operation_summary=_("查询数据库版本列表"),
        query_serializer=serializers.ListVersionSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=serializers.ListVersionSerializer)
    def list_versions(self, requests, *args, **kwargs):
        """版本列表"""
        validated_data = self.params_validate(self.get_serializer_class())
        query_key = validated_data["query_key"]

        if query_key in [ClusterType.TenDBSingle, ClusterType.TenDBHA, ClusterType.TenDBCluster, PackageType.MySQL]:
            versions = constants.MySQLVersion.get_values()
        elif query_key in [
            PackageType.TendisPlus,
            ClusterType.TendisPredixyTendisplusCluster,
            ClusterType.TendisTwemproxyTendisplusIns,
            ClusterType.TendisTendisplusInsance,
            ClusterType.TendisTendisplusCluster,
        ]:
            versions = constants.TendisPlusVersion.get_values()
        elif query_key in [
            PackageType.Proxy,
            PackageType.DBActuator,
            PackageType.RedisTools,
            PackageType.DbMon,
            PackageType.MySQLRotateBinlog,
            PackageType.MySQLToolKit,
            PackageType.DbBackup,
            PackageType.MySQLChecksum,
            PackageType.MySQLMonitor,
            PackageType.MySQLCrond,
        ]:
            versions = [constants.LATEST]
        elif query_key in [
            PackageType.Twemproxy,
        ]:
            versions = constants.TwemproxyVersion.get_values()
        elif query_key in [
            PackageType.Predixy,
        ]:
            versions = constants.PredixyVersion.get_values()

        elif query_key in [
            PackageType.Redis,
            ClusterType.TendisPredixyRedisCluster,
            ClusterType.TendisTwemproxyRedisInstance,
            ClusterType.TendisRedisInstance,
            ClusterType.TendisRedisCluster,
        ]:
            versions = constants.RedisVersion.get_values()
        elif query_key in [
            PackageType.TendisSsd,
            ClusterType.TwemproxyTendisSSDInstance,
        ]:
            versions = constants.TendisSsdVersion.get_values()
        else:
            versions = list(Package.objects.filter(pkg_type=query_key).values_list("version", flat=True))
        if not versions:
            # 当没有版本时，默认给个 latest 版本
            # TODO 后续考虑废除 latest，所有二进制都给带上版本号，以便排查问题
            versions = [constants.LATEST]
        return Response(versions)
