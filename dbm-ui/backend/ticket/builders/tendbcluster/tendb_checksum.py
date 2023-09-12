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

from typing import Any, Dict, List

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.configuration.constants import DBType
from backend.db_meta.models import Cluster, StorageInstance, TenDBClusterStorageSet
from backend.flow.engine.controller.mysql import MySQLController
from backend.flow.engine.controller.spider import SpiderController
from backend.ticket import builders
from backend.ticket.builders.common.constants import (
    MySQLChecksumTicketMode,
    MySQLDataRepairTriggerMode,
    TendbChecksumScope,
)
from backend.ticket.builders.mysql.mysql_checksum import (
    MySQLChecksumFlowBuilder,
    MySQLChecksumFlowParamBuilder,
    MySQLDataRepairFlowParamBuilder,
)
from backend.ticket.builders.tendbcluster.base import TendbBaseOperateDetailSerializer
from backend.ticket.constants import TicketType
from backend.ticket.models import Flow


class TendbChecksumDetailSerializer(TendbBaseOperateDetailSerializer):
    class DataRepairSerializer(serializers.Serializer):
        is_repair = serializers.BooleanField(help_text=_("是否修复"))
        mode = serializers.ChoiceField(help_text=_("数据校验后修复执行类型"), choices=MySQLChecksumTicketMode.get_choices())

    class ChecksumDataInfoSerializer(serializers.Serializer):
        class BackupInfoSerializer(serializers.Serializer):
            master = serializers.CharField(help_text=_("主库实例"), required=False, allow_null=True, allow_blank=True)
            slave = serializers.CharField(help_text=_("从库实例"), required=False, allow_null=True, allow_blank=True)
            db_patterns = serializers.ListField(help_text=_("匹配DB列表"), child=serializers.CharField())
            ignore_dbs = serializers.ListField(help_text=_("忽略DB列表"), child=serializers.CharField())
            table_patterns = serializers.ListField(help_text=_("匹配Table列表"), child=serializers.CharField())
            ignore_tables = serializers.ListField(help_text=_("忽略Table列表"), child=serializers.CharField())

        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        checksum_scope = serializers.ChoiceField(help_text=_("校验范围"), choices=TendbChecksumScope.get_choices())
        backup_infos = serializers.ListSerializer(help_text=_("备份信息"), child=BackupInfoSerializer())

    data_repair = DataRepairSerializer(help_text=_("数据修复信息"))
    runtime_hour = serializers.IntegerField(help_text=_("超时时间"))
    timing = serializers.CharField(help_text=_("定时触发时间"))
    infos = serializers.ListField(help_text=_("全备信息列表"), child=ChecksumDataInfoSerializer())
    is_sync_non_innodb = serializers.BooleanField(help_text=_("非innodb表是否修复"), required=False, default=False)

    def validate(self, attrs):
        # super().validate(attrs)
        return attrs


class TendbChecksumParamBuilder(MySQLChecksumFlowParamBuilder):
    controller = SpiderController.spider_checksum

    def _get_backup_table_info(self, backup_info):
        return {
            "db_patterns": backup_info["db_patterns"],
            "ignore_dbs": backup_info["ignore_dbs"],
            "table_patterns": backup_info["table_patterns"],
            "ignore_tables": backup_info["ignore_tables"],
        }

    def _get_instance_related_info(self, inst):
        return {
            "id": inst.id,
            "ip": inst.machine.ip,
            "port": inst.port,
            "instance_inner_role": inst.instance_inner_role,
        }

    def fetch_cluster_shard_infos(self, cluster, backup_table_info):
        storage_set = TenDBClusterStorageSet.objects.select_related("storage_instance_tuple").filter(cluster=cluster)
        shard_infos: List[Dict[str, Any]] = []
        for shard in storage_set:
            # 排除spider集群迁移的情况(这个放到具体场景下做)。正常checksum提单，一个分片只有一主一从
            master = self._get_instance_related_info(shard.storage_instance_tuple.ejector)
            slave = self._get_instance_related_info(shard.storage_instance_tuple.receiver)
            shard_infos.append({"shard_id": shard.shard_id, "master": master, "slaves": [slave], **backup_table_info})

        return shard_infos

    def fetch_instance_shard_infos(self, cluster, master, backup_table_info):
        master_inst = StorageInstance.find_insts_by_addresses([master]).first()
        inst_tuple = master_inst.as_ejector.first()
        master_info = self._get_instance_related_info(master_inst)
        slave_info = self._get_instance_related_info(inst_tuple.receiver)

        shard_info = {
            "shard_id": inst_tuple.tendbclusterstorageset.shard_id,
            "master": master_info,
            "slaves": [slave_info],
            **backup_table_info,
        }

        return shard_info

    def format_ticket_data(self):
        cluster_ids = [info["cluster_id"] for info in self.ticket_data["infos"]]
        cluster_id__cluster_map = {cluster.id: cluster for cluster in Cluster.objects.filter(id__in=cluster_ids)}
        for info in self.ticket_data["infos"]:
            cluster = cluster_id__cluster_map[info["cluster_id"]]

            # 如果校验范围为全库，则查询所有的分片信息。 否则根据实例查询对应分片信息
            if info["checksum_scope"] == TendbChecksumScope.ALL:
                backup_table_info = self._get_backup_table_info(info["backup_infos"][0])
                shard_infos = self.fetch_cluster_shard_infos(cluster, backup_table_info)
            else:
                shard_infos: List[Dict[str, Any]] = []
                for backup_info in info["backup_infos"]:
                    backup_table_info = self._get_backup_table_info(backup_info)
                    sub_shard_info = self.fetch_instance_shard_infos(cluster, backup_info["master"], backup_table_info)
                    shard_infos.append(sub_shard_info)

            # 填充校验的分片信息，填充时区，域名和云区域
            info["shards"] = shard_infos
            info["time_zone"] = cluster.time_zone
            info["immute_domain"] = cluster.immute_domain
            info["bk_cloud_id"] = cluster.bk_cloud_id

    def make_repair_data(self, data_repair_name):
        """构造数据修复的数据"""

        # 获取每个实例的数据校验结果
        consistent_list = self.ticket_data["is_consistent_list"]
        slave_address_list = list(consistent_list.keys())
        slaves = StorageInstance.find_insts_by_addresses(addresses=slave_address_list)
        data_repair_infos = [
            {
                "cluster_id": slave.cluster.first().id,
                "master": self._get_instance_related_info(slave.as_receiver.first().ejector),
                "slaves": [
                    {**self._get_instance_related_info(slave), "is_consistent": consistent_list[slave.ip_port]}
                ],
            }
            for slave in slaves
        ]

        # 获取数据修复的flow
        table_sync_flow = Flow.objects.get(ticket=self.ticket, details__controller_info__func_name=data_repair_name)

        # 更新校验表和触发类型
        table_sync_flow.details["ticket_data"].update(
            checksum_table=self.ticket_data["checksum_table"],
            trigger_type=MySQLDataRepairTriggerMode.MANUAL.value,
            infos=data_repair_infos,
        )
        table_sync_flow.save(update_fields=["details"])

    def post_callback(self):
        """根据数据校验的结果，填充上下文信息给数据修复"""
        if self.skip_data_repair(MySQLController.mysql_pt_table_sync_scene.__name__, TicketType.TENDBCLUSTER_CHECKSUM):
            return

        self.make_repair_data(MySQLController.mysql_pt_table_sync_scene.__name__)


class TendbChecksumPauseParamBuilder(builders.PauseParamBuilder):
    """TendbCluster 数据修复人工确认执行的单据参数"""

    def format(self):
        self.params["pause_type"] = TicketType.TENDBCLUSTER_CHECKSUM


class TendbDataRepairFlowParamBuilder(MySQLDataRepairFlowParamBuilder):
    """TendbCluster 数据修复执行的单据参数"""

    pass


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_CHECKSUM)
class TendbChecksumFlowBuilder(MySQLChecksumFlowBuilder):
    group = DBType.TenDBCluster.value
    serializer = TendbChecksumDetailSerializer
    # 流程构造类
    checksum_flow_builder = TendbChecksumParamBuilder
    pause_flow_builder = TendbChecksumPauseParamBuilder
    data_repair_flow_builder = TendbDataRepairFlowParamBuilder

    def patch_ticket_detail(self):
        pass

    def custom_ticket_flows(self):
        return super().custom_ticket_flows()
