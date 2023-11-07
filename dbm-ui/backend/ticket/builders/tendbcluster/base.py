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
from django.db.models import Q
from django.utils.translation import ugettext as _
from rest_framework import serializers

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterTenDBClusterStatusFlag, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster
from backend.flow.consts import MAX_SPIDER_MASTER_COUNT, MIN_SPIDER_MASTER_COUNT, MIN_SPIDER_SLAVE_COUNT
from backend.ticket import builders
from backend.ticket.builders import TicketFlowBuilder
from backend.ticket.builders.common.base import MySQLTicketFlowBuilderPatchMixin, fetch_cluster_ids
from backend.ticket.builders.mysql.base import (
    MySQLBaseOperateDetailSerializer,
    MySQLBaseOperateResourceParamBuilder,
    MySQLClustersTakeDownDetailsSerializer,
)
from backend.ticket.constants import TicketType


class BaseTendbTicketFlowBuilder(MySQLTicketFlowBuilderPatchMixin, TicketFlowBuilder):
    group = DBType.TenDBCluster.value


class TendbBasePauseParamBuilder(builders.PauseParamBuilder):
    pass


class TendbBaseOperateDetailSerializer(MySQLBaseOperateDetailSerializer):
    """
    tendbcluster操作的基类，主要功能:
    1. 屏蔽序列化的to_representation
    2. 存放tendbcluster操作的各种校验逻辑
    """

    #  实例不可用时，还能正常提单类型的白名单
    # spider 接入层异常, 只允许修复接入层异常的单据 1. 踢出故障 spider 2. 上架 (扩容) 新的 spider
    SPIDER_UNAVAILABLE_WHITELIST = []
    # 存储层 master 异常 (dbha 因为某些问题未正常介入),只有切换单据可用
    REMOTE_MASTER_UNAVAILABLE_WHITELIST = [
        TicketType.TENDBCLUSTER_MASTER_SLAVE_SWITCH,
        TicketType.TENDBCLUSTER_MASTER_FAIL_OVER,
    ]
    # 存储层 slave 异常 (正常情况下,所有存储异常最终都会变成slave异常),备份, 校验单据不可用
    REMOTE_SLAVE_UNAVAILABLE_WHITELIST = [
        t
        for t in TicketType.get_ticket_type_by_db(DBType.TenDBCluster.value)
        if t
        not in [
            TicketType.TENDBCLUSTER_FULL_BACKUP,
            TicketType.TENDBCLUSTER_DB_TABLE_BACKUP,
            TicketType.TENDBCLUSTER_CHECKSUM,
        ]
    ]

    # 集群的flag状态与白名单的映射表
    unavailable_whitelist__status_flag = {
        ClusterTenDBClusterStatusFlag.SpiderUnavailable: SPIDER_UNAVAILABLE_WHITELIST,
        ClusterTenDBClusterStatusFlag.RemoteMasterUnavailable: REMOTE_MASTER_UNAVAILABLE_WHITELIST,
        ClusterTenDBClusterStatusFlag.RemoteSlaveUnavailable: REMOTE_SLAVE_UNAVAILABLE_WHITELIST,
    }

    @classmethod
    def fetch_cluster_map(cls, attrs):
        cluster_ids = fetch_cluster_ids(attrs)
        clusters = Cluster.objects.prefetch_related("proxyinstance_set", "storageinstance_set").filter(
            id__in=cluster_ids
        )
        cluster_id__cluster = {cluster.id: cluster for cluster in clusters}
        return cluster_id__cluster

    def validate_max_spider_master_mnt_count(self, attrs):
        """校验部署后spider_master + spider_mnt的数量<37"""
        cluster_id__cluster = self.fetch_cluster_map(attrs)
        for info in attrs["infos"]:
            cluster = cluster_id__cluster[info["cluster_id"]]
            # 对于spider-slave的情况不校验
            if (
                self.context["ticket_type"] == TicketType.TENDBCLUSTER_SPIDER_ADD_NODES
                and info["add_spider_role"] == TenDBClusterSpiderRole.SPIDER_SLAVE
            ):
                continue

            # 获取当前存在的spider master/spider mnt 节点数量 以及 新加入的节点数量
            spider_master_mnt_count = cluster.proxyinstance_set.filter(
                Q(tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER)
                | Q(tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MNT)
            ).count()
            if self.context["ticket_type"] == TicketType.TENDBCLUSTER_SPIDER_ADD_NODES:
                new_add_count = info["resource_spec"]["spider_ip_list"]["count"]
            else:
                new_add_count = len(info["spider_ip_list"])

            if spider_master_mnt_count + new_add_count > MAX_SPIDER_MASTER_COUNT:
                raise serializers.ValidationError(_("【{}】请保证集群部署的接入层主节点和运维节点的总和小于37").format(cluster.name))

    def validate_min_spider_count(self, attrs):
        """校验缩容后，spider节点能满足最小限度"""
        cluster_id__cluster = self.fetch_cluster_map(attrs)
        for info in attrs["infos"]:
            cluster = cluster_id__cluster[info["cluster_id"]]

            spider_node_count = cluster.proxyinstance_set.filter(
                tendbclusterspiderext__spider_role=info["reduce_spider_role"]
            ).count()
            if info["spider_reduced_to_count"] >= spider_node_count:
                raise serializers.ValidationError(_("【{}】请保证缩容后的接入层数量小于当前节点数量").format(cluster.name))

            role = info["reduce_spider_role"]
            if (
                role == TenDBClusterSpiderRole.SPIDER_MASTER
                and info["spider_reduced_to_count"] < MIN_SPIDER_MASTER_COUNT
            ):
                raise serializers.ValidationError(_("【{}】请保证缩容后的接入层spider master数量>1").format(cluster.name))

            if (
                role == TenDBClusterSpiderRole.SPIDER_SLAVE
                and info["spider_reduced_to_count"] < MIN_SPIDER_SLAVE_COUNT
            ):
                raise serializers.ValidationError(_("【{}】请保证缩容后的接入层spider master数量>0").format(cluster.name))

    def validate_checksum_database_selector(self, attrs):
        """校验tendbcluster的checksum库表选择器"""
        cluster_database_info = {
            "infos": [
                {**backup_info, "cluster_id": info["cluster_id"]}
                for info in attrs["infos"]
                for backup_info in info["backup_infos"]
            ]
        }
        super().validate_database_table_selector(attrs=cluster_database_info)


class TendbClustersTakeDownDetailsSerializer(MySQLClustersTakeDownDetailsSerializer):
    is_only_delete_slave_domain = serializers.BooleanField(help_text=_("是否只禁用只读接入层"), required=False, default=False)
    is_only_add_slave_domain = serializers.BooleanField(help_text=_("是否只启用只读接入层"), required=False, default=False)


class TendbBaseOperateResourceParamBuilder(MySQLBaseOperateResourceParamBuilder):
    pass
