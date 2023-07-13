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

from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.redis.base import BaseRedisTicketFlowBuilder
from backend.ticket.constants import TicketType, AffinityEnum


class RedisClusterCutOffDetailSerializer(serializers.Serializer):
    """整机替换"""

    class InfoSerializer(serializers.Serializer):
        class HostInfoSerializer(serializers.Serializer):
            ip = serializers.IPAddressField()
            spec_id = serializers.IntegerField()

        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
        proxy = serializers.ListField(help_text=_("proxy列表"), child=HostInfoSerializer(), required=False)
        redis_master = serializers.ListField(help_text=_("proxy列表"), child=HostInfoSerializer(), required=False)
        redis_slave = serializers.ListField(help_text=_("proxy列表"), child=HostInfoSerializer(), required=False)

    ip_source = serializers.ChoiceField(help_text=_("主机来源"), choices=IpSource.get_choices())
    infos = serializers.ListField(help_text=_("批量操作参数列表"), child=InfoSerializer())


class RedisClusterCutOffParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_cluster_cutoff_scene

    def format_ticket_data(self):
        super().format_ticket_data()


class RedisClusterCutOffResourceParamBuilder(builders.ResourceApplyParamBuilder):
    def post_callback(self):
        nodes = self.ticket_data.pop('nodes', [])

        next_flow = self.ticket.next_flow()
        ticket_data = next_flow.details["ticket_data"]

        for info_index, info in enumerate(self.ticket_data["infos"]):
            for role in ["redis_master", "proxy", "redis_slave"]:
                role_hosts = info.get(role)
                if not role_hosts:
                    continue

                role_group = "backend_group" if role == "redis_master" else role
                for role_host_index, role_host in enumerate(role_hosts):
                    role_host["target"] = nodes.get(f"{info_index}_{role_group}")[role_host_index]

                # 保留下个节点更完整的resource_spec
                info["resource_spec"] = ticket_data['infos'][info_index]["resource_spec"]
                info["resource_spec"].pop("backend_group", None)

            ticket_data['infos'][info_index] = info

        next_flow.save(update_fields=["details"])
        super().post_callback()


@builders.BuilderFactory.register(TicketType.REDIS_CLUSTER_CUTOFF, is_apply=True)
class RedisClusterCutOffFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisClusterCutOffDetailSerializer
    inner_flow_builder = RedisClusterCutOffParamBuilder
    inner_flow_name = _("整机替换")
    resource_batch_apply_builder = RedisClusterCutOffResourceParamBuilder

    @property
    def need_itsm(self):
        return False

    def patch_ticket_detail(self):
        """redis_master -> backend_group"""

        super().patch_ticket_detail()

        resource_spec = {}
        for info in self.ticket.details["infos"]:
            for role in ["redis_master", "proxy", "redis_slave"]:
                role_hosts = info.get(role)
                if not role_hosts:
                    continue
                role_group = "backend_group" if role == "redis_master" else role
                role_group_affinity = AffinityEnum.CROS_SUBZONE if role_group == "backend_group" else AffinityEnum.NONE
                resource_spec[role_group] = {
                    "spec_id": info[role][0]["spec_id"],
                    "count": len(role_hosts),
                    "affinity": role_group_affinity.value
                }
            info["resource_spec"] = resource_spec

        print(self.ticket.details["infos"])
        self.ticket.save(update_fields=["details"])

