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
import re

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.configuration.constants import AffinityEnum
from backend.db_services.dbbase.constants import ES_DEFAULT_PORT

# ES 集群包含的节点角色
ES_ROLES = ["master", "hot", "cold", "client"]


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


class SubmitBillOutputSerializer(serializers.Serializer):
    bill_id = serializers.IntegerField(help_text=_("单据id, 理论上都会返回，如果没有返回说明有错误，需要把错误暴露出来"))
    bill_url = serializers.CharField(help_text=_("单据地址"))


class SubmitBillEsBaseInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务 id, bk_biz_id"), min_value=1)
    cluster_domain = serializers.CharField(help_text=_("集群域名"))


def _validate_resource_spec(resource_spec):
    """校验资源池规格结构的合法性：每个角色须包含正整数 count 字段"""
    if not isinstance(resource_spec, dict):
        raise serializers.ValidationError(_("resource_spec必须是一个字典，格式为 {'role': {'count': 3, 'spec_id': xxx}}"))
    for role, spec in resource_spec.items():
        if role not in ES_ROLES:
            raise serializers.ValidationError(_("resource_spec包含非法角色: {}，合法角色为: {}").format(role, ES_ROLES))
        if not isinstance(spec, dict):
            raise serializers.ValidationError(_("resource_spec[{}]必须是一个字典").format(role))
        count = spec.get("count")
        if not isinstance(count, int) or count < 1:
            raise serializers.ValidationError(_("resource_spec[{}].count必须为正整数").format(role))
    return resource_spec


class _EsNodesFieldSerializer(object):
    """ES 节点列表字段校验混入类：形如 {"master": [...], "hot": [...], "cold": [...], "client": [...]}"""

    @classmethod
    def validate_es_nodes(cls, value, field_name="nodes"):
        if not isinstance(value, dict):
            raise serializers.ValidationError(
                _("{}必须是一个字典，格式为 {{'master': [...], 'hot': [...], 'cold': [...], 'client': [...]}}").format(field_name)
            )
        for role, node_list in value.items():
            if not isinstance(node_list, list):
                raise serializers.ValidationError(_("{}[{}]必须是列表").format(field_name, role))
            for i, node in enumerate(node_list):
                if not isinstance(node, dict):
                    raise serializers.ValidationError(_("{}[{}][{}]必须是字典").format(field_name, role, i))
                required_fields = ["bk_host_id", "bk_cloud_id"]
                missing_fields = [f for f in required_fields if f not in node]
                if missing_fields:
                    raise serializers.ValidationError(
                        _(
                            "{}中的节点{}索引{}缺少必需字段: {}，请使用cluster_overview接口获取完整节点信息。"
                            "仅提供'ip'字段是不够的，必须包含bk_host_id和bk_cloud_id。"
                        ).format(field_name, role, i, ", ".join(missing_fields))
                    )
        return value


class SubmitBillEsScaleUpInputSerializer(SubmitBillEsBaseInputSerializer):
    resource_spec = LenientJSONField(
        help_text=_("资源池规格，格式为 {'hot': {'count': 3, 'spec_id': xxx}}"),
    )

    def validate(self, attrs):
        if not attrs.get("resource_spec"):
            raise serializers.ValidationError(_("resource_spec字段必填"))
        _validate_resource_spec(attrs["resource_spec"])
        return attrs


class SubmitBillEsShrinkInputSerializer(SubmitBillEsBaseInputSerializer, _EsNodesFieldSerializer):
    old_nodes = LenientJSONField(
        help_text=_(
            "需要缩容的节点列表信息，格式为 {'hot': [{'ip': 'xxx', 'bk_host_id': xxx, 'bk_cloud_id': xxx}], 'cold': [...], 'client': [...]}"
        ),
    )

    def validate_old_nodes(self, value):
        return self.validate_es_nodes(value, "old_nodes")


class SubmitBillEsReplaceInputSerializer(SubmitBillEsBaseInputSerializer, _EsNodesFieldSerializer):
    old_nodes = LenientJSONField(
        help_text=_("旧节点列表信息，格式为 {'master': [...], 'hot': [...], 'cold': [...], 'client': [...]}"),
    )
    resource_spec = LenientJSONField(
        help_text=_("资源池规格，格式为 {'hot': {'count': 3, 'spec_id': xxx}}，默认与被替换节点规格相同"),
        required=False,
    )

    def validate_old_nodes(self, value):
        return self.validate_es_nodes(value, "old_nodes")

    def validate_resource_spec(self, value):
        return _validate_resource_spec(value)


class SubmitBillEsEnableInputSerializer(SubmitBillEsBaseInputSerializer):
    def validate(self, attrs):
        from backend.db_meta.enums import ClusterPhase
        from backend.db_meta.models import Cluster

        attrs = super().validate(attrs)
        cluster = Cluster.objects.get(bk_biz_id=attrs["bk_biz_id"], immute_domain=attrs["cluster_domain"])
        if cluster.phase != ClusterPhase.OFFLINE.value:
            raise serializers.ValidationError(
                _("启用集群前，集群必须处于禁用状态。当前集群状态为：{}。" "状态转移规则：ONLINE(在线) → OFFLINE(禁用) → ONLINE(在线)").format(cluster.phase)
            )
        return attrs


class SubmitBillEsDisableInputSerializer(SubmitBillEsBaseInputSerializer):
    def validate(self, attrs):
        from backend.db_meta.enums import ClusterPhase
        from backend.db_meta.models import Cluster

        attrs = super().validate(attrs)
        cluster = Cluster.objects.get(bk_biz_id=attrs["bk_biz_id"], immute_domain=attrs["cluster_domain"])
        if cluster.phase != ClusterPhase.ONLINE.value:
            raise serializers.ValidationError(
                _("禁用集群前，集群必须处于在线状态。当前集群状态为：{}。" "状态转移规则：ONLINE(在线) → OFFLINE(禁用)").format(cluster.phase)
            )
        return attrs


class SubmitBillEsDestroyInputSerializer(SubmitBillEsBaseInputSerializer):
    def validate(self, attrs):
        from backend.db_meta.enums import ClusterPhase
        from backend.db_meta.models import Cluster

        attrs = super().validate(attrs)
        cluster = Cluster.objects.get(bk_biz_id=attrs["bk_biz_id"], immute_domain=attrs["cluster_domain"])
        if cluster.phase != ClusterPhase.OFFLINE.value:
            raise serializers.ValidationError(
                _("删除集群前，集群必须处于禁用状态。当前集群状态为：{}，请先执行禁用操作。" "状态转移规则：ONLINE(在线) → OFFLINE(禁用) → DESTROY(删除)").format(
                    cluster.phase
                )
            )
        return attrs


class SubmitBillEsApplyInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务 id, bk_biz_id"), min_value=1)
    cluster_name = serializers.CharField(help_text=_("集群名称"))
    resource_spec = LenientJSONField(
        help_text=_(
            "资源池规格，格式为 {'master': {'count': 3, 'spec_id': xxx}, 'hot': {'count': 3, 'spec_id': xxx}, "
            "'cold': {...}, 'client': {...}}"
        ),
    )
    db_app_abbr = serializers.CharField(help_text=_("业务缩写，用于生成域名前缀"))
    version = serializers.CharField(help_text=_("ES版本，格式为 x.y.z，如 7.10.2"))
    http_port = serializers.IntegerField(
        help_text=_("端口，范围 1-65535，默认 9200"), min_value=1, max_value=65535, required=False, default=ES_DEFAULT_PORT
    )
    city_code = serializers.CharField(help_text=_("城市代码，如 default、上海、深圳等"))
    cluster_alias = serializers.CharField(help_text=_("集群别名，默认空字符串"), required=False, allow_blank=True, default="")
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID，非负整数，默认 0"), min_value=0, required=False, default=0)
    disaster_tolerance_level = serializers.ChoiceField(
        choices=AffinityEnum.get_choices(),
        help_text=_("容灾级别，默认 MAX_EACH_ZONE_EQUAL(各机房均衡)"),
        required=False,
        default=AffinityEnum.MAX_EACH_ZONE_EQUAL.value,
    )

    def validate_cluster_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError(_("cluster_name不能为空"))
        return value

    def validate_db_app_abbr(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError(_("db_app_abbr不能为空"))
        return value

    def validate_version(self, value):
        value = value.strip()
        if not re.match(r"^\d+\.\d+\.\d+$", value):
            raise serializers.ValidationError(_("ES版本格式不正确，应为 x.y.z 格式，如 7.10.2"))
        return value

    def validate_city_code(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError(_("city_code不能为空"))
        return value

    def validate(self, attrs):
        _validate_resource_spec(attrs["resource_spec"])
        spec = attrs["resource_spec"]
        master_count = spec.get("master", {}).get("count", 0)
        if master_count < 3 or (master_count & 1) == 0:
            raise serializers.ValidationError(_("master节点数量必须为>=3的奇数，请保证master至少3台且为奇数"))
        hot_count = spec.get("hot", {}).get("count", 0)
        cold_count = spec.get("cold", {}).get("count", 0)
        if hot_count + cold_count < 1:
            raise serializers.ValidationError(_("hot/cold节点至少需要1台"))

        return attrs


class SubmitBillEsNameServiceInputSerializer(SubmitBillEsBaseInputSerializer):
    """CLB / Polaris 等名字服务单据，仅需业务ID和集群域名"""
