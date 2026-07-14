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
import re

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import DBVersion, Distribution
from backend.db_package.constants import PackageType
from backend.db_package.models import Package
from backend.db_services.version import constants
from backend.db_services.version.constants import (
    FULL_VERSION_SEGMENT_COUNT,
    SHORT_VERSION_SEGMENT_COUNT,
    VERSION_PADDING_SEGMENT,
)

_MONGODB_LIST_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


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


def strip_full_version(full_version: str, display_version_seg: int) -> str:
    """
    将 6 段存储版本号截取为对外展示段数
    例如 pkg_type=redis (3 段), full_version="6.2.7.0.0.0" -> "6.2.7"
    """
    if not full_version:
        return full_version
    segs = full_version.split(".")
    if len(segs) <= display_version_seg:
        return full_version
    return ".".join(segs[:display_version_seg])


def _normalize_mongodb_list_version(version: str):
    """将介质版本规范为 x.y.z; 无法解析时返回 None"""
    if not version:
        return None
    short_version = strip_full_version(version.strip(), SHORT_VERSION_SEGMENT_COUNT)
    if _MONGODB_LIST_VERSION_RE.match(short_version):
        return short_version
    try:
        from backend.flow.utils.mongodb.version_utils import normalize_mongodb_full_version

        normalized = normalize_mongodb_full_version(version)
        display_version = normalized.removeprefix("mongodb-").split("-", 1)[0]
        if _MONGODB_LIST_VERSION_RE.match(display_version):
            return display_version
    except ValueError:
        return None
    return None


def _mongodb_list_version_sort_key(version: str) -> tuple:
    from backend.flow.utils.mongodb.version_utils import _instance_version_tuple

    return _instance_version_tuple("mongodb-{}".format(version))


def query_mongodb_versions():
    """MongoDB 版本列表: 仅返回 enable=True, 对外展示 x.y.z, 按版本号降序"""
    distribution_ids = Distribution.objects.filter(pkg_type=PackageType.MongoDB).values_list("id", flat=True)
    versions = list(
        DBVersion.objects.filter(distribution_id__in=distribution_ids, enable=True)
        .order_by("-full_version")
        .values_list("full_version", flat=True)
    )
    if not versions:
        versions = list(
            Package.objects.filter(pkg_type=PackageType.MongoDB, enable=True)
            .order_by("-version")
            .values_list("version", flat=True)
        )

    seen = set()
    result = []
    for version in versions:
        short_version = _normalize_mongodb_list_version(version)
        if not short_version or short_version in seen:
            continue
        seen.add(short_version)
        result.append(short_version)
    result.sort(key=_mongodb_list_version_sort_key, reverse=True)
    return result


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
    elif query_key in [PackageType.MongoDB]:
        versions = query_mongodb_versions()
    else:
        versions = list(Package.objects.filter(pkg_type=query_key).values_list("version", flat=True))

    if not versions:
        # 当没有版本时，默认给个 latest 版本
        versions = [constants.LATEST]

    return versions
