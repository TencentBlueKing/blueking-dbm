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
from backend.db_package.constants import FULL_SEGMENT_PKG_TYPES, PackageType
from backend.db_package.models import Package
from backend.db_services.version import constants
from backend.db_services.version.constants import (
    FULL_VERSION_SEGMENT_COUNT,
    SHORT_VERSION_SEGMENT_COUNT,
    VERSION_PADDING_SEGMENT,
)


def get_display_segment_count(pkg_type: str) -> int:
    """获取指定 pkg_type 对外展示的版本段数"""
    return FULL_VERSION_SEGMENT_COUNT if pkg_type in FULL_SEGMENT_PKG_TYPES else SHORT_VERSION_SEGMENT_COUNT


def pad_full_version(full_version: str) -> str:
    """
    将前端传入的 N 段版本号 (N=pkg_type 对应展示段数) 补齐为底层 6 段
    例如 pkg_type=redis (3 段), full_version="6.2.7" -> "6.2.7.0.0.0"
    """
    if not full_version:
        return full_version
    segs = full_version.split(".")
    if len(segs) == FULL_VERSION_SEGMENT_COUNT:
        return full_version
    segs += [VERSION_PADDING_SEGMENT] * (FULL_VERSION_SEGMENT_COUNT - len(segs))
    return ".".join(segs)


def strip_full_version(full_version: str, pkg_type: str) -> str:
    """
    将 6 段存储版本号截取为对外展示段数
    例如 pkg_type=redis (3 段), full_version="6.2.7.0.0.0" -> "6.2.7"
    """
    if not full_version:
        return full_version
    expected = get_display_segment_count(pkg_type)
    segs = full_version.split(".")
    if len(segs) <= expected:
        return full_version
    return ".".join(segs[:expected])


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
        PackageType.MySQLProxy,
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
    elif query_key in [PackageType.Sqlserver]:
        versions = constants.SqlserverVersion.get_values()
    else:
        versions = list(Package.objects.filter(pkg_type=query_key).values_list("version", flat=True))

    if not versions:
        # 当没有版本时，默认给个 latest 版本
        versions = [constants.LATEST]

    return versions
