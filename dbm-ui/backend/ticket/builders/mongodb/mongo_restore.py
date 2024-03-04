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
import datetime
from typing import Any, Dict, List

from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.configuration.constants import AffinityEnum
from backend.db_meta.enums import ClusterType, MachineType
from backend.db_meta.enums.comm import SystemTagEnum, TagType
from backend.db_meta.models import AppCache, Cluster, Tag
from backend.db_services.dbbase.constants import IpSource
from backend.flow.consts import MongoDBClusterDefaultPort
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.ticket import builders
from backend.ticket.builders.common.field import DBTimezoneField
from backend.ticket.builders.mongodb.base import (
    BaseMongoDBOperateDetailSerializer,
    BaseMongoDBTicketFlowBuilder,
    DBTableSerializer,
)
from backend.ticket.builders.mongodb.mongo_replicaset_apply import (
    MongoReplicaSetApplyFlowBuilder,
    MongoReplicaSetResourceParamBuilder,
)
from backend.ticket.builders.mongodb.mongo_shard_apply import MongoShardedClusterResourceParamBuilder
from backend.ticket.constants import FlowRetryType, FlowType, TicketType
from backend.ticket.models import ClusterOperateRecord, Flow
from backend.utils.time import date2str


class MongoDBRestoreDetailSerializer(BaseMongoDBOperateDetailSerializer):
    cluster_ids = serializers.ListField(help_text=_("集群列表"), child=serializers.IntegerField())
    cluster_type = serializers.ChoiceField(help_text=_("集群类型"), choices=ClusterType.get_choices(), required=False)
    ns_filter = DBTableSerializer(help_text=_("库表选择器"), required=False)
    rollback_time = DBTimezoneField(help_text=_("回档时间"), required=False)
    backupinfo = serializers.JSONField(help_text=_("指定备份记录[集群ID: 记录]"), required=False)
    city_code = serializers.CharField(help_text=_("部署城市"), required=False, default="default")
    instance_per_host = serializers.IntegerField(help_text=_("每台主机部署的节点数"))
    resource_spec = serializers.JSONField(help_text=_("资源池规格"))

    def validate(self, attrs):
        clusters = Cluster.objects.filter(id__in=attrs["cluster_ids"])
        cluster_type = clusters.first().cluster_type
        attrs["cluster_type"] = cluster_type

        # 分片集群暂不支持批量回档
        if cluster_type == ClusterType.MongoShardedCluster and clusters.count() > 1:
            raise serializers.ValidationError(_("分片集群暂时不支持批量回档"))

        # 副本集集群回档的版本和城市需要一致
        if cluster_type == ClusterType.MongoReplicaSet:
            self.validate_cluster_same_attr(clusters, attrs=["region", "major_version"])

        return attrs


class MongoDBRestoreResourceParamBuilder(MongoReplicaSetResourceParamBuilder, MongoShardedClusterResourceParamBuilder):
    def format(self):
        self.ticket_data = self.ticket_data["apply_details"]
        if self.ticket_data["cluster_type"] == ClusterType.MongoShardedCluster:
            resource_spec = self.ticket_data["resource_spec"]
            self.format_mongo_resource_spec(resource_spec, self.ticket_data["shard_machine_group"], shard_count=1)

    def post_callback(self):
        if self.ticket_data["cluster_type"] == ClusterType.MongoShardedCluster:
            MongoShardedClusterResourceParamBuilder.post_callback(self)
        else:
            MongoReplicaSetResourceParamBuilder.post_callback(self)


class MongoDBRestoreClusterApplyFlowParamBuilder(builders.FlowParamBuilder):
    controller_shard = MongoDBController.cluster_create
    controller_replicaset = MongoDBController.multi_replicaset_create

    def build_controller_info(self) -> dict:
        if self.ticket_data["cluster_type"] == ClusterType.MongoShardedCluster:
            self.controller = self.controller_shard
        else:
            self.controller = self.controller_replicaset
        return super().build_controller_info()

    def format_ticket_data(self):
        pass


class MongoDBRestoreFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.fake_scene

    def format_ticket_data(self):
        pass

    def pre_callback(self):
        rollback_flow = self.ticket.current_flow()
        ticket_data = rollback_flow.details["ticket_data"]

        # 查询部署的临时集群
        bk_biz_id, cluster_type = ticket_data["bk_biz_id"], ticket_data["cluster_type"]
        if cluster_type == ClusterType.MongoShardedCluster:
            cluster_names = [self.ticket_data["apply_details"]["cluster_name"]]
        else:
            cluster_names = [s["name"] for s in self.ticket_data["apply_details"]["replica_sets"]]

        tmp_cluster_filters = Q()
        for cluster_name in cluster_names:
            tmp_cluster_filters |= Q(bk_biz_id=bk_biz_id, cluster_type=cluster_type, cluster_name=cluster_name)
        tmp_clusters = Cluster.objects.filter(tmp_cluster_filters)

        # 为临时集群添加临时标志和记录
        temporary_tag, _ = Tag.objects.get_or_create(
            bk_biz_id=bk_biz_id, name=SystemTagEnum.TEMPORARY.value, type=TagType.SYSTEM.value
        )
        source_cluster_name__cluster: Dict[str, Cluster] = {}
        cluster_records: List[ClusterOperateRecord] = []
        for cluster in tmp_clusters:
            cluster.tag_set.add(temporary_tag)
            source_cluster_name__cluster[cluster.name.rsplit("-", 2)[0]] = cluster
            cluster_records.append(ClusterOperateRecord(cluster_id=cluster.id, ticket=self.ticket, flow=rollback_flow))

        ClusterOperateRecord.objects.bulk_create(cluster_records)

        # 为定点构造的flow填充临时集群的信息
        id__cluster = {cluster.id: cluster for cluster in Cluster.objects.filter(id__in=ticket_data["cluster_ids"])}
        infos: List[Dict[str, Any]] = []
        for cluster_id in ticket_data["cluster_ids"]:
            restore_info = {
                "cluster_id": cluster_id,
                "temporary_cluster_id": source_cluster_name__cluster[id__cluster[cluster_id].name].id,
                "ns_filter": self.ticket_data["ns_filter"],
                "rollback_time": self.ticket_data.get("rollback_time", None),
                "backupinfo": self.ticket_data.get("backupinfo", {}).get(cluster_id, None),
            }
            infos.append(restore_info)

        ticket_data.update(infos=infos)
        rollback_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.MONGODB_RESTORE)
class MongoDBRestoreApplyFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoDBRestoreDetailSerializer

    @classmethod
    def get_common_apply_details(cls, cluster, ticket_data):
        """回去回档集群的通用部署参数"""
        db_app_abbr = AppCache.get_app_attr(cluster.bk_biz_id)
        apply_details = {}
        apply_details.update(
            bk_cloud_id=cluster.bk_cloud_id,
            cluster_type=cluster.cluster_type,
            db_app_abbr=db_app_abbr,
            city_code=ticket_data["city_code"],
            disaster_tolerance_level=AffinityEnum.NONE.value,
            db_version=cluster.major_version,
            # start_port默认为27001, oplog_percent=5
            start_port=MongoDBClusterDefaultPort.SHARD_START_PORT.value,
            oplog_percent=5,
            ip_source=IpSource.RESOURCE_POOL,
        )
        return apply_details

    @classmethod
    def get_replicaset_apply_details(cls, ticket_id, ticket_data):
        """补充副本集回档的部署参数"""
        # 任取一个集群来补充信息(所有副本集回档的集群属性一致)
        id__cluster = {cluster.id: cluster for cluster in Cluster.objects.filter(id__in=ticket_data["cluster_ids"])}
        cluster = id__cluster[ticket_data["cluster_ids"][0]]
        db_app_abbr = AppCache.get_app_attr(cluster.bk_biz_id)

        # 生成replica_sets
        replica_sets = []
        for cluster_id in ticket_data["cluster_ids"]:
            cluster_name = id__cluster[cluster_id].name
            set_id = name = f"{cluster_name}-tmp{date2str(datetime.date.today(), '%Y%m%d')}-{ticket_id}"
            domain = f"m1.{set_id}.{db_app_abbr}.db"
            replica_sets.append({"set_id": set_id, "name": name, "domain": domain})

        # 生成部署信息
        apply_details = cls.get_common_apply_details(cluster, ticket_data)
        apply_details.update(
            replica_sets=replica_sets,
            node_replica_count=ticket_data["instance_per_host"],
            replica_count=len(ticket_data["cluster_ids"]),
            # 每个副本集只有一个节点
            node_count=1,
            spec_id=ticket_data["resource_spec"]["mongodb"],
        )
        return apply_details

    @classmethod
    def get_shard_apply_details(cls, ticket_id, ticket_data, apply_details=None):
        """补充分片集回档的部署参数"""
        # 分片集暂时只支持单个回档，因此cluster_ids只有一个元素
        cluster = Cluster.objects.get(id=ticket_data["cluster_ids"][0])
        shard_num = cluster.nosqlstoragesetdtl_set.filter(instance__machine__machine_type=MachineType.MONGODB).count()
        cluster_name = cluster_alias = f"{cluster.name}-tmp{date2str(datetime.date.today(), '%Y%m%d')}-{ticket_id}"

        # 生成部署信息
        apply_details = cls.get_common_apply_details(cluster, ticket_data)
        apply_details.update(
            cluster_name=cluster_name,
            cluster_alias=cluster_alias,
            # 分片回档集群的shard节点数固定为1，因此机器组数等于机器数量
            shard_machine_group=int(shard_num / ticket_data["instance_per_host"]),
            shard_num=shard_num,
            resource_spec=ticket_data["resource_spec"],
        )
        return apply_details

    def patch_ticket_detail(self):
        """补充单据信息，在这里主要是补充回档集群的部署信息"""
        if self.ticket.details["cluster_type"] == ClusterType.MongoReplicaSet:
            apply_details = self.get_replicaset_apply_details(self.ticket.id, self.ticket.details)
            apply_details["infos"] = MongoReplicaSetApplyFlowBuilder.get_replicaset_resource_spec(apply_details)
        else:
            apply_details = self.get_shard_apply_details(self.ticket.id, self.ticket.details)

        self.ticket.update_details(apply_details=apply_details)
        super().patch_ticket_detail()

    def custom_ticket_flows(self):
        cluster_type = self.ticket.details["cluster_type"]
        flow_infix = "_" if cluster_type == ClusterType.MongoShardedCluster else "_BATCH_"
        resource_apply_flow_type = getattr(FlowType, f"RESOURCE{flow_infix}APPLY")
        resource_deliver_flow_type = getattr(FlowType, f"RESOURCE{flow_infix}DELIVERY")

        flows = [
            Flow(
                ticket=self.ticket,
                flow_type=resource_apply_flow_type,
                details=MongoDBRestoreResourceParamBuilder(self.ticket).get_params(),
                flow_alias=_("资源申请"),
            ),
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.INNER_FLOW.value,
                details=MongoDBRestoreClusterApplyFlowParamBuilder(self.ticket).get_params(),
                flow_alias=_("[{}]回档临时集群部署".format(ClusterType.get_choice_label(cluster_type))).format(),
                retry_type=FlowRetryType.MANUAL_RETRY.value,
            ),
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.INNER_FLOW.value,
                details=MongoDBRestoreFlowParamBuilder(self.ticket).get_params(),
                flow_alias=_("MongoDB 回档执行"),
                retry_type=FlowRetryType.MANUAL_RETRY.value,
            ),
            Flow(
                ticket=self.ticket,
                flow_type=resource_deliver_flow_type,
                flow_alias=_("资源确认"),
            ),
        ]
        return flows

    @classmethod
    def describe_ticket_flows(cls, flow_config_map):
        flow_desc = cls._add_itsm_pause_describe(flow_desc=[], flow_config_map=flow_config_map)
        flow_desc.extend([_("资源申请"), _("回档临时集群部署"), _("MongoDB 回档执行"), _("资源确认")])
        return flow_desc
