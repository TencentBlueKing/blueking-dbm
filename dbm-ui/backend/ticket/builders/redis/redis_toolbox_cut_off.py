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
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.redis import RedisController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.common.base import (
    BaseOperateResourceParamBuilder,
    DisplayInfoSerializer,
    SkipToRepresentationMixin,
    TicketBaseValidateSerializerMixin,
)
from backend.ticket.builders.redis.base import BaseRedisTicketFlowBuilder, ClusterValidateMixin
from backend.ticket.constants import TicketType


class RedisClusterCutOffDetailSerializer(
    TicketBaseValidateSerializerMixin, SkipToRepresentationMixin, ClusterValidateMixin, serializers.Serializer
):
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
        resource_spec = serializers.JSONField(required=False, help_text=_("资源申请信息"))
        old_nodes = serializers.JSONField(required=False, help_text=_("回收主机信息"))
        switch_role = serializers.CharField(required=False, help_text=_("替换角色"))

    ip_source = serializers.ChoiceField(
        help_text=_("主机来源"), choices=IpSource.get_choices(), default=IpSource.RESOURCE_POOL
    )
    infos = serializers.ListField(help_text=_("批量操作参数列表"), child=InfoSerializer())

    def validate(self, attrs):
        attrs = super().validate(attrs)
        return attrs


class RedisClusterCutOffParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_cluster_cutoff_scene

    def format_ticket_data(self):
        super().format_ticket_data()


class RedisClusterCutOffResourceParamBuilder(BaseOperateResourceParamBuilder):
    def format(self):
        # 资源申请的一些参数补充
        for info in self.ticket_data["infos"]:
            role_tolerance_map = {"redis_master": 0, "proxy": 0.5, "redis_slave": 0}
            exclusive_machine_map = {}
            cluster = Cluster.objects.get(id=info["cluster_ids"][0])
            if info["switch_role"] == InstanceRole.REDIS_SLAVE.value:
                redis_slaves = StorageInstance.objects.prefetch_related("as_receiver__ejector", "machine").filter(
                    cluster=cluster, machine__ip__in=[host["ip"] for host in info["redis_slave"]]
                )
                exclusive_machine_map = {
                    slave.machine.ip: [slave.as_receiver.get().ejector.machine] for slave in redis_slaves
                }
            if info["switch_role"] == InstanceRole.REDIS_PROXY.value:
                machine_type = cluster.proxyinstance_set.first().machine.machine_type
                common_filters = Q(machine__machine_type=machine_type, cluster__in=info["cluster_ids"]) & ~Q(
                    machine__bk_host_id__in=[host["bk_host_id"] for host in info["proxy"]]
                )
                proxy_insts = list(ProxyInstance.objects.select_related("machine").filter(common_filters))
                exclusive_machine_map = {"proxy": [inst.machine for inst in proxy_insts]}

            for role in info["resource_spec"]:
                self.patch_common_affinity(
                    info,
                    role=role,
                    cluster=cluster,
                    exclusive_hosts=exclusive_machine_map.get(role.split("_")[-1], []),
                    tolerance=role_tolerance_map[info["switch_role"]],
                )

    def post_callback(self):

        next_flow = self.ticket.next_flow()
        ticket_data = next_flow.details["ticket_data"]
        for info in ticket_data["infos"]:
            switch_role = info["switch_role"]
            for host_index, host in enumerate(info[switch_role]):
                if switch_role == InstanceRole.REDIS_MASTER.value:
                    host["target"] = {}
                    host["target"]["master"] = info["backend_group"][host_index]["master"]
                    host["target"]["slave"] = info["backend_group"][host_index]["slave"]

                elif switch_role == InstanceRole.REDIS_SLAVE:
                    host["target"] = info[f"redis_slave_{host['ip']}"][0]

                elif switch_role == InstanceRole.REDIS_PROXY:
                    host["target"] = info["new_proxy"][host_index]
        next_flow.save(update_fields=["details"])
        super().post_callback()


@builders.BuilderFactory.register(
    TicketType.REDIS_CLUSTER_CUTOFF, is_apply=True, is_recycle=True, async_build=True, iam=ActionEnum.REDIS_MANAGE
)
class RedisClusterCutOffFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisClusterCutOffDetailSerializer
    inner_flow_builder = RedisClusterCutOffParamBuilder
    inner_flow_name = _("整机替换")
    resource_batch_apply_builder = RedisClusterCutOffResourceParamBuilder
    need_patch_recycle_host_details = True
