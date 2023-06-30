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

from typing import Dict

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from rest_framework.serializers import ValidationError

from backend.configuration.constants import DBType
from backend.db_meta.enums.cluster_phase import ClusterPhase
from backend.db_meta.models.cluster import Cluster
from backend.db_meta.models.instance import StorageInstance
from backend.db_meta.models.machine import Machine
from backend.db_services.dbbase.constants import IpSource
from backend.ticket import builders
from backend.ticket.builders import TicketFlowBuilder
from backend.ticket.builders.common.base import (
    BigDataTicketFlowBuilderPatchMixin,
    CommonValidate,
    InfluxdbTicketFlowBuilderPatchMixin,
    remove_useless_spec,
)
from backend.ticket.builders.common.constants import BigDataRole
from backend.ticket.constants import TICKET_TYPE__CLUSTER_PHASE_MAP, TICKET_TYPE__CLUSTER_TYPE_MAP


class BigDataDetailsSerializer(serializers.Serializer):
    nodes = serializers.JSONField(help_text=_("节点列表信息"), required=False)

    def to_representation(self, instance):
        return instance

    @classmethod
    def validate_hosts_from_idle_pool(cls, bk_biz_id, nodes: Dict):
        hosts_set = set()
        for role in nodes:
            role_host_list = [node["bk_host_id"] for node in nodes[role] if node.get("bk_host_id")]
            hosts_set.update(role_host_list)

        hosts_not_in_idle_pool = CommonValidate.validate_hosts_from_idle_pool(bk_biz_id, list(hosts_set))
        if hosts_not_in_idle_pool:
            raise serializers.ValidationError(_("主机{}不在空闲机池，请保证所选的主机均来自空闲机").format(hosts_not_in_idle_pool))

    @classmethod
    def validate_hosts_not_in_db_meta(cls, nodes: Dict):
        for role in nodes:
            role_host_list = [node["bk_host_id"] for node in nodes[role] if node.get("bk_host_id")]
            exist_host_ids = Machine.objects.filter(bk_host_id__in=role_host_list)
            if exist_host_ids.exists():
                raise serializers.ValidationError(
                    _("主机{}已经被使用，请重新选择主机").format(list(exist_host_ids.values_list("ip", flat=True)))
                )

    @classmethod
    def validate_duplicate_cluster_name(cls, bk_biz_id, ticket_type, cluster_name):
        CommonValidate.validate_duplicate_cluster_name(bk_biz_id, ticket_type, cluster_name)


class BigDataSingleClusterOpsDetailsSerializer(BigDataDetailsSerializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))


class BigDataTakeDownDetailSerializer(BigDataSingleClusterOpsDetailsSerializer):
    def validate_cluster_id(self, value):
        """校验集群的phase转移是否符合预期"""

        ticket_type = self.context["ticket_type"]
        cluster = Cluster.objects.get(id=value)
        ticket_cluster_phase = TICKET_TYPE__CLUSTER_PHASE_MAP.get(ticket_type)
        if not ClusterPhase.cluster_status_transfer_valid(cluster.phase, ticket_cluster_phase):
            raise ValidationError(
                _("集群{}状态转移不合法：{}--->{} is invalid").format(cluster.name, cluster.phase, ticket_cluster_phase)
            )

        return value


class BigDataScaleDetailSerializer(BigDataSingleClusterOpsDetailsSerializer):
    ip_source = serializers.ChoiceField(help_text=_("主机来源"), choices=IpSource.get_choices())
    resource_spec = serializers.JSONField(help_text=_("资源池规格"), required=False)

    def validate(self, attrs):
        # 判断主机是否来自手工输入，从资源池拿到的主机不需要校验
        if attrs["ip_source"] == IpSource.RESOURCE_POOL:
            return attrs

        # 判断主机是否都来自空闲机
        super().validate_hosts_from_idle_pool(bk_biz_id=self.context["bk_biz_id"], nodes=attrs["nodes"])

        # 判断机器是否已经存在于db_meta中
        super().validate_hosts_not_in_db_meta(nodes=attrs["nodes"])

        return attrs


class BigDataApplyDetailsSerializer(BigDataDetailsSerializer):
    """大数据相关组件申请详情基类序列化器"""

    city_code = serializers.CharField(
        help_text=_("城市代码"), required=False, allow_blank=True, allow_null=True, default=""
    )
    db_app_abbr = serializers.CharField(help_text=_("业务英文缩写"))
    cluster_name = serializers.CharField(help_text=_("集群名称（英文数字及下划线）"))
    cluster_alias = serializers.CharField(help_text=_("集群别名（一般为中文别名）"), required=False, allow_blank=True)
    db_version = serializers.CharField(help_text=_("版本号"))
    ip_source = serializers.ChoiceField(help_text=_("主机来源"), choices=IpSource.get_choices())
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    resource_spec = serializers.JSONField(help_text=_("资源申请规格"), required=False)

    def get_node_count(self, attrs, role):
        if attrs["ip_source"] == IpSource.MANUAL_INPUT:
            return len(attrs["nodes"].get(role) or [])
        else:
            if role not in attrs["resource_spec"]:
                return 0
            return attrs["resource_spec"][role]["count"]

    def validate(self, attrs):
        bk_biz_id = self.context["bk_biz_id"]
        ticket_type = self.context["ticket_type"]

        # 判断是否存在同业务下同类型同名集群
        super().validate_duplicate_cluster_name(
            bk_biz_id=bk_biz_id, ticket_type=ticket_type, cluster_name=attrs["cluster_name"]
        )

        # 判断主机是否来自手工输入，从资源池拿到的主机不需要校验
        if attrs["ip_source"] == IpSource.RESOURCE_POOL:
            remove_useless_spec(attrs)
            return attrs

        # 判断主机角色是否互斥
        contain_role = [BigDataRole.Hdfs.ZK_JN.value, BigDataRole.Hdfs.NAMENODE.value]
        role__nodes_map = attrs["nodes"]
        ip__role_map: Dict = {}
        for role, nodes in role__nodes_map.items():
            for node in nodes:
                # 如果当前ip还没处于任何一个角色中，则赋予角色并继续
                if node["ip"] not in ip__role_map:
                    ip__role_map[node["ip"]] = role
                    continue

                # 如果包含在不互斥的角色列表中，则可忽略
                if ip__role_map[node["ip"]] in contain_role and role in contain_role:
                    continue

                # 出现主机角色互斥情况
                raise serializers.ValidationError(
                    _("主机{}出现角色互斥，{}与{}冲突").format(node["ip"], ip__role_map[node["ip"]], role)
                )

        # 判断主机是否都来自空闲机
        super().validate_hosts_from_idle_pool(bk_biz_id=bk_biz_id, nodes=attrs["nodes"])

        # 判断主机是否已经存在db_meta信息中
        super().validate_hosts_not_in_db_meta(nodes=attrs["nodes"])

        return attrs


class BigDataReplaceDetailSerializer(BigDataSingleClusterOpsDetailsSerializer):
    ip_source = serializers.ChoiceField(help_text=_("主机来源"), choices=IpSource.get_choices())
    old_nodes = serializers.DictField(help_text=_("旧节点信息集合"), child=serializers.ListField(help_text=_("节点信息")))
    new_nodes = serializers.DictField(
        help_text=_("新节点信息集合"), child=serializers.ListField(help_text=_("节点信息")), required=False
    )
    resource_spec = serializers.JSONField(help_text=_("规格类型"), required=False)

    def validate(self, attrs):
        # 校验替换前后角色类型和数量一致
        old_nodes = attrs["old_nodes"]
        new_nodes = attrs["new_nodes"] if attrs["ip_source"] == IpSource.MANUAL_INPUT else attrs["resource_spec"]
        if set(old_nodes.keys()) != set(new_nodes.keys()):
            raise serializers.ValidationError(_("替换前后角色类型不一致，请保证替换前后角色类型和数量一致！"))

        for role in old_nodes:
            old_role_num = len(old_nodes[role])
            new_role_num = (
                len(new_nodes[role]) if attrs["ip_source"] == IpSource.MANUAL_INPUT else new_nodes[role]["count"]
            )
            if old_role_num != new_role_num:
                raise serializers.ValidationError(_("角色{}替换前后数量不一致，请保证替换前后角色类型和数量一致！").format(role))

        # 判断主机是否来自手工输入，从资源池拿到的主机不需要校验
        if attrs["ip_source"] == IpSource.RESOURCE_POOL:
            return attrs

        # 校验替换后新的主机是否存在于空闲机
        super().validate_hosts_from_idle_pool(self.context["bk_biz_id"], attrs["new_nodes"])

        # 判断主机是否已经存在db_meta信息中
        super().validate_hosts_not_in_db_meta(nodes=attrs["new_nodes"])

        return attrs


class BigDataRebootDetailSerializer(BigDataSingleClusterOpsDetailsSerializer):
    class RebootNodeSerializer(serializers.Serializer):
        ip = serializers.CharField(help_text=_("IP"))
        port = serializers.IntegerField(help_text=_("端口号"))
        instance_name = serializers.CharField(help_text=_("实例名"), required=False, allow_blank=True)
        instance_id = serializers.IntegerField(help_text=_("实例ID"))
        bk_host_id = serializers.IntegerField(help_text=_("主机ID"))
        bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))

    instance_list = serializers.ListSerializer(help_text=_("实例列表"), child=RebootNodeSerializer())

    def validate(self, attrs):
        for instance_info in attrs["instance_list"]:
            instance = StorageInstance.objects.filter(machine=instance_info["bk_host_id"], port=instance_info["port"])
            if not instance.exists():
                raise serializers.ValidationError(_("实例{}不存在, 请重新确认实例的合法性").format(instance_info["instance_name"]))

            instance = instance.first()
            can_access, access_message = instance.can_access()
            if not can_access:
                raise serializers.ValidationError(_("无法进行重启操作，原因:{}").format(access_message))

        return attrs


class BigDataScaleUpResourceParamBuilder(builders.ResourceApplyParamBuilder):
    def format(self):
        super(BigDataScaleUpResourceParamBuilder, self).format()
        self.ticket_data["bk_cloud_id"] = Cluster.objects.get(id=self.ticket_data["cluster_id"]).bk_cloud_id


class BigDataReplaceResourceParamBuilder(builders.ResourceApplyParamBuilder):
    def format(self):
        super(BigDataReplaceResourceParamBuilder, self).format()
        self.ticket_data["bk_cloud_id"] = Cluster.objects.get(id=self.ticket_data["cluster_id"]).bk_cloud_id

    def post_callback(self):
        next_flow = self.ticket.next_flow()
        next_flow.details["ticket_data"]["new_nodes"] = next_flow.details["ticket_data"].pop("nodes")
        next_flow.save(update_fields=["details"])


class BaseEsTicketFlowBuilder(BigDataTicketFlowBuilderPatchMixin, TicketFlowBuilder):
    group = DBType.Es.value


class BaseHdfsTicketFlowBuilder(BigDataTicketFlowBuilderPatchMixin, TicketFlowBuilder):
    group = DBType.Hdfs.value


class BaseKafkaTicketFlowBuilder(BigDataTicketFlowBuilderPatchMixin, TicketFlowBuilder):
    group = DBType.Kafka.value


class BasePulsarTicketFlowBuilder(BigDataTicketFlowBuilderPatchMixin, TicketFlowBuilder):
    group = DBType.Pulsar.value


class BaseInfluxDBTicketFlowBuilder(InfluxdbTicketFlowBuilderPatchMixin, TicketFlowBuilder):
    group = DBType.InfluxDB.value


class BaseCloudTicketFlowBuilder(TicketFlowBuilder):
    group = DBType.Cloud.value


# TODO: Influxdb 单独封装，区别于其他集群，目前bigdata可以考虑拆分了
class BaseInfluxDBOpsDetailSerializer(BigDataDetailsSerializer):
    class InstanceSerializer(serializers.Serializer):
        ip = serializers.CharField(help_text=_("IP"))
        port = serializers.IntegerField(help_text=_("端口号"))
        instance_id = serializers.IntegerField(help_text=_("实例ID"))
        bk_host_id = serializers.IntegerField(help_text=_("主机ID"))
        bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))

    instance_list = serializers.ListSerializer(help_text=_("实例列表"), child=InstanceSerializer())

    def validate(self, attrs):
        for instance_info in attrs["instance_list"]:
            instance = StorageInstance.objects.filter(machine=instance_info["bk_host_id"], port=instance_info["port"])
            if not instance.exists():
                raise serializers.ValidationError(_("实例{}不存在, 请重新确认实例的合法性").format(instance_info["instance_name"]))
        return attrs


class BaseInfluxDBReplaceDetailSerializer(BigDataDetailsSerializer):
    ip_source = serializers.ChoiceField(help_text=_("主机来源"), choices=IpSource.get_choices())
    old_nodes = serializers.DictField(help_text=_("旧节点信息集合"), child=serializers.ListField(help_text=_("节点信息")))
    new_nodes = serializers.DictField(
        help_text=_("新节点信息集合"), child=serializers.ListField(help_text=_("节点信息")), required=False
    )
    resource_spec = serializers.JSONField(help_text=_("规格"), required=False)

    def validate(self, attrs):
        # 校验替换前后角色类型和数量一致
        old_nodes = attrs["old_nodes"]
        new_nodes = attrs["new_nodes"] if attrs["ip_source"] == IpSource.MANUAL_INPUT else attrs["resource_spec"]
        if set(old_nodes.keys()) != set(new_nodes.keys()):
            raise serializers.ValidationError(_("替换前后角色类型不一致，请保证替换前后角色类型和数量一致！"))

        for role in old_nodes:
            old_nodes_len = len(old_nodes[role])
            new_nodes_len = (
                len(new_nodes[role]) if attrs["ip_source"] == IpSource.MANUAL_INPUT else new_nodes[role]["count"]
            )
            if old_nodes_len != new_nodes_len:
                raise serializers.ValidationError(_("角色{}替换前后数量不一致，请保证替换前后角色类型和数量一致！").format(role))

        # 判断主机是否来自手工输入，从资源池拿到的主机不需要校验
        if attrs["ip_source"] == IpSource.RESOURCE_POOL:
            return attrs

        # 校验替换后新的主机是否存在于空闲机
        self.validate_hosts_from_idle_pool(self.context["bk_biz_id"], attrs["new_nodes"])

        # 判断主机是否已经存在db_meta信息中
        self.validate_hosts_not_in_db_meta(nodes=attrs["new_nodes"])

        return attrs
