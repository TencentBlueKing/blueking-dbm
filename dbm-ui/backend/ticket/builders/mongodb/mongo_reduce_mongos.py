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

from collections import defaultdict

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_meta.enums import ClusterType, MachineType
from backend.db_meta.models import AppCache, Cluster, ProxyInstance, StorageInstance
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.common.base import CommonValidate, HostInfoSerializer
from backend.ticket.builders.mongodb.base import (
    BaseMongoDBOperateDetailSerializer,
    BaseMongoOperateFlowParamBuilder,
    BaseMongoShardedTicketFlowBuilder,
    assign_recycle_hosts,
)
from backend.ticket.constants import TicketType


def collect_reduce_mongos_recycle_hosts(bk_biz_id: int, infos: list) -> list:
    """缩容 mongos 后，本业务已无 Proxy 也无 Storage 的主机。"""

    hosts = {}
    # (cluster_id, ip, cloud) -> 节点上明确给出的端口
    explicit_ports = defaultdict(set)
    # 节点没带 port 的 (cluster_id, ip, cloud)
    portless = set()
    for info in infos or []:
        cluster_id = info["cluster_id"]
        for node in (info.get("old_nodes") or {}).get("mongos") or []:
            key = (node["ip"], int(node["bk_cloud_id"]))
            hosts[key] = node["bk_host_id"]
            port = node.get("port")
            if port is None:
                portless.add((cluster_id, key))
            else:
                explicit_ports[(cluster_id, key)].add(int(port))
    if not hosts:
        return []

    removed_ports = defaultdict(set)
    for (_cluster_id, key), ports in explicit_ports.items():
        removed_ports[key] |= ports

    # 节点未带 port。假定同集群同机只有一个 mongos，用该集群全部 mongos 端口当作本次待移除端口。
    fallback_clusters = {cluster_id for cluster_id, key in portless if (cluster_id, key) not in explicit_ports}
    cluster_ports = {
        cluster_id: {
            int(port) for port in ProxyInstance.objects.filter(cluster__id=cluster_id).values_list("port", flat=True)
        }
        for cluster_id in fallback_clusters
    }
    for cluster_id, key in portless:
        if (cluster_id, key) in explicit_ports:
            continue
        removed_ports[key] |= cluster_ports[cluster_id]

    ips = list({ip for ip, _cloud_id in hosts})
    storage_keys = {
        (ip, int(cloud_id))
        for ip, cloud_id in StorageInstance.objects.filter(bk_biz_id=bk_biz_id, machine__ip__in=ips).values_list(
            "machine__ip", "machine__bk_cloud_id"
        )
    }
    proxy_left = set()
    proxy_rows = ProxyInstance.objects.filter(bk_biz_id=bk_biz_id, machine__ip__in=ips).values_list(
        "machine__ip", "machine__bk_cloud_id", "port"
    )
    for ip, cloud_id, port in proxy_rows:
        key = (ip, int(cloud_id))
        if key not in hosts:
            continue
        if int(port) not in removed_ports[key]:
            proxy_left.add(key)

    result = []
    seen_host_ids = set()
    for key, host_id in hosts.items():
        if key in storage_keys or key in proxy_left or host_id in seen_host_ids:
            continue
        seen_host_ids.add(host_id)
        result.append({"ip": key[0], "bk_host_id": host_id, "bk_cloud_id": key[1]})
    return result


class MongoDBReduceMongosDetailSerializer(BaseMongoDBOperateDetailSerializer):
    class ReduceMongosDetailSerializer(serializers.Serializer):
        class OldNodesSerializer(serializers.Serializer):
            mongos = serializers.ListSerializer(help_text=_("缩容mongos"), child=HostInfoSerializer())

        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        role = serializers.CharField(help_text=_("接入层角色"), required=False, default=MachineType.MONGOS)
        old_nodes = OldNodesSerializer(help_text=_("缩容信息"))

    is_safe = serializers.BooleanField(help_text=_("是否做安全检测"), default=True, required=False)
    infos = serializers.ListSerializer(help_text=_("缩容接入层申请信息"), child=ReduceMongosDetailSerializer())

    def validate(self, attrs):
        attrs = super().validate(attrs)
        cluster_ids = [info["cluster_id"] for info in attrs["infos"]]
        cluster_map = Cluster.objects.prefetch_related("proxyinstance_set__machine").in_bulk(cluster_ids)

        # 校验集群类型合法性
        CommonValidate.validated_cluster_type(cluster_ids, ClusterType.MongoShardedCluster)

        for info in attrs["infos"]:
            cluster = cluster_map[info["cluster_id"]]
            mongos_count = cluster.proxyinstance_set.count()
            info["reduce_count"] = len(info["old_nodes"]["mongos"])

            # 缩容后的整体mongos机器数量不能小于2
            if mongos_count - info["reduce_count"] < 2:
                raise serializers.ValidationError(_("缩容后的整体mongos机器数量不能小于2"))

            # 缩容后的整体mongos需要满足集群亲和性，等后续支持指定count缩容后才校验
            machines = [s.machine for s in cluster.proxyinstance_set.all()]
            shrink_ips = [node["ip"] for node in info["old_nodes"]["mongos"]]
            self.validate_shrink_ip_machine_affinity(cluster, machines, shrink_ips)

            # 缩容的mongos机器台数不能高于当前规格台数, 且不能为负数。TODO: 等支持指定规格数量缩容后，才需要这个校验
            # if mongos_count <= info["reduce_count"] or info["reduce_count"] < 0:
            #     raise serializers.ValidationError(_("缩容的mongos机器台数不能高于当前规格台数, 且不能为负数"))

        return attrs


class MongoDBReduceMongosFlowParamBuilder(BaseMongoOperateFlowParamBuilder):
    controller = MongoDBController.reduce_mongos

    def format_ticket_data(self):
        bk_biz_id = self.ticket_data["bk_biz_id"]
        self.ticket_data["db_app_abbr"] = AppCache.objects.get(bk_biz_id=bk_biz_id).db_app_abbr
        self.ticket_data["infos"] = self.add_cluster_info(self.ticket_data["infos"])
        for info in self.ticket_data["infos"]:
            info["reduce_nodes"] = info.pop("old_nodes")["mongos"]


@builders.BuilderFactory.register(TicketType.MONGODB_REDUCE_MONGOS, is_recycle=True, iam=ActionEnum.MONGODB_MANAGE)
class MongoDBReduceMongosFlowBuilder(BaseMongoShardedTicketFlowBuilder):
    serializer = MongoDBReduceMongosDetailSerializer
    inner_flow_builder = MongoDBReduceMongosFlowParamBuilder
    inner_flow_name = _("MongoDB 缩容接入层执行")
    # 下架主机由 patch_ticket_detail 按缩完后的空机写入，不走基类按 old_nodes 全量回填
    need_patch_recycle_host_details = False
    need_patch_machine_details = True

    def patch_ticket_detail(self):
        # old_nodes 仍是要缩的 mongos；下架单只收缩完后已无存储、也无 mongos 的主机
        hosts = collect_reduce_mongos_recycle_hosts(self.ticket.bk_biz_id, self.ticket.details.get("infos") or [])
        assign_recycle_hosts(self.ticket.details, hosts)
        super().patch_ticket_detail()
