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
import copy
from typing import Any, Dict, List

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_meta.models import Cluster, StorageInstance, TenDBClusterStorageSet
from backend.flow.engine.controller.spider import SpiderController
from backend.ticket import builders
from backend.ticket.builders.common.base import HostInfoSerializer
from backend.ticket.builders.common.constants import MySQLChecksumTicketMode, TendbChecksumScope
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder, TendbBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class TendbChecksumDetailSerializer(TendbBaseOperateDetailSerializer):
    class DataRepairSerializer(serializers.Serializer):
        is_repair = serializers.BooleanField(help_text=_("是否修复"))
        mode = serializers.ChoiceField(help_text=_("数据校验后修复执行类型"), choices=MySQLChecksumTicketMode.get_choices())

    class ChecksumDataInfoSerializer(serializers.Serializer):
        class BackupInfoSerializer(serializers.Serializer):
            master = serializers.CharField(help_text=_("主库IP"))
            slave = serializers.CharField(help_text=_("从库IP"))
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


class TendbChecksumParamBuilder(builders.FlowParamBuilder):
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

    def fetch_machine_shard_infos(self, cluster, master_machine, backup_table_info):
        masters = StorageInstance.objects.prefetch_related("as_ejector").filter(
            cluster=cluster, machine__ip=master_machine
        )
        shard_infos: List[Dict[str, Any]] = []
        for master in masters:
            # 获取master关联的storage_tuple，并查询对应的slave和shard_id
            inst_tuple = master.as_ejector.first()
            master_info = self._get_instance_related_info(master)
            slave_info = self._get_instance_related_info(inst_tuple.receiver)
            shard_infos.append(
                {
                    "shard_id": inst_tuple.tendbclusterstorageset.shard_id,
                    "master": master_info,
                    "slaves": [slave_info],
                    **backup_table_info,
                }
            )

        return shard_infos

    def format_ticket_data(self):
        cluster_ids = [info["cluster_id"] for info in self.ticket_data["infos"]]
        cluster_id__cluster_map = {cluster.id: cluster for cluster in Cluster.objects.filter(id__in=cluster_ids)}
        for info in self.ticket_data["infos"]:
            cluster = cluster_id__cluster_map[info["cluster_id"]]

            # 如果校验范围为全库，则查询所有的分片信息。 否则根据machine查询对应分片信息
            if info["checksum_scope"] == TendbChecksumScope.ALL:
                backup_table_info = self._get_backup_table_info(info["backup_infos"][0])
                shard_infos = self.fetch_cluster_shard_infos(cluster, backup_table_info)
            else:
                shard_infos: List[Dict[str, Any]] = []
                for backup_info in info["backup_infos"]:
                    backup_table_info = self._get_backup_table_info(backup_info)
                    sub_shard_infos = self.fetch_machine_shard_infos(cluster, backup_info["master"], backup_table_info)
                    shard_infos.extend(sub_shard_infos)

            # 填充校验的分片信息，填充时区，域名和云区域
            info["shards"] = shard_infos
            info["time_zone"] = cluster.time_zone
            info["immute_domain"] = cluster.immute_domain
            info["bk_cloud_id"] = cluster.bk_cloud_id


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_CHECKSUM)
class TendbChecksumFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TendbChecksumDetailSerializer
    inner_flow_builder = TendbChecksumParamBuilder
    inner_flow_name = _("TendbCluster 数据校验修复")

    @property
    def need_itsm(self):
        return False
