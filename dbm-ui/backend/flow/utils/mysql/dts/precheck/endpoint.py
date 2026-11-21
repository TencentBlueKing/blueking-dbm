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

from collections.abc import Callable

from django.utils.translation import gettext_lazy as _

from backend.db_meta.enums import ClusterType, InstanceRole, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster
from backend.flow.utils.mysql.dts.precheck.collector import Endpoint, PrecheckCollectError
from blue_krill.data_types.enum import EnumField, StrStructuredEnum


class Side(StrStructuredEnum):
    SOURCE = EnumField("source", _("source"))
    TARGET = EnumField("target", _("target"))


def _storage_by_role(cluster: Cluster, role: InstanceRole):
    instance = (
        cluster.storageinstance_set.select_related("machine").filter(instance_role=role.value).order_by("id").first()
    )
    if instance is None and role == InstanceRole.ORPHAN:
        instance = cluster.storageinstance_set.select_related("machine").order_by("id").first()
    return instance


def _spider_master(cluster: Cluster):
    return (
        cluster.proxyinstance_set.select_related("machine")
        .filter(tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER.value)
        .order_by("id")
        .first()
    )


_ENDPOINT_RESOLVERS: dict[tuple[str, Side], Callable[[Cluster], object]] = {
    (ClusterType.TenDBHA.value, Side.SOURCE): lambda cluster: _storage_by_role(cluster, InstanceRole.BACKEND_MASTER),
    (ClusterType.TenDBHA.value, Side.TARGET): lambda cluster: _storage_by_role(cluster, InstanceRole.BACKEND_MASTER),
    (ClusterType.TenDBSingle.value, Side.SOURCE): lambda cluster: _storage_by_role(cluster, InstanceRole.ORPHAN),
    (ClusterType.TenDBSingle.value, Side.TARGET): lambda cluster: _storage_by_role(cluster, InstanceRole.ORPHAN),
    (ClusterType.TenDBCluster.value, Side.SOURCE): lambda cluster: _storage_by_role(
        cluster, InstanceRole.REMOTE_MASTER
    ),
    (ClusterType.TenDBCluster.value, Side.TARGET): _spider_master,
}


def _parse_address(address: str) -> tuple[str, int]:
    try:
        ip, port_text = address.strip().rsplit(":", 1)
        port = int(port_text)
    except (AttributeError, TypeError, ValueError) as exc:
        raise PrecheckCollectError(_("无效实例地址: {!r}").format(address)) from exc
    if not ip or not 1 <= port <= 65535:
        raise PrecheckCollectError(_("无效实例地址: {!r}").format(address))
    return ip, port


def resolve_endpoint(cluster: Cluster, side: Side, *, address: str = "") -> Endpoint:
    if address:
        ip, port = _parse_address(address)
        return Endpoint(
            ip=ip,
            port=port,
            bk_cloud_id=cluster.bk_cloud_id,
            cluster_id=cluster.id,
        )

    resolver = _ENDPOINT_RESOLVERS.get((cluster.cluster_type, side))
    if resolver is None:
        raise PrecheckCollectError(_("集群 {} 类型 {} 不支持 {} 端预检查").format(cluster.id, cluster.cluster_type, side.value))
    instance = resolver(cluster)
    if instance is None:
        raise PrecheckCollectError(_("集群 {} 无法解析 {} 端连接点").format(cluster.id, side.value))
    return Endpoint(
        ip=instance.machine.ip,
        port=instance.port,
        bk_cloud_id=cluster.bk_cloud_id,
        cluster_id=cluster.id,
    )
