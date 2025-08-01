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
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict

from django.db.models import Q
from django.forms.models import model_to_dict
from django.utils import timezone
from django.utils.translation import ugettext as _

from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.models.cluster import Cluster
from backend.db_meta.models.mysql_backup_result import MysqlBackupResult
from backend.db_services.mysql.mysql_backup.constants import BACKUP_FILE_DEADLINE_DAYS

logger = logging.getLogger("flow")


class MySQLBackupHandler:
    """
    mysql 备份文件查询相关接口
    """

    def __init__(
        self,
        cluster_id: int,
        is_full_backup=False,
        check_instance_exist=False,
        deadlines_days=BACKUP_FILE_DEADLINE_DAYS,
    ):
        """
        @param cluster_id: 集群ID
        @param is_full_backup: 是否过滤为全备的记录
        @param check_instance_exist: 是否检查实例是否存在当前集群
        @param deadlines_days:检查获取截止时间为n天前
        """
        self.cluster = Cluster.objects.get(id=cluster_id)
        # 是否为全备份
        self.is_full_backup = is_full_backup
        # 检查实例是否在
        self.check_instance_exist = check_instance_exist
        # 查询是否有时间限制
        self.deadlines_days = deadlines_days
        storages = self.cluster.storageinstance_set.all()
        self.instance_ips = [s.machine.ip for s in storages]

    @staticmethod
    def _backup_info_format(backup_info_set) -> Dict[str, Any]:
        """
        备份信息格式化，兼容从es获取的备份信息
        """
        backup_info = model_to_dict(backup_info_set)
        backup_info["binlog_info"] = json.loads(backup_info["binlog_info"])
        backup_info["file_list"] = json.loads(backup_info["file_list"])
        backup_info["extra_fields"] = json.loads(backup_info["extra_fields"])
        backup_info["consistent_backup_time"] = backup_info["backup_consistent_time"]
        backup_info["backup_time"] = backup_info["backup_consistent_time"]
        backup_info["bk_cloud_id"] = backup_info["extra_fields"]["bk_cloud_id"]
        backup_info["encrypt_enable"] = backup_info["extra_fields"]["encrypt_enable"]
        backup_info["time_zone"] = backup_info["extra_fields"]["time_zone"]
        backup_info["backup_charset"] = backup_info["extra_fields"]["backup_charset"]
        backup_info["backup_tool"] = backup_info["extra_fields"]["backup_tool"]
        backup_info["file_list_details"] = backup_info["file_list"]
        task_ids = []
        for file in backup_info["file_list_details"]:
            task_ids.append(file["task_id"])
            if file["file_type"] == "priv":
                file["mysql_role"] = backup_info["mysql_role"]
                file["backup_consistent_time"] = backup_info["backup_consistent_time"]
                backup_info["priv"] = file
            if file["file_type"] == "index":
                backup_info["index"] = file
        backup_info["task_ids"] = task_ids
        return backup_info

    def get_backup_infos(self, latest_time: datetime = None) -> list:
        """
        获取指定集群的备份信息，根据备份时间排序
        """
        conditions = Q(cluster_id=self.cluster.id)
        if self.is_full_backup:
            # spider dbctl 节点只是备份权限。
            logger.info(_("指定查询全备，spider_master/TDBCTL 除外"))
            conditions &= Q(is_full_backup=self.is_full_backup) | (
                Q(mysql_role__in=["spider_master", "TDBCTL"]) & Q(data_schema_grant="schema,grant")
            )
        if self.check_instance_exist:
            logger.info(_("指定备份实例的ip必须在集群ip里"))
            conditions &= Q(backup_host__in=self.instance_ips)
        if self.deadlines_days > 0:
            logger.info(_("指定备份最小时间 {} 天前").format(self.deadlines_days))
            # rollback_time = datetime.now(timezone.utc)
            begin_time = datetime.now(timezone.utc) - timedelta(days=self.deadlines_days)
            conditions &= Q(backup_consistent_time__gte=begin_time)
        if latest_time is not None:
            logger.info(_("指定备份最迟时间 {} ").format(latest_time))
            # 非空说明截止时间有指定
            conditions &= Q(backup_consistent_time__lte=latest_time)

        backup_infos = MysqlBackupResult.objects.filter(conditions).order_by("-backup_consistent_time")
        if backup_infos is None or len(backup_infos) == 0:
            return None
        backup_info_dist = []
        for index, backup_info in enumerate(backup_infos):
            backup_info_dist.append(self._backup_info_format(backup_info))
        return backup_info_dist

    def get_tendb_latest_backup_info(self, latest_time: datetime = None) -> Dict[str, Any]:
        """
        tendbHa 获取指定集群的最近一份备份
        """
        backup_infos = self.get_backup_infos(latest_time)
        if backup_infos is None:
            return None
        return backup_infos[0]

    def get_tendb_priv_backup_info(self, latest_time: datetime = None) -> Dict[str, Any]:
        """
        tendbHa 获取指定集群所有ip节点的最近一份权限备份。
        """
        # 查询当前集群集群实例下各个节点的最新一份权限备份。
        backup_infos = self.get_backup_infos(latest_time)
        if backup_infos is None:
            return None
        backup_priv_info = {
            "cluster_id": self.cluster.id,
            "cluster_address": self.cluster.immute_domain,
            "bk_biz_id": self.cluster.bk_biz_id,
            "bk_cloud_id": self.cluster.bk_cloud_id,
            "file_list": {},
            "task_ids": [],
        }
        instance_ips = copy.deepcopy(self.instance_ips)
        for backup_info in backup_infos:
            if backup_info["backup_host"] in instance_ips:
                instance_ips.remove(backup_info["backup_host"])
                key_name = "{}{}{}".format(backup_info["backup_host"], IP_PORT_DIVIDER, backup_info["backup_port"])
                backup_priv_info["file_list"][key_name] = backup_info["priv"]
                backup_priv_info["task_ids"].append(backup_info["priv"]["task_id"])
        if len(backup_priv_info["file_list"]) == 0:
            return None
        if len(instance_ips) > 0:
            logger.info("{} only part of storage instance get privilege file".format(self.cluster.id))
        return backup_priv_info

    def get_spider_latest_backup_info(self, latest_time: datetime = None, shard_list: list = None) -> Dict[str, Any]:
        """
        tendbCluster 查询当前集群集群各个remote节点点的最新一份权限备份
        """
        backup_infos = self.get_backup_infos(latest_time)
        if backup_infos is None:
            return None
        cluster_shards = self.cluster.tendbclusterstorageset_set.all()
        if shard_list is None:
            shard_list = [shard.shard_id for shard in cluster_shards]
        logger.info("get backup shards {}".format(shard_list))
        cluster_backup_info = {
            "cluster_id": self.cluster.id,
            "bk_cloud_id": self.cluster.bk_cloud_id,
            "bk_biz_id": self.cluster.bk_biz_id,
            "cluster_address": self.cluster.immute_domain,
            "spider_node": {},
            "tdbctl_node": {},
            "remote_node": {},
        }
        for backup_info in backup_infos:
            if backup_info["shard_value"] in shard_list and backup_info["mysql_role"] in ["master", "slave"]:
                shard_list.remove(backup_info["shard_value"])
                cluster_backup_info["remote_node"][str(backup_info["shard_value"])] = backup_info
        if len(shard_list) != 0:
            logger.info("get backup shards failed {}".format(shard_list))
            return None
        return cluster_backup_info

    def get_spider_rollback_backup_info(self, latest_time: datetime = None, limit_one: bool = False) -> Dict[str, Any]:
        backup_infos = self.get_backup_infos(latest_time)
        if backup_infos is None:
            return None
        cluster_shards = self.cluster.tendbclusterstorageset_set.all()
        shard_list = [shard.shard_id for shard in cluster_shards]
        # shard_list=[1,2,3,0]
        cluster_backup_info = {
            "cluster_id": self.cluster.id,
            "bk_cloud_id": self.cluster.bk_cloud_id,
            "bk_biz_id": self.cluster.bk_biz_id,
            "cluster_address": self.cluster.immute_domain,
            "spider_node": {},
            "tdbctl_node": {},
            "remote_node": {},
        }
        cluster_backup_info_map = {}
        cluster_backup_id_list = []
        for backup_info in backup_infos:
            if backup_info["backup_id"] not in cluster_backup_info_map:
                cluster_backup_id_list.append(backup_info["backup_id"])
                cluster_backup_info_map[backup_info["backup_id"]] = copy.deepcopy(cluster_backup_info)
                cluster_backup_info_map[backup_info["backup_id"]]["backup_consistent_time"] = backup_info[
                    "backup_consistent_time"
                ]
                cluster_backup_info_map[backup_info["backup_id"]]["shard_list"] = copy.deepcopy(shard_list)

            if backup_info["shard_value"] in cluster_backup_info_map[backup_info["backup_id"]][
                "shard_list"
            ] and backup_info["mysql_role"] in ["master", "slave"]:
                cluster_backup_info_map[backup_info["backup_id"]]["shard_list"].remove(backup_info["shard_value"])
                cluster_backup_info_map[backup_info["backup_id"]]["remote_node"][
                    str(backup_info["shard_value"])
                ] = backup_info
            elif (
                len(cluster_backup_info_map[backup_info["backup_id"]]["spider_node"]) == 0
                and backup_info["mysql_role"] == "spider_master"
            ):
                cluster_backup_info_map[backup_info["backup_id"]]["spider_node"] = backup_info
            elif (
                len(cluster_backup_info_map[backup_info["backup_id"]]["tdbctl_node"]) == 0
                and backup_info["mysql_role"] == "TDBCTL"
            ):
                cluster_backup_info_map[backup_info["backup_id"]]["tdbctl_node"] = backup_info
        # 检查cluster_backup_info_map是否完整
        cluster_backup_info_map_tmp = copy.deepcopy(cluster_backup_info_map)
        for backup_id, backup_map in cluster_backup_info_map_tmp.items():
            if (
                len(backup_map["shard_list"]) > 0
                or len(backup_map["tdbctl_node"]) == 0
                or len(backup_map["spider_node"]) == 0
            ):
                logger.info("{} backup_id has not all node info ", backup_id)
                cluster_backup_id_list.remove(backup_id)
                cluster_backup_info_map.pop(backup_id)
        if len(cluster_backup_info_map) == 0:
            logger.info("{} cluster has not a all node full backup", self.cluster.id)
            return None
        if limit_one:
            return cluster_backup_info_map[cluster_backup_id_list[0]]
        return cluster_backup_info_map
