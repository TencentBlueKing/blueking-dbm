# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

NOTE: 入参契约对齐正式部署单据，改动时两边一起改：
  - 副本集: ticket/builders/mongodb/mongo_replicaset_apply.py
    (MongoReplicaSetApplyDetailSerializer)
  - 分片: ticket/builders/mongodb/mongo_shard_apply.py
    (MongoShardedClusterApplyDetailSerializer)
"""
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.configuration.constants import AffinityEnum
from backend.db_meta.enums.spec import SpecMachineType
from backend.db_services.dbbase.constants import IpSource
from backend.dbm_aiagent.mcp_tools.mongodb.impl.mongodb_bill import filter_disallowed_spec_ids

_MONGO_SPEC_MACHINE_TYPES = (
    SpecMachineType.MONGODB.value,
    SpecMachineType.MONOG_CONFIG.value,
    SpecMachineType.MONGOS.value,
)


def _validate_spec_whitelist(spec_ids):
    """创单只允许使用 list_mongodb_specs 返回的规格，避免 AI 传入任意 spec_id。"""
    disallowed = filter_disallowed_spec_ids(spec_ids)
    if disallowed:
        raise serializers.ValidationError(_("spec_id {} 不可用，请先调用 list_mongodb_specs 获取可选规格").format(disallowed))


def _resource_spec_spec_ids(resource_spec):
    if not isinstance(resource_spec, dict):
        return []
    return [role.get("spec_id") for role in resource_spec.values() if isinstance(role, dict)]


class SubmitBillOutputSerializer(serializers.Serializer):
    bill_id = serializers.IntegerField(help_text=_("单据 ID"))
    bill_url = serializers.CharField(help_text=_("单据地址"))


class ListMongoDBSpecsInputSerializer(serializers.Serializer):
    """列出 desc（备注）中含 mcp_allow（大小写不敏感）的 MongoDB 规格，供 apply 选型。"""

    machine_type = serializers.ChoiceField(
        choices=_MONGO_SPEC_MACHINE_TYPES,
        required=False,
        allow_blank=True,
        default="",
        help_text=_("可选。过滤机器类型：mongodb / mongo_config / mongos；不传则三类都返回"),
    )


class ListMongoDBSpecsOutputSerializer(serializers.Serializer):
    results = serializers.ListField(child=serializers.DictField(), help_text=_("规格列表"))
    count = serializers.IntegerField(help_text=_("数量"))


class _ReplicaSetItemSerializer(serializers.Serializer):
    set_id = serializers.CharField(help_text=_("复制集群 ID（英文数字及下划线）"))
    name = serializers.CharField(help_text=_("集群别名"), allow_blank=True, allow_null=True, required=False, default="")
    domain = serializers.CharField(help_text=_("集群域名，如 m1.rs0.dba.db"))


class SubmitBillMongoReplicaSetApplyInputSerializer(serializers.Serializer):
    """镜像 MongoReplicaSetApplyDetailSerializer；字段变更请回写正式单据 builder。"""

    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域 ID"), default=0)
    db_app_abbr = serializers.CharField(help_text=_("业务英文缩写"))
    city_code = serializers.CharField(
        help_text=_("城市代码，随机或不指定时用 default"),
        required=False,
        allow_blank=True,
        default="default",
    )
    disaster_tolerance_level = serializers.ChoiceField(
        help_text=_("容灾级别"),
        choices=AffinityEnum.get_choices(),
        required=False,
        default=AffinityEnum.NONE.value,
    )
    db_version = serializers.CharField(help_text=_("版本号，如 mongodb-6.0.27"))
    start_port = serializers.IntegerField(help_text=_("起始端口，默认 27001"), default=27001)
    replica_count = serializers.IntegerField(help_text=_("副本集数量"))
    node_count = serializers.IntegerField(help_text=_("副本集节点数量，MCP 固定为 3"))
    node_replica_count = serializers.IntegerField(help_text=_("每组主机部署副本集数量"))
    replica_sets = serializers.ListSerializer(
        help_text=_("副本集列表，数量需等于 replica_count"),
        child=_ReplicaSetItemSerializer(),
        allow_empty=False,
    )
    spec_id = serializers.IntegerField(help_text=_("规格 ID"))
    oplog_percent = serializers.IntegerField(help_text=_("oplog 容量占比"), default=10)
    ip_source = serializers.ChoiceField(
        help_text=_("主机来源：resource_pool（默认）或 manual_input"),
        choices=IpSource.get_choices(),
        required=False,
        default=IpSource.RESOURCE_POOL.value,
    )
    resource_spec = serializers.JSONField(
        help_text=_("资源池规格，格式如 {'mongo_machine_set': {'spec_id': 1, 'count': 3}}；resource_pool 时建议传"),
        required=False,
    )
    nodes = serializers.JSONField(help_text=_("手工录入节点；manual_input 时必填"), required=False)

    def validate(self, attrs):
        replica_count = attrs["replica_count"]
        node_replica_count = attrs["node_replica_count"]
        node_count = attrs["node_count"]
        if node_replica_count <= 0:
            raise serializers.ValidationError(_("node_replica_count 必须大于 0"))
        if replica_count <= 0:
            raise serializers.ValidationError(_("replica_count 必须大于 0"))
        if node_count != 3:
            raise serializers.ValidationError(_("MCP 仅允许部署标准 3 节点副本集，node_count 必须为 3"))
        if replica_count % node_replica_count != 0:
            raise serializers.ValidationError(_("replica_count 必须能被 node_replica_count 整除"))
        if len(attrs["replica_sets"]) != replica_count:
            raise serializers.ValidationError(
                _("replica_sets 数量({})与 replica_count({})不一致").format(len(attrs["replica_sets"]), replica_count)
            )
        ip_source = attrs.get("ip_source")
        if ip_source == IpSource.RESOURCE_POOL.value:
            if not attrs.get("resource_spec"):
                # builder 也可仅用 spec_id 补 infos；resource_spec 可选补全
                pass
        elif ip_source == IpSource.MANUAL_INPUT.value and not attrs.get("nodes"):
            raise serializers.ValidationError(_("manual_input 时 nodes 必填"))
        _validate_spec_whitelist([attrs["spec_id"], *_resource_spec_spec_ids(attrs.get("resource_spec"))])
        return attrs


class SubmitBillMongoShardApplyInputSerializer(serializers.Serializer):
    """镜像 MongoShardedClusterApplyDetailSerializer；字段变更请回写正式单据 builder。"""

    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域 ID"), default=0)
    db_app_abbr = serializers.CharField(help_text=_("业务英文缩写"))
    city_code = serializers.CharField(
        help_text=_("城市代码，随机或不指定时用 default"),
        required=False,
        allow_blank=True,
        default="default",
    )
    disaster_tolerance_level = serializers.ChoiceField(
        help_text=_("容灾级别"),
        choices=AffinityEnum.get_choices(),
        required=False,
        default=AffinityEnum.NONE.value,
    )
    cluster_name = serializers.CharField(help_text=_("集群 ID / 名称"))
    cluster_alias = serializers.CharField(
        help_text=_("集群别名"), required=False, allow_blank=True, allow_null=True, default=""
    )
    db_version = serializers.CharField(help_text=_("版本号，如 mongodb-6.0.27"))
    start_port = serializers.IntegerField(help_text=_("起始端口 / mongos 端口，默认 27021"), default=27021)
    oplog_percent = serializers.IntegerField(help_text=_("oplog 容量占比"), default=10)
    shard_machine_group = serializers.IntegerField(help_text=_("机器组数"))
    shard_num = serializers.IntegerField(help_text=_("集群分片数"))
    ip_source = serializers.ChoiceField(
        help_text=_("主机来源：resource_pool（默认）或 manual_input"),
        choices=IpSource.get_choices(),
        required=False,
        default=IpSource.RESOURCE_POOL.value,
    )
    resource_spec = serializers.JSONField(
        help_text=_(
            "资源申请规格，需含 mongodb / mongo_config / mongos，"
            "如 {'mongodb': {'spec_id': 1, 'count': 6}, "
            "'mongo_config': {'spec_id': 1, 'count': 3}, "
            "'mongos': {'spec_id': 1, 'count': 2}}；"
            "每个机器组 mongodb count=3，mongo_config count=3，mongos count>=2"
        ),
        required=False,
    )
    nodes = serializers.JSONField(help_text=_("手工录入节点；manual_input 时必填"), required=False)

    def validate(self, attrs):
        shard_num = attrs["shard_num"]
        shard_machine_group = attrs["shard_machine_group"]
        if shard_num <= 0:
            raise serializers.ValidationError(_("shard_num 必须大于 0"))
        if shard_machine_group <= 0:
            raise serializers.ValidationError(_("shard_machine_group 必须大于 0"))
        if shard_num % shard_machine_group != 0:
            raise serializers.ValidationError(_("shard_num 必须能被 shard_machine_group 整除"))

        resource_spec = attrs.get("resource_spec") or {}
        for role in ("mongodb", "mongo_config", "mongos"):
            if role not in resource_spec:
                raise serializers.ValidationError(_("resource_spec 缺少角色: {}").format(role))
            count = resource_spec[role].get("count")
            if not count or count <= 0:
                raise serializers.ValidationError(_("resource_spec.{} 的 count 必须大于 0").format(role))
            if not resource_spec[role].get("spec_id"):
                raise serializers.ValidationError(_("resource_spec.{} 缺少 spec_id").format(role))

        mongodb_count = resource_spec["mongodb"]["count"]
        if mongodb_count % shard_machine_group != 0:
            raise serializers.ValidationError(_("mongodb 机器数必须能被 shard_machine_group 整除"))
        shardsvr_members = mongodb_count // shard_machine_group
        if shardsvr_members != 3:
            raise serializers.ValidationError(_("MCP 仅允许部署标准 3 节点 shardsvr，每个机器组的 mongodb count 必须为 3"))
        if resource_spec["mongo_config"]["count"] != 3:
            raise serializers.ValidationError(_("MCP 仅允许部署标准 3 节点 configsvr，mongo_config count 必须为 3"))
        if resource_spec["mongos"]["count"] < 2:
            raise serializers.ValidationError(_("MCP 部署的 mongos count 不能少于 2"))

        ip_source = attrs.get("ip_source")
        if ip_source == IpSource.MANUAL_INPUT.value and not attrs.get("nodes"):
            raise serializers.ValidationError(_("manual_input 时 nodes 必填"))
        _validate_spec_whitelist(_resource_spec_spec_ids(attrs.get("resource_spec")))
        return attrs
