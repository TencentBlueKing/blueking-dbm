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
from backend.ticket.builders.common.base import CommonValidate
from backend.ticket.builders.mongodb.base import BaseMongoDBTicketFlowBuilder
from backend.ticket.constants import TicketType


class MongoReplicaSetApplyDetailSerializer(serializers.Serializer):
    class ReplicaSet(serializers.Serializer):
        set_id = serializers.CharField(help_text=_("集群ID（英文数字及下划线）"))
        name = serializers.CharField(help_text=_("集群别名"))
        domain = serializers.IntegerField(help_text=_("集群域名"))

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

    def get_bk_cloud_name(self, obj):
        clouds = ResourceQueryHelper.search_cc_cloud(get_cache=True)
        return clouds[str(obj["bk_cloud_id"])]["bk_cloud_name"]

    def get_city_name(self, obj):
        city_code = obj["city_code"]
        return self.context["ticket_ctx"].city_map.get(city_code, city_code)

    def validate(self, attrs):
        # 校验集群名是否重复
        CommonValidate.validate_duplicate_cluster_name(
            self.context["bk_biz_id"], self.context["ticket_type"], attrs["cluster_name"]
        )
        return attrs


class MongoReplicaSetApplyFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.mongodb_cluster_apply_scene

    def format_ticket_data(self):
        print(self.ticket_data)


class MongoReplicaSetApplyResourceParamBuilder(builders.ResourceApplyParamBuilder):
    def format(self):
        node_count = self.ticket_data["node_count"]
        node_replica_count = self.ticket_data["node_replica_count"]
        replica_count = self.ticket_data["replica_count"]
        group_count = int(replica_count / node_replica_count)

        self.ticket_data["infos"] = [
            {
                "resource_spec": {
                    "mongo_machine_set": {
                        "affinity": True,
                        "location_spec": self.ticket_data["city_code"],
                        "group_count": group_count,
                        "count": node_count,
                        "spec_id": self.ticket_data["spec_id"],
                        "set_id": replica_set["set_id"]
                    }
                }
            }
            for replica_set in self.ticket_data["replica_sets"]
        ]

    def post_callback(self):
        """组装infos"""
        next_flow = self.ticket.next_flow()
        print(next_flow.details["ticket_data"])


@builders.BuilderFactory.register(TicketType.MONGODB_REPLICASET_APPLY, is_apply=True,
                                  cluster_type=ClusterType.MongoReplicaSet)
class MongoReplicaSetApplyFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoReplicaSetApplyDetailSerializer
    inner_flow_builder = MongoReplicaSetApplyFlowParamBuilder
    inner_flow_name = _("MongoDB 副本集集群部署执行")
    resource_batch_apply_builder = MongoReplicaSetApplyResourceParamBuilder

    def patch_ticket_detail(self):
        print(self.ticket.details)

