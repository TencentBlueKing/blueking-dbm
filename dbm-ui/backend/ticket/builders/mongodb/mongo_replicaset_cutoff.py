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

from backend.db_meta.enums import MachineType
from backend.db_meta.models import AppCache, Machine
from backend.db_services.mongodb.resources.query import MongoDBListRetrieveResource
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.common.base import get_mongodb_cluster_tolerance
from backend.ticket.builders.mongodb.base import BaseMongoDBOperateResourceParamBuilder, BaseMongoDBTicketFlowBuilder
from backend.ticket.builders.mongodb.inst_desc import build_mongo_inst_desc
from backend.ticket.builders.mongodb.mongo_shard_cutoff import MongoDBShardCutoffDetailSerializer
from backend.ticket.constants import TicketType
from backend.utils.basic import get_target_items_from_details


class MongoDBReplicasetCutoffDetailSerializer(MongoDBShardCutoffDetailSerializer):
    pass


class MongoDBReplicasetCutoffFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.machine_replace

    def format_ticket_data(self):
        bk_biz_id = self.ticket_data["bk_biz_id"]
        self.ticket_data["bk_app_abbr"] = AppCache.objects.get(bk_biz_id=bk_biz_id).db_app_abbr


class MongoDBReplicasetCutoffResourceParamBuilder(BaseMongoDBOperateResourceParamBuilder):
    def format(self):
        # 补充城市和亲和性
        self.patch_info_common_affinity(
            role="new_mongodb",
            remain_machine_type=MachineType.MONGODB,
            replace_key="mongodb",
            tolerance=get_mongodb_cluster_tolerance,
            tolerance_type="mongodb",
        )

        super().format()

    @staticmethod
    def _get_mongo_inst_desc(instance, storage_id__shard):
        return build_mongo_inst_desc(instance, storage_id__shard)

    def _fill_instance_infos(self, machine, storage_id__shard):
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
                for host in info.get("mongodb", []):
                    host["target"] = info.pop("new_mongodb")[0]
                    # 填充实例信息
                    machine = ip__machine[host["ip"]]
                    host["instances"] = self._fill_instance_infos(machine, storage_id__shard)


@builders.BuilderFactory.register(
    TicketType.MONGODB_REPLICASET_CUTOFF, is_apply=True, is_recycle=True, iam=ActionEnum.MONGODB_MANAGE
)
class MongoDBReplicasetCutoffApplyFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoDBReplicasetCutoffDetailSerializer
    inner_flow_builder = MongoDBReplicasetCutoffFlowParamBuilder
    inner_flow_name = _("MongoDB 副本集整机替换执行")
    resource_batch_apply_builder = MongoDBReplicasetCutoffResourceParamBuilder
    need_patch_recycle_host_details = True
