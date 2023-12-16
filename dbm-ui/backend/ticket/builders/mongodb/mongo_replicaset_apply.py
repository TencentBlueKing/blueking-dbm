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

from backend.configuration.constants import AffinityEnum
from backend.db_meta.enums import ClusterType
from backend.db_services.dbbase.constants import IpSource
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.ticket import builders
from backend.ticket.builders.mongodb.base import BaseMongoDBOperateResourceParamBuilder, BaseMongoDBTicketFlowBuilder
from backend.ticket.constants import TicketType


class MongoReplicaSetApplyDetailSerializer(serializers.Serializer):
    class ReplicaSet(serializers.Serializer):
        set_id = serializers.CharField(help_text=_("复制集群ID（英文数字及下划线）"))
        name = serializers.CharField(help_text=_("集群别名"))
        domain = serializers.CharField(help_text=_("集群域名"))

    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    db_app_abbr = serializers.CharField(help_text=_("业务英文缩写"))
    city_code = serializers.CharField(
        help_text=_("城市代码"), required=False, allow_blank=True, allow_null=True, default=""
    )
    disaster_tolerance_level = serializers.ChoiceField(
        help_text=_("容灾级别"), choices=AffinityEnum.get_choices(), required=False, default=AffinityEnum.NONE.value
    )

    cluster_type = serializers.CharField(help_text=_("集群类型"))
    db_version = serializers.CharField(help_text=_("版本号"))
    start_port = serializers.IntegerField(help_text=_("起始端口"))
    replica_count = serializers.IntegerField(help_text=_("副本集数量"))
    node_count = serializers.IntegerField(help_text=_("副本集节点数量"))
    node_replica_count = serializers.IntegerField(help_text=_("单机副本集数量"))
    replica_sets = serializers.ListSerializer(help_text=_("副本集列表"), child=ReplicaSet(), allow_empty=False)
    spec_id = serializers.IntegerField(help_text=_("规格ID"))
    oplog_percent = serializers.IntegerField(help_text=_("oplog容量占比"))

    ip_source = serializers.ChoiceField(help_text=_("主机来源"), choices=IpSource.get_choices())

    # display fields
    bk_cloud_name = serializers.SerializerMethodField(help_text=_("云区域"), read_only=True)
    city_name = serializers.SerializerMethodField(help_text=_("城市名"), read_only=True)
    resource_spec = serializers.SerializerMethodField(help_text=_("集群规格"), read_only=True)

    def get_bk_cloud_name(self, obj):
        clouds = ResourceQueryHelper.search_cc_cloud(get_cache=True)
        return clouds[str(obj["bk_cloud_id"])]["bk_cloud_name"]

    def get_city_name(self, obj):
        city_code = obj["city_code"]
        return self.context["ticket_ctx"].city_map.get(city_code, city_code)

    def get_resource_spec(self, obj):
        # 任取一个replica_set来作为单据的规格描述
        return obj["infos"][0]["resource_spec"]

    def validate(self, attrs):
        """TODO: validate"""
        return attrs


class MongoReplicaSetApplyFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.multi_replicaset_create

    def format_ticket_data(self):
        self.ticket_data["bk_app_abbr"] = self.ticket_data["db_app_abbr"]


class MongoReplicaSetResourceParamBuilder(BaseMongoDBOperateResourceParamBuilder):
    def format(self):
        pass

    def post_callback(self):
        next_flow = self.ticket.next_flow()
        for info in next_flow.details["ticket_data"]["infos"]:
            info["resource_spec"]["spec_config"] = info["resource_spec"].pop("mongo_machine_set")
        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(
    TicketType.MONGODB_REPLICASET_APPLY, is_apply=True, cluster_type=ClusterType.MongoReplicaSet
)
class MongoReplicaSetApplyFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoReplicaSetApplyDetailSerializer
    inner_flow_builder = MongoReplicaSetApplyFlowParamBuilder
    inner_flow_name = _("MongoDB 副本集集群部署执行")
    resource_batch_apply_builder = MongoReplicaSetResourceParamBuilder

    @classmethod
    def get_replicaset_resource_spec(cls, ticket_data):
        """获取副本集部署的资源池规格信息"""
        # infos的组数 = 副本集数量 / 单机部署副本集数
        groups = int(ticket_data["replica_count"] / ticket_data["node_replica_count"])
        infos = [
            {
                "bk_cloud_id": ticket_data["bk_cloud_id"],
                "resource_spec": {
                    "mongo_machine_set": {
                        "affinity": ticket_data["disaster_tolerance_level"],
                        "location_spec": {"city": ticket_data["city_code"], "sub_zone_ids": []},
                        # 副本集的亲和性要求至少跨两个机房
                        "group_count": 2,
                        "count": ticket_data["node_count"],
                        "spec_id": ticket_data["spec_id"],
                    }
                },
            }
            for _ in range(groups)
        ]
        return infos

    def patch_ticket_detail(self):
        # 补充资源池的申请参数
        self.ticket.details["infos"] = self.get_replicaset_resource_spec(self.ticket.details)
        self.ticket.save(update_fields=["details"])
