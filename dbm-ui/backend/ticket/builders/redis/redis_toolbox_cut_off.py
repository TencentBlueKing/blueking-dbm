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
import itertools
from collections import defaultdict

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.configuration.constants import AffinityEnum
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster, StorageInstance
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.common.base import (
    BaseOperateResourceParamBuilder,
    DisplayInfoSerializer,
    HostRecycleSerializer,
    SkipToRepresentationMixin,
)
from backend.ticket.builders.redis.base import BaseRedisTicketFlowBuilder, ClusterValidateMixin
from backend.ticket.constants import TicketType


class RedisClusterCutOffDetailSerializer(SkipToRepresentationMixin, ClusterValidateMixin, serializers.Serializer):
    """整机替换"""

    class InfoSerializer(DisplayInfoSerializer):
        class HostInfoSerializer(serializers.Serializer):
            ip = serializers.IPAddressField()
            spec_id = serializers.IntegerField()
            bk_host_id = serializers.IntegerField()

        cluster_ids = serializers.ListField(help_text=_("集群列表"), child=serializers.IntegerField())
        bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
        proxy = serializers.ListField(help_text=_("proxy列表"), child=HostInfoSerializer(), required=False)
        redis_master = serializers.ListField(help_text=_("master列表"), child=HostInfoSerializer(), required=False)
        redis_slave = serializers.ListField(help_text=_("slave列表"), child=HostInfoSerializer(), required=False)
        resource_spec = serializers.JSONField(required=False, help_text=_("资源申请信息(前端不用传递，后台渲染)"))

    ip_source = serializers.ChoiceField(
        help_text=_("主机来源"), choices=IpSource.get_choices(), default=IpSource.RESOURCE_POOL
    )
    ip_recycle = HostRecycleSerializer(help_text=_("主机回收信息"), default=HostRecycleSerializer.DEFAULT)
    infos = serializers.ListField(help_text=_("批量操作参数列表"), child=InfoSerializer())


class RedisClusterCutOffParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_cluster_cutoff_scene

    def format_ticket_data(self):
        super().format_ticket_data()


class RedisClusterCutOffResourceParamBuilder(BaseOperateResourceParamBuilder):
    def post_callback(self):
        nodes = self.ticket_data.pop("nodes", [])

        next_flow = self.ticket.next_flow()
        ticket_data = next_flow.details["ticket_data"]

        for info_index, info in enumerate(self.ticket_data["infos"]):
            slave_role_groups = []
            for role in [InstanceRole.REDIS_PROXY.value, InstanceRole.REDIS_SLAVE.value, InstanceRole.REDIS_MASTER]:
                role_hosts, role_group = info.get(role), role

                if not role_hosts:
                    continue

                for role_host_index, role_host in enumerate(role_hosts):
                    if role == InstanceRole.REDIS_MASTER:
                        role_group, index = "backend_group", role_host_index
                    elif role == InstanceRole.REDIS_SLAVE:
                        role_group, index = f"{role}_{role_host['ip']}", 0
                        slave_role_groups.append(role_group)
                    elif role == InstanceRole.REDIS_PROXY:
                        role_group, index = role, role_host_index

                    role_host["target"] = nodes.get(f"{info_index}_{role_group}")[index]

            # 保留下个节点更完整的resource_spec
            info["resource_spec"] = ticket_data["infos"][info_index]["resource_spec"]
            info["resource_spec"].pop("backend_group", None)
            # 将redis_slave_{ip}重命名为redis_slave
            if slave_role_groups:
                info["resource_spec"][InstanceRole.REDIS_SLAVE] = info["resource_spec"][slave_role_groups[0]]
                info["resource_spec"] = {k: v for k, v in info["resource_spec"].items() if k not in slave_role_groups}
            ticket_data["infos"][info_index] = info

        next_flow.save(update_fields=["details"])
        super().post_callback()


@builders.BuilderFactory.register(TicketType.REDIS_CLUSTER_CUTOFF, is_apply=True, is_recycle=True)
class RedisClusterCutOffFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisClusterCutOffDetailSerializer
    inner_flow_builder = RedisClusterCutOffParamBuilder
    inner_flow_name = _("整机替换")
    resource_batch_apply_builder = RedisClusterCutOffResourceParamBuilder
    need_patch_recycle_host_details = True

    def patch_master_resource(self, cluster, info, resource_spec, old_nodes):
        role = InstanceRole.REDIS_MASTER.value
        role_hosts = info.get(role)

        if not info.get(role):
            return

        old_nodes[role].extend(role_hosts)

        resource_spec["backend_group"] = {
            "spec_id": info[role][0]["spec_id"],
            "count": len(role_hosts),
            "location_spec": {"city": cluster.region, "sub_zone_ids": []},
            "affinity": cluster.disaster_tolerance_level,
        }

        # 资源申请同城同园区条件：补充园区id, 且需传include_or_exclude=True来指定申请的园区
        bk_sub_zone_id = cluster.storageinstance_set.first().machine.bk_sub_zone_id
        if cluster.disaster_tolerance_level in [AffinityEnum.SAME_SUBZONE, AffinityEnum.SAME_SUBZONE_CROSS_SWTICH]:
            resource_spec["backend_group"]["location_spec"].update(
                sub_zone_ids=[bk_sub_zone_id], include_or_exclude=True
            )

        # 替换redis master需要将slave也下架，所以需要加入old_nodes
        redis_masters = StorageInstance.objects.prefetch_related("as_ejector__receiver", "machine").filter(
            cluster=cluster, machine__ip__in=[host["ip"] for host in role_hosts]
        )

        # 使用集合存储已添加的ip地址
        seen_ips = set()
        for master in redis_masters:
            slave = master.as_ejector.get().receiver.machine
            if slave.ip not in seen_ips:
                old_nodes[InstanceRole.REDIS_SLAVE].append(
                    {
                        "ip": slave.ip,
                        "bk_host_id": slave.bk_host_id,
                        "master_ip": master.machine.ip,
                        "master_spec_id": master.machine.spec_id,
                    }
                )
                seen_ips.add(slave.ip)

    def patch_slave_resource(self, cluster, info, resource_spec, old_nodes):
        role = InstanceRole.REDIS_SLAVE.value
        role_hosts = info.get(role)

        if not info.get(role):
            return

        old_nodes[role].extend(role_hosts)

        redis_slaves = StorageInstance.objects.prefetch_related("as_receiver__ejector", "machine").filter(
            cluster=cluster, machine__ip__in=[host["ip"] for host in role_hosts]
        )
        redis_slave_ip_map = {slave.machine.ip: slave for slave in redis_slaves}
        for role_host in role_hosts:
            redis_master = redis_slave_ip_map[role_host["ip"]].as_receiver.get().ejector

            # slave的一一替换，以ip为key作为分组名
            group_key = f"{role}_{role_host['ip']}"
            resource_spec[group_key] = {
                "spec_id": role_host["spec_id"],
                "count": 1,
                "location_spec": {"city": cluster.region, "sub_zone_ids": []},
                "affinity": cluster.disaster_tolerance_level,
            }

            # 同园区，则slave与master在相同的subzone，跨园区，则排除master的subzone
            if cluster.disaster_tolerance_level == AffinityEnum.CROS_SUBZONE:
                resource_spec[group_key]["location_spec"].update(
                    sub_zone_ids=[redis_master.machine.bk_sub_zone_id], include_or_exclue=False
                )
            elif cluster.disaster_tolerance_level in [
                AffinityEnum.SAME_SUBZONE,
                AffinityEnum.SAME_SUBZONE_CROSS_SWTICH,
            ]:
                resource_spec[group_key]["location_spec"].update(
                    sub_zone_ids=[redis_master.machine.bk_sub_zone_id], include_or_exclue=True
                )

    def patch_proxy_resource(self, cluster, info, resource_spec, old_nodes):
        role = InstanceRole.REDIS_PROXY.value
        role_hosts = info.get(role)

        if not info.get(role):
            return

        old_nodes[role].extend(role_hosts)

        resource_spec[role] = {
            "spec_id": info[role][0]["spec_id"],
            "count": len(role_hosts),
            "location_spec": {"city": cluster.region, "sub_zone_ids": []},
            "affinity": cluster.disaster_tolerance_level,
            # 跨园区情况下，proxy则至少跨两个机房
            "group_count": 2,
        }

        # 资源申请同城同园区条件：补充园区id, 且需传include_or_exclude=True来指定申请的园区
        bk_sub_zone_id = cluster.storageinstance_set.first().machine.bk_sub_zone_id
        if cluster.disaster_tolerance_level in [AffinityEnum.SAME_SUBZONE, AffinityEnum.SAME_SUBZONE_CROSS_SWTICH]:
            resource_spec["backend_group"]["location_spec"].update(
                sub_zone_ids=[bk_sub_zone_id], include_or_exclude=True
            )

    def patch_resource_and_old_nodes(self):
        cluster_ids = list(itertools.chain(*[infos["cluster_ids"] for infos in self.ticket.details["infos"]]))
        cluster_map = {cluster.id: cluster for cluster in Cluster.objects.filter(id__in=cluster_ids)}

        for info in self.ticket.details["infos"]:
            old_nodes = defaultdict(list)
            # 取第一个cluster即可，即使是多集群，也是单机多实例的情况
            cluster = cluster_map[info["cluster_ids"][0]]
            resource_spec = {}

            self.patch_master_resource(cluster, info, resource_spec, old_nodes)
            self.patch_slave_resource(cluster, info, resource_spec, old_nodes)
            self.patch_proxy_resource(cluster, info, resource_spec, old_nodes)

            info["resource_spec"] = resource_spec
            info.update(resource_spec=resource_spec, old_nodes=old_nodes)

        self.ticket.save(update_fields=["details"])

    def patch_ticket_detail(self):
        """redis_master -> backend_group"""
        self.patch_resource_and_old_nodes()
        super().patch_ticket_detail()
