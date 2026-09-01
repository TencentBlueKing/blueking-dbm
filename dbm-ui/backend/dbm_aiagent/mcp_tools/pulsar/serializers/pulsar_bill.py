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
import json

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_services.dbbase.constants import IpSource


class LenientJSONField(serializers.JSONField):
    """
    兼容 MCP 工具调用侧把嵌套对象/数组序列化成 JSON 字符串传入的情况。

    原生 serializers.JSONField 遇到字符串类型的输入时不会反向 json.loads()，
    只会用 json.dumps() 校验其可序列化性，校验通过后原样返回字符串本身，
    导致业务逻辑对它调用 .get()/.items() 时报 AttributeError。
    """

    def to_internal_value(self, data):
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except (TypeError, ValueError):
                self.fail("invalid")
        return super().to_internal_value(data)


# Pulsar 可扩缩容的角色，zookeeper 固定 3 台不参与扩缩容
SCALABLE_ROLE_NAMES = ["broker", "bookkeeper"]
# 替换支持全部三个角色
REPLACEABLE_ROLE_NAMES = ["broker", "bookkeeper", "zookeeper"]


def validate_role_nodes(value, allowed_roles, field_name="nodes"):
    """
    校验按角色分组的节点字典，形如 {"broker": [{...}], "bookkeeper": [{...}]}
    """
    if not isinstance(value, dict):
        raise serializers.ValidationError(
            _("{}必须是一个字典，格式为 {{'broker': [...], 'bookkeeper': [...]}}").format(field_name)
        )

    invalid_roles = [role for role in value if role not in allowed_roles]
    if invalid_roles:
        raise serializers.ValidationError(
            _("{}包含不支持的角色: {}，可选角色: {}").format(field_name, ", ".join(invalid_roles), ", ".join(allowed_roles))
        )

    for role, node_list in value.items():
        if not isinstance(node_list, list):
            raise serializers.ValidationError(_("{}[{}]必须是列表").format(field_name, role))
        for i, node in enumerate(node_list):
            if not isinstance(node, dict):
                raise serializers.ValidationError(_("{}[{}][{}]必须是字典").format(field_name, role, i))
            missing_fields = [f for f in ["bk_host_id", "bk_cloud_id"] if f not in node]
            if missing_fields:
                raise serializers.ValidationError(
                    _("{}[{}][{}]缺少必填字段: {}").format(field_name, role, i, ", ".join(missing_fields))
                )
    return value


class PulsarSubmitBillOutputSerializer(serializers.Serializer):
    bill_id = serializers.IntegerField(help_text=_("单据id, 理论上都会返回，如果没有返回说明有错误，需要把错误暴露出来"))
    bill_url = serializers.CharField(help_text=_("单据地址"))


class SubmitBillPulsarBaseInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务 id, bk_biz_id"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))


class SubmitBillPulsarScaleUpInputSerializer(SubmitBillPulsarBaseInputSerializer):
    ip_source = serializers.ChoiceField(
        choices=IpSource.get_choices(),
        help_text=_("主机来源: resource_pool(资源池) 或 manual_input(手工输入)，默认资源池"),
        required=False,
        default=IpSource.RESOURCE_POOL.value,
    )
    nodes = LenientJSONField(
        help_text=_(
            "节点列表信息，可含 broker/bookkeeper 两个角色，"
            "格式为 {'broker': [{'ip': 'xxx', 'bk_host_id': xxx, 'bk_cloud_id': xxx}], 'bookkeeper': [...]}"
        ),
        required=False,
    )
    resource_spec = LenientJSONField(
        help_text=_(
            "资源池规格，可含 broker/bookkeeper 两个角色，"
            "格式为 {'broker': {'count': 3, 'spec_id': xxx}, 'bookkeeper': {'count': 2, 'spec_id': xxx}}，"
            "当ip_source为resource_pool时必填。"
            "spec_id 可省略，省略时自动沿用该角色现有节点的规格，"
            "因此用户只说'扩容N台broker'而未指明规格时，无需追问规格，直接用 {'broker': {'count': N}} 提交即可"
        ),
        required=False,
    )

    def validate(self, attrs):
        ip_source = attrs.get("ip_source")
        if ip_source == IpSource.RESOURCE_POOL.value:
            if not attrs.get("resource_spec"):
                raise serializers.ValidationError(_("当主机来源为资源池时，resource_spec字段必填"))
        elif ip_source == IpSource.MANUAL_INPUT.value:
            if not attrs.get("nodes"):
                raise serializers.ValidationError(_("当主机来源为手工输入时，nodes字段必填"))
            validate_role_nodes(attrs["nodes"], SCALABLE_ROLE_NAMES)
        return attrs


class SubmitBillPulsarShrinkInputSerializer(SubmitBillPulsarBaseInputSerializer):
    nodes = LenientJSONField(
        help_text=_(
            "需要缩容的节点，可含 broker/bookkeeper 两个角色（不支持缩容 zookeeper），"
            "格式为 {'broker': [{'ip': 'xxx', 'bk_host_id': xxx, 'bk_cloud_id': xxx}], 'bookkeeper': [...]}。"
            "注意：broker 至少保留1台，bookkeeper 至少保留2台"
        ),
    )

    def validate_nodes(self, value):
        value = validate_role_nodes(value, SCALABLE_ROLE_NAMES)
        if not any(value.get(role) for role in SCALABLE_ROLE_NAMES):
            raise serializers.ValidationError(_("请至少选择一个 broker 或 bookkeeper 节点进行缩容"))
        return value


class SubmitBillPulsarReplaceInputSerializer(SubmitBillPulsarBaseInputSerializer):
    old_nodes = LenientJSONField(
        help_text=_(
            "被替换的节点，可含 broker/bookkeeper/zookeeper 三个角色，"
            "格式为 {'broker': [{'ip': 'xxx', 'bk_host_id': xxx, 'bk_cloud_id': xxx}]}"
        ),
    )
    ip_source = serializers.ChoiceField(
        choices=IpSource.get_choices(),
        help_text=_("新机器来源: resource_pool(资源池) 或 manual_input(手工输入)，默认资源池"),
        required=False,
        default=IpSource.RESOURCE_POOL.value,
    )
    new_nodes = LenientJSONField(
        help_text=_("新节点信息，当ip_source为manual_input时必填，各角色数量需与old_nodes一致"),
        required=False,
    )
    resource_spec = LenientJSONField(
        help_text=_("资源池规格，不传则按old_nodes数量和现有机器规格自动补齐"),
        required=False,
    )

    def validate_old_nodes(self, value):
        value = validate_role_nodes(value, REPLACEABLE_ROLE_NAMES, "old_nodes")
        if not any(value.get(role) for role in REPLACEABLE_ROLE_NAMES):
            raise serializers.ValidationError(_("请至少选择一个节点进行替换"))
        return value

    def validate(self, attrs):
        if attrs.get("ip_source") == IpSource.MANUAL_INPUT.value:
            if not attrs.get("new_nodes"):
                raise serializers.ValidationError(_("当主机来源为手工输入时，new_nodes字段必填"))
            validate_role_nodes(attrs["new_nodes"], REPLACEABLE_ROLE_NAMES, "new_nodes")
        return attrs


class PulsarRebootInstanceSerializer(serializers.Serializer):
    ip = serializers.CharField(help_text=_("实例IP"))
    port = serializers.IntegerField(help_text=_("实例端口"))
    instance_id = serializers.IntegerField(help_text=_("实例ID"))
    bk_host_id = serializers.IntegerField(help_text=_("主机ID"))
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    instance_name = serializers.CharField(help_text=_("实例名"), required=False, allow_blank=True)


class SubmitBillPulsarRebootInputSerializer(SubmitBillPulsarBaseInputSerializer):
    instance_list = serializers.ListSerializer(
        child=PulsarRebootInstanceSerializer(),
        help_text=_("待重启实例列表，实例信息可通过 pulsar_query_meta_cluster_overview 的 nodes 字段获取"),
    )


class SubmitBillPulsarTakeDownInputSerializer(SubmitBillPulsarBaseInputSerializer):
    """启用/禁用/删除类单据，只需集群信息"""


class SubmitBillPulsarApplyInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务 id, bk_biz_id"))
    cluster_name = serializers.CharField(help_text=_("集群名称（英文数字及下划线）"))
    cluster_alias = serializers.CharField(help_text=_("集群别名（一般为中文别名）"), required=False, allow_blank=True, default="")
    db_app_abbr = serializers.CharField(help_text=_("业务英文缩写"))
    city_code = serializers.CharField(help_text=_("城市代码，如 深圳 对应 shenzhen"))
    db_version = serializers.CharField(help_text=_("Pulsar版本，如 2.10.1"))
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID，默认0(直连区域)"), required=False, default=0)
    port = serializers.IntegerField(help_text=_("broker服务端口，如 6650"))
    partition_num = serializers.IntegerField(help_text=_("分区数"))
    retention_hours = serializers.IntegerField(help_text=_("消息保留时间(小时)"))
    replication_num = serializers.IntegerField(help_text=_("副本数，取值范围 2 到 bookkeeper 台数"))
    ack_quorum = serializers.IntegerField(help_text=_("最少成功写入副本数，必须小于等于 replication_num"))
    ip_source = serializers.ChoiceField(
        choices=IpSource.get_choices(),
        help_text=_("主机来源: resource_pool(资源池) 或 manual_input(手工输入)，默认资源池"),
        required=False,
        default=IpSource.RESOURCE_POOL.value,
    )
    nodes = LenientJSONField(
        help_text=_(
            "节点列表，当ip_source为manual_input时必填，"
            "格式 {'zookeeper': [...], 'bookkeeper': [...], 'broker': [...]}。"
            "注意：zookeeper 必须恰好3台，bookkeeper 至少2台，broker 至少1台"
        ),
        required=False,
    )
    resource_spec = LenientJSONField(
        help_text=_(
            "资源池规格，当ip_source为resource_pool时必填，"
            "格式 {'zookeeper': {'count': 3, 'spec_id': xxx}, 'bookkeeper': {...}, 'broker': {...}}"
        ),
        required=False,
    )

    def validate(self, attrs):
        if attrs["ack_quorum"] > attrs["replication_num"]:
            raise serializers.ValidationError(
                _("ack_quorum({})不能大于replication_num({})").format(attrs["ack_quorum"], attrs["replication_num"])
            )

        ip_source = attrs.get("ip_source", IpSource.RESOURCE_POOL.value)
        if ip_source == IpSource.RESOURCE_POOL.value:
            if not attrs.get("resource_spec"):
                raise serializers.ValidationError(_("当主机来源为资源池时，resource_spec字段必填"))
        elif ip_source == IpSource.MANUAL_INPUT.value:
            if not attrs.get("nodes"):
                raise serializers.ValidationError(_("当主机来源为手工输入时，nodes字段必填"))
        return attrs
