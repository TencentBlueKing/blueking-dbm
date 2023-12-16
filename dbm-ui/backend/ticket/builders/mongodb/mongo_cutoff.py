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

from backend.db_meta.enums import MachineType
from backend.db_meta.models import Cluster, Machine
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.ticket import builders
from backend.ticket.builders.mongodb.base import (
    BaseMongoDBOperateDetailSerializer,
    BaseMongoDBOperateResourceParamBuilder,
    BaseMongoDBTicketFlowBuilder,
)
from backend.ticket.constants import TicketType


class MongoDBCutoffDetailSerializer(BaseMongoDBOperateDetailSerializer):
    class ACutoffDetailSerializer(serializers.Serializer):
        class IpSpecSLZ(serializers.Serializer):
            ip = serializers.CharField(help_text=_("替换主机IP"))
            spec_id = serializers.IntegerField(help_text=_("规格ID"))

        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        mongos = serializers.ListSerializer(child=IpSpecSLZ(help_text=_("替换mongos的信息")), required=False)
        mongodb = serializers.ListSerializer(child=IpSpecSLZ(help_text=_("替换mongodb的信息")), required=False)
        mongo_config = serializers.ListSerializer(child=IpSpecSLZ(help_text=_("替换mongo_config的信息")), required=False)

    ip_source = serializers.ChoiceField(
        help_text=_("主机来源"), choices=IpSource.get_choices(), default=IpSource.RESOURCE_POOL
    )
    infos = serializers.ListSerializer(help_text=_("整机替换信息"), child=ACutoffDetailSerializer())

    def validate(self, attrs):
        # 校验替换的mongodb机器不在同一分片中
        machines_ips = []
        for info in attrs["infos"]:
            mongodb_ips = [d["ip"] for d in info["mongodb"]]
            mongodb_config_ips = [d["ip"] for d in info["mongo_config"]]
            machines_ips.extend([*mongodb_ips, *mongodb_config_ips])

        machines = Machine.objects.filter(machine_type__in=[MachineType.MONGOS, MachineType.MONOG_CONFIG]).filter(
            ip__in=machines_ips
        )
        self.validate_machine_in_different_shard(machines)

        return attrs


class MongoDBCutoffFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.fake_scene

    def format_ticket_data(self):
        pass


class MongoDBCutoffResourceParamBuilder(BaseMongoDBOperateResourceParamBuilder):
    def format(self):
        super().format()

    def post_callback(self):
        mongo_roles = [MachineType.MONGOS, MachineType.MONOG_CONFIG, MachineType.MONGODB]
        with self.next_flow_manager() as next_flow:
            for info in next_flow.details["ticket_data"]["infos"]:
                resource_spec = info["resource_spec"]
                # 拆包资源信息：在每个替换信息中填充规格和目标机器
                for role in mongo_roles:
                    for host in info.get("role", []):
                        # 填充规格
                        host["spec_config"] = resource_spec[f"{role}_{host['ip']}"]
                        host["spec_id"] = host["spec_config"]["id"]
                        # 填充主机信息
                        host["target"] = info[f"{role}_{host['ip']}"][0]


@builders.BuilderFactory.register(TicketType.MONGODB_CUTOFF, is_apply=True)
class MongoDBCutoffApplyFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoDBCutoffDetailSerializer
    inner_flow_builder = MongoDBCutoffFlowParamBuilder
    inner_flow_name = _("MongoDB 整机替换执行")
    resource_batch_apply_builder = MongoDBCutoffResourceParamBuilder

    def patch_ticket_detail(self):
        mongo_roles = [MachineType.MONGOS, MachineType.MONOG_CONFIG, MachineType.MONGODB]
        cluster_ids = [info["cluster_id"] for info in self.ticket.details["infos"]]
        id__cluster = Cluster.objects.filter(id__in=cluster_ids)
        for info in self.ticket.details["infos"]:
            city = id__cluster[info["cluster_id"]].region
            # 打包资源信息：按照role_ip这样的命名格式构造每一个资源申请信息组，每组的城市同集群，数量为1
            resource_spec = {}
            for role in mongo_roles:
                for host in info.get("role", []):
                    group_name = f"{role}_{host['ip']}"
                    resource_spec[group_name] = {
                        "spec_id": host["spec_id"],
                        "count": 1,
                        "location_spec": {"city": city, "sub_zone_ids": []},
                    }
            info["resource_spec"] = resource_spec
