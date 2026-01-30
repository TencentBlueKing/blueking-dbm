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

from backend.db_services.dbbase.constants import IpSource


class SubmitBillOutputSerializer(serializers.Serializer):
    bill_id = serializers.IntegerField(help_text=_("单据id, 理论上都会返回，如果没有返回说明有错误，需要把错误暴露出来"))
    bill_url = serializers.CharField(help_text=_("单据地址"))


class SubmitBillKafkaBaseInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务 id, bk_biz_id"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))


class SubmitBillKafkaScaleUpInputSerializer(SubmitBillKafkaBaseInputSerializer):
    ip_source = serializers.ChoiceField(
        choices=IpSource.get_choices(),
        help_text=_("主机来源: resource_pool(资源池) 或 manual_input(手工输入)"),
    )
    nodes = serializers.JSONField(
        help_text=_("节点列表信息，格式为 {'broker': [{'ip': 'xxx', 'bk_host_id': xxx, 'bk_cloud_id': xxx}]}"),
        required=False,
    )
    resource_spec = serializers.JSONField(
        help_text=_("资源池规格，格式为 {'broker': {'count': 3, 'spec_id': xxx}}，当ip_source为resource_pool时必填"),
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
        return attrs


# Kafka 缩容单据相关 Serializer
class SubmitBillKafkaShrinkInputSerializer(SubmitBillKafkaBaseInputSerializer):
    nodes = serializers.JSONField(
        help_text=_("需要缩容的节点列表信息，格式为 {'broker': [{'ip': 'xxx', 'bk_host_id': xxx, 'bk_cloud_id': xxx}]}"),
    )

    def validate_nodes(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError(_("nodes必须是一个字典，格式为 {'broker': [...]}"))
        for role, node_list in value.items():
            if not isinstance(node_list, list):
                raise serializers.ValidationError(_("nodes[{}]必须是列表").format(role))
            for i, node in enumerate(node_list):
                if not isinstance(node, dict):
                    raise serializers.ValidationError(_("nodes[{}][{}]必须是字典").format(role, i))
                required_fields = ["bk_host_id", "bk_cloud_id"]
                missing_fields = [f for f in required_fields if f not in node]
                if missing_fields:
                    raise serializers.ValidationError(
                        _(
                            "节点{}索引{}缺少必需字段: {}，请使用cluster_overview接口获取完整节点信息。"
                            "仅提供'ip'字段是不够的，必须包含bk_host_id和bk_cloud_id。"
                        ).format(role, i, ", ".join(missing_fields))
                    )
        return value


# Kafka 替换单据相关 Serializer
class SubmitBillKafkaReplaceInputSerializer(SubmitBillKafkaBaseInputSerializer):
    old_nodes = serializers.JSONField(
        help_text=_("旧节点列表信息，格式为 {'broker': [{'ip': 'xxx', 'bk_host_id': xxx, 'bk_cloud_id': xxx}]}"),
    )
    ip_source = serializers.ChoiceField(
        choices=IpSource.get_choices(),
        help_text=_("主机来源: resource_pool(资源池) 或 manual_input(手工输入)，默认为资源池"),
        required=False,
        default=IpSource.RESOURCE_POOL.value,
    )
    new_nodes = serializers.JSONField(
        help_text=_(
            "新节点列表信息，格式为 {'broker': [{'ip': 'xxx', 'bk_host_id': xxx, 'bk_cloud_id': xxx}]}，当ip_source为manual_input时必填"
        ),
        required=False,
    )
    resource_spec = serializers.JSONField(
        help_text=_("资源池规格，格式为 {'broker': {'count': 3, 'spec_id': xxx}}，默认与被替换节点规格相同"),
        required=False,
    )

    def _validate_node_structure(self, nodes, field_name="nodes"):
        """验证节点结构是否包含必需字段"""
        if not isinstance(nodes, dict):
            raise serializers.ValidationError(_("{}必须是一个字典，格式为 {{'broker': [...]}}").format(field_name))
        for role, node_list in nodes.items():
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
        return nodes

    def validate_old_nodes(self, value):
        return self._validate_node_structure(value, "old_nodes")

    def validate_new_nodes(self, value):
        return self._validate_node_structure(value, "new_nodes")

    def validate(self, attrs):
        # 如果未指定 ip_source，默认使用资源池
        if "ip_source" not in attrs:
            attrs["ip_source"] = IpSource.RESOURCE_POOL.value

        ip_source = attrs.get("ip_source")
        if ip_source == IpSource.RESOURCE_POOL.value:
            # 资源池方式：resource_spec 可选，后端会自动填充与被替换节点相同的规格
            pass
        elif ip_source == IpSource.MANUAL_INPUT.value:
            if not attrs.get("new_nodes"):
                raise serializers.ValidationError(_("当主机来源为手工输入时，new_nodes字段必填"))
        return attrs


# Kafka 均衡单据相关 Serializer
class SubmitBillKafkaRebalanceInputSerializer(SubmitBillKafkaBaseInputSerializer):
    topics = serializers.ListField(
        help_text=_("需要均衡的topic列表，默认['*']表示所有topic"),
        child=serializers.CharField(),
        required=False,
        default=["*"],
    )
    throttle_rate = serializers.IntegerField(
        help_text=_("均衡速率，单位bytes/s。默认80000000(80MB/s)，建议值: 10000000-100000000(10MB/s-100MB/s)"),
        required=False,
        default=80000000,
    )
    target_ips = serializers.ListField(
        help_text=_("目标broker IP列表（可选），指定将数据均衡到这些IP所在的broker节点，不传则均衡到所有broker"),
        child=serializers.CharField(),
        required=False,
        default=None,
    )

    def validate_throttle_rate(self, value):
        if value <= 0:
            raise serializers.ValidationError(_("throttle_rate必须大于0"))
        if value > 1000000000:
            raise serializers.ValidationError(_("throttle_rate不能超过1000000000 bytes/s (1GB/s)"))
        return value

    def validate_topics(self, value):
        if not value:
            raise serializers.ValidationError(_("topics列表不能为空"))
        for i, topic in enumerate(value):
            if not isinstance(topic, str) or not topic.strip():
                raise serializers.ValidationError(_("topics列表第{}项必须是非空字符串").format(i))
        return value


# Kafka 实例重启单据相关 Serializer
class SubmitBillKafkaRebootInputSerializer(SubmitBillKafkaBaseInputSerializer):
    instance_list = serializers.JSONField(
        help_text=_(
            "需要重启的实例列表，格式为 [{'ip': 'xxx', 'port': xxx, 'instance_id': xxx, 'bk_host_id': xxx, 'bk_cloud_id': xxx}]"
        ),
    )

    def validate_instance_list(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError(_("instance_list必须是一个列表"))

        for i, instance in enumerate(value):
            if not isinstance(instance, dict):
                raise serializers.ValidationError(_("instance_list第{}项必须是字典").format(i))

            required_fields = ["ip", "port", "bk_host_id", "bk_cloud_id"]
            missing_fields = [f for f in required_fields if f not in instance]

            if missing_fields:
                raise serializers.ValidationError(
                    _("instance_list第{}项缺少必需字段: {}").format(i, ", ".join(missing_fields))
                )

            # 验证 port 是整数
            if not isinstance(instance.get("port"), int):
                raise serializers.ValidationError(_("instance_list第{}项的port必须是整数").format(i))

        return value


# Kafka 集群启用单据相关 Serializer
class SubmitBillKafkaEnableInputSerializer(SubmitBillKafkaBaseInputSerializer):
    def validate(self, attrs):
        from backend.db_meta.enums import ClusterPhase
        from backend.db_meta.models import Cluster

        attrs = super().validate(attrs)

        cluster = Cluster.objects.get(bk_biz_id=attrs["bk_biz_id"], immute_domain=attrs["cluster_domain"])

        # 启用操作必须是禁用状态
        if cluster.phase != ClusterPhase.OFFLINE.value:
            raise serializers.ValidationError(
                _("启用集群前，集群必须处于禁用状态。当前集群状态为：{}。" "状态转移规则：ONLINE(在线) → OFFLINE(禁用) → ONLINE(在线)").format(cluster.phase)
            )

        return attrs


# Kafka 集群禁用单据相关 Serializer
class SubmitBillKafkaDisableInputSerializer(SubmitBillKafkaBaseInputSerializer):
    def validate(self, attrs):
        from backend.db_meta.enums import ClusterPhase
        from backend.db_meta.models import Cluster

        attrs = super().validate(attrs)

        cluster = Cluster.objects.get(bk_biz_id=attrs["bk_biz_id"], immute_domain=attrs["cluster_domain"])

        # 禁用操作必须是在线状态
        if cluster.phase != ClusterPhase.ONLINE.value:
            raise serializers.ValidationError(
                _("禁用集群前，集群必须处于在线状态。当前集群状态为：{}。" "状态转移规则：ONLINE(在线) → OFFLINE(禁用)").format(cluster.phase)
            )

        return attrs


# Kafka 集群删除单据相关 Serializer
class SubmitBillKafkaDestroyInputSerializer(SubmitBillKafkaBaseInputSerializer):
    def validate(self, attrs):
        from backend.db_meta.enums import ClusterPhase
        from backend.db_meta.models import Cluster

        attrs = super().validate(attrs)

        cluster = Cluster.objects.get(bk_biz_id=attrs["bk_biz_id"], immute_domain=attrs["cluster_domain"])

        # 删除操作必须先禁用
        if cluster.phase != ClusterPhase.OFFLINE.value:
            raise serializers.ValidationError(
                _("删除集群前，集群必须处于禁用状态。当前集群状态为：{}，请先执行禁用操作。" "状态转移规则：ONLINE(在线) → OFFLINE(禁用) → DESTROY(删除)").format(
                    cluster.phase
                )
            )

        return attrs


# Kafka 集群部署单据相关 Serializer
class SubmitBillKafkaApplyInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务 id, bk_biz_id"))
    cluster_name = serializers.CharField(help_text=_("集群名称"))
    ip_source = serializers.ChoiceField(
        choices=IpSource.get_choices(),
        help_text=_("主机来源: resource_pool(资源池) 或 manual_input(手工输入)，默认资源池"),
        required=False,
        default=IpSource.RESOURCE_POOL.value,
    )
    nodes = serializers.JSONField(
        help_text=(
            _(
                "节点列表信息，格式为 {'zookeeper': [{'ip': 'xxx', 'bk_host_id': xxx, 'bk_cloud_id': xxx}], "
                "'broker': [{'ip': 'xxx', 'bk_host_id': xxx, 'bk_cloud_id': xxx}]}。"
                "zookeeper必须正好3个节点，broker至少1个节点"
            )
        ),
        required=False,
    )
    resource_spec = serializers.JSONField(
        help_text=(
            _(
                "资源池规格，格式为 {'zookeeper': {'count': 3, 'spec_id': xxx}, "
                "'broker': {'count': 3, 'spec_id': xxx}}，当ip_source为resource_pool时必填。"
                "zookeeper固定为3个节点"
            )
        ),
        required=False,
    )
    db_app_abbr = serializers.CharField(help_text=_("业务缩写，用于生成域名前缀"))
    timezone = serializers.CharField(help_text=_("时区，默认 Asia/Shanghai"), required=False, default="Asia/Shanghai")
    city_code = serializers.CharField(help_text=_("城市代码"))
    region = serializers.CharField(help_text=_("区域，默认 default"), required=False, default="default")
    disaster_tolerance_level = serializers.CharField(
        help_text=_("容灾级别，默认 MAX_EACH_ZONE_EQUAL(各机房均衡)"), required=False, default="MAX_EACH_ZONE_EQUAL"
    )
    replication_num = serializers.IntegerField(
        help_text=_("副本数，默认2。必须小于等于broker节点数量。" "建议值: 2 (双副本，在可靠性和性能间取得平衡)"),
        required=False,
        default=2,
    )
    version = serializers.CharField(help_text=_("Kafka版本，默认 2.4.0"), required=False, default="2.4.0")

    def validate_replication_num(self, value):
        if value < 1 or value > 10:
            raise serializers.ValidationError(_("replication_num必须在1-10之间"))
        return value

    def validate_nodes(self, value):
        """验证节点结构"""
        if not isinstance(value, dict):
            raise serializers.ValidationError(_("nodes必须是一个字典，格式为 {'zookeeper': [...], 'broker': [...]}"))

        required_roles = ["zookeeper", "broker"]
        for role in required_roles:
            if role not in value:
                raise serializers.ValidationError(_("nodes必须包含{}节点列表").format(role))

        for role, node_list in value.items():
            if not isinstance(node_list, list):
                raise serializers.ValidationError(_("nodes[{}]必须是列表").format(role))

            for i, node in enumerate(node_list):
                if not isinstance(node, dict):
                    raise serializers.ValidationError(_("nodes[{}][{}]必须是字典").format(role, i))

                required_fields = ["bk_host_id", "bk_cloud_id"]
                missing_fields = [f for f in required_fields if f not in node]
                if missing_fields:
                    raise serializers.ValidationError(
                        _(
                            "{}中的节点{}索引{}缺少必需字段: {}，请使用cluster_overview接口获取完整节点信息。"
                            "仅提供'ip'字段是不够的，必须包含bk_host_id和bk_cloud_id。"
                        ).format(role, i, ", ".join(missing_fields))
                    )

        return value

    def validate(self, attrs):
        ip_source = attrs.get("ip_source")
        if ip_source == IpSource.RESOURCE_POOL.value:
            if not attrs.get("resource_spec"):
                raise serializers.ValidationError(_("当主机来源为资源池时，resource_spec字段必填"))
            # 验证zookeeper固定为3个节点
            spec = attrs["resource_spec"]
            if "zookeeper" not in spec or spec["zookeeper"].get("count") != 3:
                raise serializers.ValidationError(_("资源池规格中zookeeper必须固定为3个节点"))
        elif ip_source == IpSource.MANUAL_INPUT.value:
            if not attrs.get("nodes"):
                raise serializers.ValidationError(_("当主机来源为手工输入时，nodes字段必填"))
            # 验证zookeeper必须正好3个节点
            nodes = attrs["nodes"]
            zk_count = len(nodes.get("zookeeper", []))
            if zk_count != 3:
                raise serializers.ValidationError(_("zookeeper节点必须正好3个节点，当前为{}个").format(zk_count))
            # 验证broker至少1个节点
            broker_count = len(nodes.get("broker", []))
            if broker_count < 1:
                raise serializers.ValidationError(_("broker节点至少需要1个节点"))

        # 验证副本数不能超过broker节点数量
        broker_count = 0
        if ip_source == IpSource.RESOURCE_POOL.value:
            broker_count = attrs["resource_spec"]["broker"]["count"]
        else:
            broker_count = len(attrs["nodes"].get("broker", []))

        replication_num = attrs.get("replication_num", 2)
        if replication_num > broker_count:
            raise serializers.ValidationError(_("副本数({})不能超过broker节点数量({})").format(replication_num, broker_count))

        return attrs
