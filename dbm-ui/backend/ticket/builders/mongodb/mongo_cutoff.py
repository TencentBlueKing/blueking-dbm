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

from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.db_meta.enums import ClusterType, MachineType
from backend.db_meta.models import AppCache, Cluster, Machine, Spec
from backend.db_services.dbbase.constants import IpSource
from backend.db_services.mongodb.resources.query import MongoDBListRetrieveResource
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.ticket import builders
from backend.ticket.builders.mongodb.base import (
    BaseMongoDBOperateDetailSerializer,
    BaseMongoDBOperateResourceParamBuilder,
    BaseMongoDBTicketFlowBuilder,
)
from backend.ticket.constants import TicketType
from backend.utils.basic import get_target_items_from_details


class MongoDBCutoffDetailSerializer(BaseMongoDBOperateDetailSerializer):
    class ACutoffDetailSerializer(serializers.Serializer):
        class IpSpecSLZ(serializers.Serializer):
            ip = serializers.CharField(help_text=_("替换主机IP"))
            bk_cloud_id = serializers.IntegerField(help_text=_("主机所在云区域"))
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

        machine_types = [MachineType.MONGODB, MachineType.MONOG_CONFIG]
        machines = Machine.objects.filter(machine_type__in=machine_types).filter(ip__in=machines_ips)
        self.validate_machine_in_different_shard(machines)

        return attrs


class MongoDBCutoffFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.machine_replace

    def format_ticket_data(self):
        bk_biz_id = self.ticket_data["bk_biz_id"]
        self.ticket_data["bk_app_abbr"] = AppCache.objects.get(bk_biz_id=bk_biz_id).db_app_abbr


class MongoDBCutoffResourceParamBuilder(BaseMongoDBOperateResourceParamBuilder):
    def format(self):
        super().format()

    @staticmethod
    def _get_mongo_inst_desc(instance, storage_id__shard):
        cluster = instance.cluster.first()
        desc = {
            "port": instance.port,
            "cluster_id": cluster.id,
            "db_version": cluster.major_version,
            "domain": cluster.immute_domain,
            "cluster_name": cluster.name,
        }
        if storage_id__shard.get(instance.id):
            desc.update(seg_range=storage_id__shard[instance.id])
        return desc

    def _fill_instance_infos(self, role, machine, storage_id__shard):
        if role == MachineType.MONGOS:
            instances = machine.proxyinstance_set.select_related("machine").prefetch_related("cluster").all()
        else:
            instances = machine.storageinstance_set.select_related("machine").prefetch_related("cluster").all()
        instance_infos = [self._get_mongo_inst_desc(inst, storage_id__shard) for inst in instances]
        return instance_infos

    def post_callback(self):
        mongo_roles = [MachineType.MONGOS, MachineType.MONOG_CONFIG, MachineType.MONGODB]
        with self.next_flow_manager() as next_flow:
            cutoff_infos = next_flow.details["ticket_data"]["infos"]

            # 获取ip和machine的映射
            ips = get_target_items_from_details(cutoff_infos, match_keys=["ip"])
            ip__machine = {
                machine.ip: machine
                for machine in Machine.objects.prefetch_related("storageinstance_set", "proxyinstance_set").filter(
                    ip__in=ips
                )
            }

            # 获取实例的分片信息
            machine_filter = Q(machine__in=list(ip__machine.values()))
            __, storage_id__shard = MongoDBListRetrieveResource.query_storage_shard(machine_filter)

            # 集群ID和集群映射
            cluster_ids = [info["cluster_id"] for info in cutoff_infos]
            id__cluster = {cluster.id: cluster for cluster in Cluster.objects.filter(id__in=cluster_ids)}

            # 拆包资源信息：在每个替换信息中填充规格，目标机器和实例信息
            for info in cutoff_infos:
                resource_spec = info["resource_spec"]
                for role in mongo_roles:
                    for host in info.get(role, []):
                        # 填充规格
                        host["spec_config"] = resource_spec[f"{role}_{host['ip']}"]
                        host["spec_id"] = host["spec_config"]["id"]
                        # 填充主机信息
                        host["target"] = info[f"{role}_{host['ip']}"][0]
                        host["target"]["spec_id"] = host["spec_config"]["id"]
                        # 填充实例信息
                        machine = ip__machine[host["ip"]]
                        host["instances"] = self._fill_instance_infos(role, machine, storage_id__shard)

            # 格式化整机替换的数据结构，
            # 分片集: [].cluster::{{role}}::info
            # 副本集：[].info
            sharded_cutoff_infos = [
                info
                for info in cutoff_infos
                if id__cluster[info["cluster_id"]].cluster_type == ClusterType.MongoShardedCluster
            ]
            replicaset_cutoff_infos = [
                info["mongodb"]
                for info in cutoff_infos
                if id__cluster[info["cluster_id"]].cluster_type == ClusterType.MongoReplicaSet
            ]
            replicaset_cutoff_infos = list(itertools.chain(*replicaset_cutoff_infos))

            next_flow.details["ticket_data"]["infos"] = {
                ClusterType.MongoShardedCluster.value: sharded_cutoff_infos,
                ClusterType.MongoReplicaSet.value: replicaset_cutoff_infos,
            }


@builders.BuilderFactory.register(TicketType.MONGODB_CUTOFF, is_apply=True)
class MongoDBCutoffApplyFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoDBCutoffDetailSerializer
    inner_flow_builder = MongoDBCutoffFlowParamBuilder
    inner_flow_name = _("MongoDB 整机替换执行")
    resource_batch_apply_builder = MongoDBCutoffResourceParamBuilder

    def patch_ticket_resources(self):
        mongo_roles = [MachineType.MONGOS, MachineType.MONOG_CONFIG, MachineType.MONGODB]
        cluster_ids = [info["cluster_id"] for info in self.ticket.details["infos"]]
        id__cluster = {cluster.id: cluster for cluster in Cluster.objects.filter(id__in=cluster_ids)}
        for info in self.ticket.details["infos"]:
            city = id__cluster[info["cluster_id"]].region
            # 打包资源信息：按照role_ip这样的命名格式构造每一个资源申请信息组，每组的城市同集群，数量为1
            resource_spec = {}
            for role in mongo_roles:
                for host in info.get(role, []):
                    group_name = f"{role}_{host['ip']}"
                    resource_spec[group_name] = {
                        "spec_id": host["spec_id"],
                        "count": 1,
                        "location_spec": {"city": city, "sub_zone_ids": []},
                    }
            info["resource_spec"] = resource_spec

    def patch_ticket_specs(self):
        spec_ids = get_target_items_from_details(self.ticket.details["infos"], match_keys=["spec_id"])
        specs = {spec.spec_id: spec.get_spec_info() for spec in Spec.objects.filter(spec_id__in=spec_ids)}
        self.ticket.details["specs"] = specs

    def patch_ticket_detail(self):
        self.patch_ticket_resources()
        self.patch_ticket_specs()
        super().patch_ticket_detail()
