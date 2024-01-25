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
from contextlib import contextmanager
from typing import Dict, List

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.configuration.constants import AffinityEnum, DBType
from backend.db_meta.models import Cluster, Machine, StorageInstance
from backend.flow.utils.mongodb.db_table_filter import MongoDbTableFilter
from backend.ticket import builders
from backend.ticket.builders import TicketFlowBuilder
from backend.ticket.builders.common.base import (
    BaseOperateResourceParamBuilder,
    MongoDBTicketFlowBuilderPatchMixin,
    SkipToRepresentationMixin,
)

MONGODB_SHARD_GROUP_COUNT = 3
MONGODB_JS_FILE_PREFIX = "/mongodb/script_result"


class DBTableSerializer(serializers.Serializer):
    db_patterns = serializers.ListField(help_text=_("匹配DB列表"), child=serializers.CharField())
    ignore_dbs = serializers.ListField(help_text=_("忽略DB列表"), child=serializers.CharField())
    table_patterns = serializers.ListField(help_text=_("匹配Table列表"), child=serializers.CharField())
    ignore_tables = serializers.ListField(help_text=_("忽略Table列表"), child=serializers.CharField())

    def validate(self, attrs):
        MongoDbTableFilter(attrs["db_patterns"], attrs["table_patterns"], attrs["ignore_dbs"], attrs["ignore_tables"])
        return attrs


class BaseMongoDBTicketFlowBuilder(MongoDBTicketFlowBuilderPatchMixin, TicketFlowBuilder):
    group = DBType.MongoDB.value


class BaseMongoDBOperateDetailSerializer(SkipToRepresentationMixin, serializers.Serializer):
    @classmethod
    def validate_shrink_machine_affinity(cls, cluster: Cluster, machines: List[Machine], spec_id: int, count: int):
        """在缩容指定规格的机器后，剩余的机器仍能满足亲和性要求"""
        if cluster.disaster_tolerance_level != AffinityEnum.CROS_SUBZONE:
            return

        # 如果其他规格的满足容灾亲和性，则合法
        other_machine_subzone_ids = {machine.bk_sub_zone_id for machine in machines if machine.spec_id != spec_id}
        if len(other_machine_subzone_ids) > 1:
            return

        # 如果缩容指定规格的机器不是全部裁掉，并且与其他机器规格有差集，则合法
        shrink_machine_subzone_ids = [machine.bk_sub_zone_id for machine in machines if machine.spec_id == spec_id]
        machine_count, shrink_machine_subzone_ids = len(shrink_machine_subzone_ids), set(shrink_machine_subzone_ids)
        if machine_count != count and (shrink_machine_subzone_ids - other_machine_subzone_ids):
            return

        raise serializers.ValidationError(_("缩容规格: {} 的台数: {} 后不满足容灾要求!").format(spec_id, count))

    @classmethod
    def validate_machine_in_different_shard(cls, machines: List[Machine]):
        """校验这一批机器对应的shard节点在不同的分片"""
        storages = StorageInstance.objects.prefetch_related(
            "nosqlstoragesetdtl_set", "as_ejector", "as_receiver", "cluster", "machine"
        ).filter(machine__in=machines)
        shard_set = set()
        for storage in storages:
            primary = (storage.as_ejector.all() or storage.as_receiver.all()).first().ejector
            shard = primary.nosqlstoragesetdtl_set.first().shard
            unique_shard_name = f"{primary.cluster.id}_{primary.machine.machine_type}_{shard}"
            if unique_shard_name in shard_set:
                raise serializers.ValidationError(
                    _("集群:{}, 请保证机器{}不能再同一个分片{}中").format(primary.cluster.name, primary.machine.machine_type, shard)
                )
            shard_set.add(unique_shard_name)

    def validate(self, attrs):
        return attrs


class BaseMongoOperateFlowParamBuilder(builders.FlowParamBuilder):
    @classmethod
    def scatter_cluster_id_info(cls, infos):
        """打散集群ID，拆成一个个的item"""
        scattered_infos: List[Dict] = []
        for info in infos:
            cluster_ids = info.pop("cluster_ids")
            scattered_infos.extend([{**info, "cluster_id": cluster_id} for cluster_id in cluster_ids])
        return scattered_infos

    @classmethod
    def add_cluster_type_info(cls, infos):
        """给每个info加上集群类型"""
        cluster_ids = [info["cluster_id"] for info in infos]
        id__cluster = {cluster.id: cluster for cluster in Cluster.objects.filter(id__in=cluster_ids)}
        for info in infos:
            info["cluster_type"] = id__cluster[info["cluster_id"]].cluster_type
        return infos


class BaseMongoDBOperateResourceParamBuilder(BaseOperateResourceParamBuilder):
    @classmethod
    def format_mongo_resource_spec(cls, resource_spec, shard_machine_group, shard_count=None):
        mongodb_resource_spec = resource_spec.pop("mongodb")
        # mongodb的一组默认为三台，如果集群进行shard节点的扩缩容，则优先以集群的为准
        mongodb_resource_spec["count"] = shard_count or MONGODB_SHARD_GROUP_COUNT
        for group in range(shard_machine_group):
            resource_spec[f"mongodb_nodes_{group}"] = mongodb_resource_spec

    @classmethod
    def format_mongo_node_infos(cls, node_infos):
        # 重新组合mongodb的资源信息, 将mongodb_1, mongodb_2聚合为mongodb: [[...], [...], [...]]
        node_infos["mongodb"] = []
        mongodb_node_infos = {role: node_info for role, node_info in node_infos.items() if "mongodb_nodes_" in role}
        for group, node_info in mongodb_node_infos.items():
            node_infos.pop(group)
            node_infos["mongodb"].append(node_info)
        return node_infos

    @classmethod
    def format_machine_specs(cls, resource_spec):
        # 格式化资源池申请信息
        machine_specs = {}
        for role, info in resource_spec.items():
            spec_info = {"spec_id": info["id"], "spec_config": info}
            machine_specs[role] = spec_info
        return machine_specs

    @contextmanager
    def next_flow_manager(self):
        # 回调更新next flow的上下文管理器
        next_flow = self.ticket.next_flow()
        yield next_flow
        next_flow.save(update_fields=["details"])

    def format(self):
        super().format()

    def post_callback(self):
        pass
