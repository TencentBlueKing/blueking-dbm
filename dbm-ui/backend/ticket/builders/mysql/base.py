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

from typing import Any, Dict, List, Union

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from rest_framework.serializers import ValidationError

from backend.configuration.constants import DBType
from backend.db_meta.enums import AccessLayer, ClusterDBHAStatusFlags, ClusterType, InstanceInnerRole
from backend.db_meta.models.cluster import Cluster, ClusterPhase
from backend.ticket import builders
from backend.ticket.builders import TicketFlowBuilder
from backend.ticket.builders.common.base import (
    CommonValidate,
    MySQLTicketFlowBuilderPatchMixin,
    SkipToRepresentationMixin,
    fetch_cluster_ids,
)
from backend.ticket.constants import TICKET_TYPE__CLUSTER_PHASE_MAP, TicketType


class BaseMySQLTicketFlowBuilder(MySQLTicketFlowBuilderPatchMixin, TicketFlowBuilder):
    group = DBType.MySQL.value


class MySQLBaseOperateDetailSerializer(SkipToRepresentationMixin, serializers.Serializer):
    """
    mysql操作的基类，主要功能:
    1. 屏蔽序列化的to_representation
    2. 存放mysql操作的各种校验逻辑
    """

    # 实例不可用时，还能正常提单类型的白名单
    SLAVE_UNAVAILABLE_CAN_ACCESS = [
        TicketType.MYSQL_IMPORT_SQLFILE.value,
        TicketType.MYSQL_CLIENT_CLONE_RULES.value,
        TicketType.MYSQL_ROLLBACK_CLUSTER.value,
        TicketType.MYSQL_HA_RENAME_DATABASE.value,
        TicketType.MYSQL_ADD_SLAVE.value,
        TicketType.MYSQL_RESTORE_LOCAL_SLAVE.value,
        TicketType.MYSQL_RESTORE_SLAVE.value,
        TicketType.MYSQL_HA_TRUNCATE_DATA.value,
    ]
    MASTER_UNAVAILABLE_CAN_ACCESS = []
    PROXY_UNAVAILABLE_CAN_ACCESS = [TicketType.get_values()]

    @classmethod
    def fetch_obj_by_keys(cls, obj_dict: Dict, keys: List[str]):
        """从给定的字典中提取key值"""
        objs: List[Any] = []
        for key in keys:
            if key not in obj_dict:
                continue

            if isinstance(obj_dict[key], list):
                objs.extend(obj_dict[key])
            else:
                objs.append(obj_dict[key])

        return objs

    def validate_cluster_can_access(self, attrs):
        """校验集群状态是否可以提单"""
        clusters = Cluster.objects.filter(id__in=fetch_cluster_ids(details=attrs))
        ticket_type = self.context["ticket_type"]
        for cluster in clusters:
            if (
                cluster.status_flag & ClusterDBHAStatusFlags.BackendMasterUnavailable
                and ticket_type not in self.MASTER_UNAVAILABLE_CAN_ACCESS
            ):
                raise serializers.ValidationError(_("matser实例状态异常，暂时无法执行该单据类型：{}").format(ticket_type))

            elif (
                cluster.status_flag & ClusterDBHAStatusFlags.BackendSlaveUnavailable
                and ticket_type not in self.SLAVE_UNAVAILABLE_CAN_ACCESS
            ):
                raise serializers.ValidationError(_("slave实例状态异常，暂时无法执行该单据类型：{}").format(ticket_type))

            elif (
                cluster.status_flag & ClusterDBHAStatusFlags.ProxyUnavailable
                and ticket_type not in self.PROXY_UNAVAILABLE_CAN_ACCESS
            ):
                raise serializers.ValidationError(_("proxy实例状态异常，暂时无法执行该单据类型：{}").format(ticket_type))

        return attrs

    def validate_hosts_clusters_in_same_cloud_area(self, attrs, host_key: List[str], cluster_key: List[str]):
        """校验新增机器和集群是否在同一云区域下"""
        for info in attrs["infos"]:
            host_infos = self.fetch_obj_by_keys(info, host_key)
            cluster_ids = self.fetch_obj_by_keys(info, cluster_key)
            if not CommonValidate.validate_hosts_clusters_in_same_cloud_area(host_infos, cluster_ids):
                raise serializers.ValidationError(_("请保证所选集群{}与新增机器{}在同一云区域下").format(cluster_ids, host_infos))

    def validate_instance_role(self, attrs, instance_key: List[str], role: Union[AccessLayer, InstanceInnerRole]):
        """校验实例的角色类型是否一致"""
        inst_list: List[Dict] = []
        for info in attrs["infos"]:
            inst_list.extend(self.fetch_obj_by_keys(info, instance_key))

        if not CommonValidate.validate_instance_role(inst_list, role):
            raise serializers.ValidationError(_("请保证实例f{}的角色类型为{}").format(inst_list, role))

    def validate_cluster_type(self, attrs, cluster_type: ClusterType):
        """校验集群类型为高可用"""
        cluster_ids = fetch_cluster_ids(attrs)
        if not CommonValidate.validate_cluster_type(cluster_ids, cluster_type):
            raise serializers.ValidationError(
                _("请保证所选集群{}都是{}集群").format(cluster_ids, ClusterType.get_choice_label(cluster_type))
            )

    def validate_instance_related_clusters(
        self, attrs, instance_key: List[str], cluster_key: List[str], role: Union[AccessLayer, InstanceInnerRole]
    ):
        """校验实例的关联集群是否一致"""
        # TODO: 貌似这里只能循环校验，数据量大可能会带来性能问题
        for info in attrs["infos"]:
            inst = self.fetch_obj_by_keys(info, instance_key)[0]
            cluster_ids = self.fetch_obj_by_keys(info, cluster_key)
            if not CommonValidate.validate_instance_related_clusters(inst, cluster_ids, role):
                raise serializers.ValidationError(_("请保证所选实例{}的关联集群为{}").format(inst, cluster_ids))

    def validate_database_table_selector(self, attrs, is_only_db_operate_list: List[bool] = None):
        """校验库表选择器的数据是否合法"""
        is_valid, message = CommonValidate.validate_database_table_selector(
            bk_biz_id=self.context["bk_biz_id"], infos=attrs["infos"], is_only_db_operate_list=is_only_db_operate_list
        )
        if not is_valid:
            raise serializers.ValidationError(message)

    def validate(self, attrs):
        # 默认全局校验只需要校验集群的状态
        self.validate_cluster_can_access(attrs)
        return attrs


class MySQLClustersTakeDownDetailsSerializer(SkipToRepresentationMixin, serializers.Serializer):
    cluster_ids = serializers.ListField(help_text=_("集群ID"), child=serializers.IntegerField())
    force = serializers.BooleanField(help_text=_("是否强制下架"), required=False, default=False)

    @classmethod
    def clusters_status_transfer_valid(cls, cluster_ids: List[int], ticket_type: str):
        cluster_list = Cluster.objects.filter(id__in=cluster_ids)
        for cluster in cluster_list:
            ticket_cluster_phase = TICKET_TYPE__CLUSTER_PHASE_MAP.get(ticket_type)
            if not ClusterPhase.cluster_status_transfer_valid(cluster.phase, ticket_cluster_phase):
                raise ValidationError(
                    _("集群{}状态转移不合法：{}--->{} is invalid").format(cluster.name, cluster.phase, ticket_cluster_phase)
                )

    def validate_cluster_ids(self, value):
        self.clusters_status_transfer_valid(cluster_ids=value, ticket_type=self.context["ticket_type"])
        return value
