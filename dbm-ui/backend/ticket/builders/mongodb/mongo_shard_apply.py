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
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.configuration.constants import AffinityEnum
from backend.db_meta.enums import ClusterType
from backend.db_services.dbbase.constants import IpSource
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.common.base import (
    TicketBaseValidateSerializerMixin,
    get_mongodb_cluster_tolerance,
    get_ticket_zone_list,
)
from backend.ticket.builders.mongodb.base import (
    BaseMongoDBOperateResourceParamBuilder,
    BaseMongoShardedTicketFlowBuilder,
)
from backend.ticket.constants import TicketType

# NOTE: 本单据的 detail 字段 / validate 规则被 MCP mongodb-bill 镜像使用。
# 若变更 DetailSerializer、校验逻辑或 Ticket.create_ticket 所需 details 结构，
# 请同步修改：
#   - backend/dbm_aiagent/mcp_tools/mongodb/serializers/mongodb_bill.py
#     (SubmitBillMongoShardApplyInputSerializer)
#   - backend/dbm_aiagent/mcp_tools/mongodb/impl/mongodb_bill.py
#     (submit_mongodb_shard_apply_bill)
#   - backend/dbm_aiagent/mcp_tools/mongodb/views/mongodb_bill_mcp.py
#     (submit_bill_shard_apply)


class MongoShardedClusterApplyDetailSerializer(TicketBaseValidateSerializerMixin, serializers.Serializer):
    """分片集群部署单据 details。改动时须同步 mongodb-bill MCP（见文件头 NOTE）。"""

    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    db_app_abbr = serializers.CharField(help_text=_("业务英文缩写"))
    city_code = serializers.CharField(
        help_text=_("城市代码"), required=False, allow_blank=True, allow_null=True, default=""
    )
    disaster_tolerance_level = serializers.ChoiceField(
        help_text=_("容灾级别"), choices=AffinityEnum.get_choices(), required=False, default=AffinityEnum.NONE.value
    )

    cluster_type = serializers.CharField(help_text=_("集群类型"))
    cluster_name = serializers.CharField(help_text=_("集群ID"))
    cluster_alias = serializers.CharField(help_text=_("集群别名"), allow_blank=True, allow_null=True)
    db_version = serializers.CharField(help_text=_("版本号"))
    start_port = serializers.IntegerField(help_text=_("起始端口"))
    oplog_percent = serializers.IntegerField(help_text=_("oplog容量占比"))

    ip_source = serializers.ChoiceField(help_text=_("主机来源"), choices=IpSource.get_choices())
    resource_spec = serializers.JSONField(help_text=_("资源申请规格"))

    shard_machine_group = serializers.IntegerField(help_text=_("机器组数"))
    shard_num = serializers.IntegerField(help_text=_("集群分片数"))
    nodes = serializers.JSONField(help_text=_("部署节点"), required=False)

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
        attrs = super().validate(attrs)
        shard_num = attrs["shard_num"]
        shard_machine_group = attrs["shard_machine_group"]
        if shard_num <= 0:
            raise serializers.ValidationError(_("集群分片数(shard_num)必须大于 0"))
        if shard_machine_group <= 0:
            raise serializers.ValidationError(_("机器组数(shard_machine_group)必须大于 0"))
        if shard_num % shard_machine_group != 0:
            raise serializers.ValidationError(
                _(
                    "集群分片数(shard_num={shard_num})必须能被机器组数"
                    "(shard_machine_group={shard_machine_group})整除，"
                    "否则单机分片数计算错误，部署会失败"
                ).format(shard_num=shard_num, shard_machine_group=shard_machine_group)
            )

        resource_spec = attrs.get("resource_spec") or {}
        for role in ("mongodb", "mongo_config", "mongos"):
            if role not in resource_spec:
                raise serializers.ValidationError(_("resource_spec 缺少角色: {}").format(role))
            count = resource_spec[role].get("count")
            if not count or count <= 0:
                raise serializers.ValidationError(_("resource_spec.{} 的 count 必须大于 0").format(role))

        # shardsvr 每片成员数 = mongodb 总机器数 / 机器组数（一组机器构成一个分片副本集）
        mongodb_count = resource_spec["mongodb"]["count"]
        if mongodb_count % shard_machine_group != 0:
            raise serializers.ValidationError(
                _(
                    "mongodb 机器数(count={mongodb_count})必须能被机器组数"
                    "(shard_machine_group={shard_machine_group})整除，"
                    "否则每组 shardsvr 成员数计算错误，部署会失败"
                ).format(mongodb_count=mongodb_count, shard_machine_group=shard_machine_group)
            )
        shardsvr_members = mongodb_count // shard_machine_group
        configsvr_members = resource_spec["mongo_config"]["count"]
        # 允许双方均为 1（单节点联调）；shardsvr 多成员时 configsvr 必须为 3
        if shardsvr_members != 1 and configsvr_members != 3:
            raise serializers.ValidationError(_("当 shardsvr 副本集成员数大于 1 时，configsvr 必须是 3 个成员"))
        return attrs


class MongoShardedClusterApplyFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.cluster_create

    def format_ticket_data(self):
        self.ticket_data["bk_app_abbr"] = self.ticket_data["db_app_abbr"]
        self.ticket_data["proxy_port"] = self.ticket_data["start_port"]

        # 补充zone_list数据 取分片集任意组件下园区即可
        self.ticket_data["zone_list"] = get_ticket_zone_list(self.ticket_data, "mongo_config")


class MongoShardedClusterResourceParamBuilder(BaseMongoDBOperateResourceParamBuilder):
    def format(self):
        """格式化mongodb申请的组数"""
        self.ticket_data["resource_spec"]["mongodb"]["tolerance"] = get_mongodb_cluster_tolerance(
            self.ticket_data["disaster_tolerance_level"], "mongodb"
        )
        self.ticket_data["resource_spec"]["mongo_config"]["tolerance"] = get_mongodb_cluster_tolerance(
            self.ticket_data["disaster_tolerance_level"], "mongo_config"
        )
        self.ticket_data["resource_spec"]["mongos"]["tolerance"] = get_mongodb_cluster_tolerance(
            self.ticket_data["disaster_tolerance_level"], "mongos"
        )

        resource_spec = self.ticket_data["resource_spec"]
        # 每组 shardsvr 成员数 = mongodb.count / shard_machine_group（勿用默认 3 覆盖用户填写）
        shard_machine_group = self.ticket_data["shard_machine_group"]
        shardsvr_members = resource_spec["mongodb"]["count"] // shard_machine_group
        self.format_mongo_resource_spec(resource_spec, shard_machine_group, shard_count=shardsvr_members)

    def post_callback(self):
        with self.next_flow_manager() as next_flow:
            # 重新组合mongodb的资源信息
            node_infos = next_flow.details["ticket_data"]["nodes"]
            self.format_mongo_node_infos(node_infos)
            # 格式化资源池申请信息
            resource_spec = next_flow.details["ticket_data"]["resource_spec"]
            machine_specs = self.format_machine_specs(resource_spec)
            # 更新ticket_data
            next_flow.details["ticket_data"].update(machine_specs=machine_specs)
            next_flow.details["ticket_data"].update(nodes=node_infos)


@builders.BuilderFactory.register(
    TicketType.MONGODB_SHARD_APPLY,
    is_apply=True,
    cluster_type=ClusterType.MongoShardedCluster,
    iam=ActionEnum.MONGODB_APPLY,
)
class MongoShardedClusterApplyFlowBuilder(BaseMongoShardedTicketFlowBuilder):
    serializer = MongoShardedClusterApplyDetailSerializer
    inner_flow_builder = MongoShardedClusterApplyFlowParamBuilder
    inner_flow_name = _("MongoDB 分片集群部署执行")
    resource_apply_builder = MongoShardedClusterResourceParamBuilder

    def patch_ticket_detail(self):
        # TODO: 待后台flow就绪调试
        print(self.ticket.details)
