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
from backend.db_meta.enums import ClusterType
from backend.db_package.constants import PackageType
from backend.db_package.models import Package
from backend.db_services.version import constants


def query_versions_by_key(query_key):
    """集群类型->集群版本"""

    if query_key in [ClusterType.TenDBSingle, ClusterType.TenDBHA, ClusterType.TenDBCluster, PackageType.MySQL]:
        versions = constants.MySQLVersion.get_values()
    elif query_key in [PackageType.Spider]:
        versions = constants.SpiderVersion.get_values()
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
        PackageType.RedisDts,
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
        versions = [constants.LATEST]

    return versions
