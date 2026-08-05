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

from backend.db_meta.enums import MachineType
from backend.db_meta.models import AppCache, Cluster, Machine, ProxyInstance, StorageInstance
from backend.db_services.dbbase.constants import IpSource
from backend.db_services.mongodb.resources.query import MongoDBListRetrieveResource
from backend.db_services.mongodb.toolbox.handlers import ToolboxHandler
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.common.base import get_mongodb_cluster_tolerance
from backend.ticket.builders.mongodb.base import (
    BaseMongoDBOperateDetailSerializer,
    BaseMongoDBOperateResourceParamBuilder,
    BaseMongoDBTicketFlowBuilder,
)
from backend.ticket.builders.mongodb.inst_desc import build_mongo_inst_desc
from backend.ticket.constants import TicketType
from backend.utils.basic import get_target_items_from_details


class MongoDBShardCutoffDetailSerializer(BaseMongoDBOperateDetailSerializer):
    class ACutoffDetailSerializer(serializers.Serializer):
        class IpSpecSLZ(serializers.Serializer):
            ip = serializers.CharField(help_text=_("替换主机IP"))
            bk_cloud_id = serializers.IntegerField(help_text=_("主机所在云区域"))
            bk_host_id = serializers.IntegerField(help_text=_("替换的主机ID"))
            down = serializers.BooleanField(help_text=_("机器是否关机"), default=False, required=False)
            spec = serializers.JSONField(help_text=_("旧节点规格信息"), required=False)

        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        switch_role = serializers.CharField(help_text=_("替换角色"))
        resource_spec = serializers.JSONField(help_text=_("资源规格信息"))
        mongos = serializers.ListSerializer(child=IpSpecSLZ(help_text=_("替换mongos的信息")), required=False)
        mongodb = serializers.ListSerializer(child=IpSpecSLZ(help_text=_("替换mongodb的信息")), required=False)
        mongo_config = serializers.ListSerializer(child=IpSpecSLZ(help_text=_("替换mongo_config的信息")), required=False)
        old_nodes = serializers.JSONField(help_text=_("旧节点信息集合"), required=False)

    ip_source = serializers.ChoiceField(
        help_text=_("主机来源"), choices=IpSource.get_choices(), default=IpSource.RESOURCE_POOL
    )
    cluster_type = serializers.CharField(help_text=_("集群版本"))
    infos = serializers.ListSerializer(help_text=_("整机替换信息"), child=ACutoffDetailSerializer())

    def validate(self, attrs):
        attrs = super().validate(attrs)
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


class MongoDBShardCutoffFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.machine_replace

    def format_ticket_data(self):
        bk_biz_id = self.ticket_data["bk_biz_id"]
        self.ticket_data["bk_app_abbr"] = AppCache.objects.get(bk_biz_id=bk_biz_id).db_app_abbr


class MongoDBShardCutoffResourceParamBuilder(BaseMongoDBOperateResourceParamBuilder):
    def format(self):
        # 补充城市和亲和性
        infos = self.ticket_data["infos"]
        for info in infos:
            cluster = Cluster.objects.get(id=info["cluster_id"])
            off_host_ids = [host["bk_host_id"] for host in info["old_nodes"][info["switch_role"]]]
            common_filters = Q(machine__machine_type=info["switch_role"], cluster__in=[info["cluster_id"]]) & ~Q(
                machine__bk_host_id__in=off_host_ids
            )
            tolerance = get_mongodb_cluster_tolerance(cluster.disaster_tolerance_level, info["switch_role"])

            if info["switch_role"] == MachineType.MONGODB.value:
                host = info["mongodb"][0]
                storage = StorageInstance.objects.filter(
                    cluster=cluster, machine__bk_host_id=host["bk_host_id"]
                ).first()
                instances = ToolboxHandler(self.ticket.bk_biz_id).get_shard_others_instance(storage, cluster)

            elif info["switch_role"] == MachineType.MONGOS.value:
                instances = list(ProxyInstance.objects.select_related("machine").filter(common_filters))
            else:
                instances = list(StorageInstance.objects.select_related("machine").filter(common_filters))

            exclusive_hosts = [ins.machine for ins in instances]
            self.patch_common_affinity(
                info,
                role=f"new_{info['switch_role']}",
                cluster=cluster,
                exclusive_hosts=exclusive_hosts,
                tolerance=tolerance,
            )

        super().format()

    @staticmethod
    def _get_mongo_inst_desc(instance, storage_id__shard):
        return build_mongo_inst_desc(instance, storage_id__shard)

    def _fill_instance_infos(self, role, machine, storage_id__shard):
        if role == MachineType.MONGOS:
            instances = machine.proxyinstance_set.select_related("machine").prefetch_related("cluster").all()
        else:
            instances = machine.storageinstance_set.select_related("machine").prefetch_related("cluster").all()
        instance_infos = [self._get_mongo_inst_desc(inst, storage_id__shard) for inst in instances]
        return instance_infos

    def post_callback(self):
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

            # 拆包资源信息：在每个替换信息中填充规格，目标机器和实例信息
            for info in cutoff_infos:
                role = f"new_{info['switch_role']}"
                for host in info.get(info["switch_role"], []):
                    index_ = info[info["switch_role"]].index(host)
                    host["target"] = info[role][index_]
                    # 填充实例信息
                    machine = ip__machine[host["ip"]]
                    host["instances"] = self._fill_instance_infos(info["switch_role"], machine, storage_id__shard)


@builders.BuilderFactory.register(
    TicketType.MONGODB_SHARD_CUTOFF, is_apply=True, is_recycle=True, iam=ActionEnum.MONGODB_MANAGE
)
class MongoDBShardCutoffApplyFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoDBShardCutoffDetailSerializer
    inner_flow_builder = MongoDBShardCutoffFlowParamBuilder
    inner_flow_name = _("MongoDB 分片集群整机替换执行")
    resource_batch_apply_builder = MongoDBShardCutoffResourceParamBuilder
    need_patch_recycle_host_details = True
