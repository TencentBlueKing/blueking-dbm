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

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.db_meta.models import Cluster, StorageInstance
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.common.base import BaseOperateResourceParamBuilder
from backend.ticket.builders.redis.base import BaseRedisTicketFlowBuilder, ClusterValidateMixin
from backend.ticket.constants import TicketType


class RedisClusterCutOffDetailSerializer(ClusterValidateMixin, serializers.Serializer):
    """整机替换"""

    class InfoSerializer(serializers.Serializer):
        class HostInfoSerializer(serializers.Serializer):
            ip = serializers.IPAddressField()
            spec_id = serializers.IntegerField()

        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
        proxy = serializers.ListField(help_text=_("proxy列表"), child=HostInfoSerializer(), required=False)
        redis_master = serializers.ListField(help_text=_("master列表"), child=HostInfoSerializer(), required=False)
        redis_slave = serializers.ListField(help_text=_("slave列表"), child=HostInfoSerializer(), required=False)
        resource_spec = serializers.JSONField(required=False, help_text=_("资源申请信息(前端不用传递，后台渲染)"))

    ip_source = serializers.ChoiceField(help_text=_("主机来源"), choices=IpSource.get_choices())
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
            for role in ["redis_master", "proxy", "redis_slave"]:
                role_hosts = info.get(role)

                if not role_hosts:
                    continue

                role_group = "backend_group" if role == "redis_master" else role
                for role_host_index, role_host in enumerate(role_hosts):
                    if role == "redis_master":
                        role_group, index = "backend_group", role_host_index
                    elif role == "redis_slave":
                        role_group, index = f"{role}_{role_host['ip']}", 0
                    elif role == "proxy":
                        role_group, index = role, role_host_index

                    role_host["target"] = nodes.get(f"{info_index}_{role_group}")[index]

            # 保留下个节点更完整的resource_spec
            info["resource_spec"] = ticket_data["infos"][info_index]["resource_spec"]
            info["resource_spec"].pop("backend_group", None)
            ticket_data["infos"][info_index] = info

        next_flow.save(update_fields=["details"])
        super().post_callback()


@builders.BuilderFactory.register(TicketType.REDIS_CLUSTER_CUTOFF, is_apply=True)
class RedisClusterCutOffFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisClusterCutOffDetailSerializer
    inner_flow_builder = RedisClusterCutOffParamBuilder
    inner_flow_name = _("整机替换")
    resource_batch_apply_builder = RedisClusterCutOffResourceParamBuilder

    def patch_ticket_detail(self):
        """redis_master -> backend_group"""

        super().patch_ticket_detail()

        resource_spec = {}
        cluster_ids = [infos["cluster_id"] for infos in self.ticket.details["infos"]]
        id__cluster = {cluster.id: cluster for cluster in Cluster.objects.filter(id__in=cluster_ids)}
        for info in self.ticket.details["infos"]:
            cluster = id__cluster[info["cluster_id"]]
            for role in ["redis_master", "proxy", "redis_slave"]:
                role_hosts = info.get(role)

                if not role_hosts:
                    continue

                if role == "redis_master":
                    # 如果替换角色是master，则是master/slave成对替换
                    resource_spec["backend_group"] = {
                        "spec_id": info[role][0]["spec_id"],
                        "count": len(role_hosts),
                        "location_spec": {"city": cluster.region, "sub_zone_ids": []},
                        "affinity": cluster.disaster_tolerance_level,
                    }
                elif role == "redis_slave":
                    # 如果是替换slave， 需要和当前集群中的配对的 master 不同机房
                    redis_slaves = StorageInstance.objects.prefetch_related("as_receiver", "machine").filter(
                        cluster=cluster, machine__ip__in=[host["ip"] for host in role_hosts]
                    )
                    ip__redis_slave = {slave.machine.ip: slave for slave in redis_slaves}
                    for role_host in role_hosts:
                        redis_master = ip__redis_slave[role_host["ip"]].as_receiver.get().ejector
                        resource_spec[f"{role}_{role_host['ip']}"] = {
                            "spec_id": role_host["spec_id"],
                            "count": 1,
                            "location_spec": {
                                "city": cluster.region,
                                "sub_zone_ids": [redis_master.machine.bk_sub_zone_id],
                                "include_or_exclue": False,
                            },
                        }
                elif role == "proxy":
                    # TODO: proxy替换的亲和性需要衡量存量proxy的分布，暂时忽略
                    resource_spec[role] = {"spec_id": info[role][0]["spec_id"], "count": len(role_hosts)}

            info["resource_spec"] = resource_spec

        self.ticket.save(update_fields=["details"])
