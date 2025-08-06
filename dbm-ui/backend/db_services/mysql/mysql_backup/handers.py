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
import os
from datetime import datetime, timedelta
from typing import Any, Dict

from django.db.models import Q
from django.forms.models import model_to_dict
from django.utils import timezone
from django.utils.translation import ugettext as _

from backend.components import DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.models.cluster import Cluster
from backend.db_meta.models.mysql_backup_result import MysqlBackupResult
from backend.db_services.mysql.mysql_backup.constants import BACKUP_FILE_DEADLINE_DAYS
from backend.utils.time import compare_time

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
        backup_id: str = None,
    ):
        """
        @param cluster_id: 集群ID
        @param is_full_backup: 是否过滤为全备的记录
        @param check_instance_exist: 是否检查实例是否存在当前集群
        @param deadlines_days:检查获取截止时间为n天前
        @param backup_id: 指定backup_id,
        """
        self.cluster = Cluster.objects.get(id=cluster_id)
        # 是否为全备份
        self.is_full_backup = is_full_backup
        # 检查实例是否在
        self.check_instance_exist = check_instance_exist
        # 在指定backup_id情况下，其他条件失效
        self.backup_id = backup_id
        # 查询是否有时间限制
        self.deadlines_days = deadlines_days
        storages = self.cluster.storageinstance_set.all()
        self.instance_ips = [s.machine.ip for s in storages]
        self.instances = [s.ip_port for s in storages]

    @staticmethod
    def _backup_info_format(backup_info: dict) -> Dict[str, Any]:
        """
        备份信息格式化，兼容从es获取的备份信息
        @param backup_info:一条备份记录
        @return: 返回格式化后的备份信息
        """
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
        获取指定集群的远程备份信息，根据备份时间排序
        @param latest_time: 备份最迟时间
        @return: 返回远程备份记录的列表
        """
        conditions = Q(cluster_id=self.cluster.id)
        if self.backup_id is not None and self.backup_id != "":
            logger.info(_("指定了backup_id {} 查询,其他条件失效".format(self.backup_id)))
            conditions = Q(backup_id=self.backup_id)
        else:
            if self.is_full_backup:
                # spider dbctl 节点只是备份权限。
                logger.info(_("指定查询全备，spider_master/TDBCTL 除外"))
                conditions &= Q(is_full_backup=self.is_full_backup) | Q(mysql_role__in=["spider_master", "TDBCTL"])

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
            logger.error("{} has no backup info".format(self.cluster.id))
            return None
        backup_info_dist = []
        for backup_info in backup_infos:
            backup_info.backup_consistent_time = backup_info.backup_consistent_time.strftime("%Y-%m-%dT%H:%M:%S%z")
            backup_info.backup_begin_time = backup_info.backup_begin_time.strftime("%Y-%m-%dT%H:%M:%S%z")
            backup_info.backup_end_time = backup_info.backup_end_time.strftime("%Y-%m-%dT%H:%M:%S%z")
            backup_info_dict = model_to_dict(backup_info)
            backup_info_dist.append(self._backup_info_format(backup_info_dict))

        return backup_info_dist

    def get_local_backup_infos(self, instances: list = None, latest_time: datetime = None, limit: str = "") -> list:
        """
        获取指定集群本地备份信息
        @param instances: 实例列表 ip:port
        @param latest_time: 最迟时间
        @param limit: 限制记录数
        @return: 返回本地备份记录的列表
        """
        cmds = """select backup_id, mysql_role, shard_value, backup_type, cluster_id, cluster_address,
        backup_host, backup_port,server_id, bill_id, bk_biz_id, mysql_version, data_schema_grant, is_full_backup,
        backup_status, backup_meta_file, binlog_info, file_list, extra_fields, backup_config_file,
        DATE_FORMAT(CONVERT_TZ(backup_begin_time,@@time_zone,"+00:00"),'%Y-%m-%dT%H:%i:%s+0000') as backup_begin_time,
        DATE_FORMAT(CONVERT_TZ(backup_end_time,@@time_zone,"+00:00"),'%Y-%m-%dT%H:%i:%s+0000')as backup_end_time,
        DATE_FORMAT(CONVERT_TZ(backup_consistent_time,@@time_zone,"+00:00"),'%Y-%m-%dT%H:%i:%s+0000') as backup_consistent_time
        from infodba_schema.local_backup_report
        where server_id=@@server_id {condition} order by backup_consistent_time desc {limit}"""

        conditions = f"and cluster_id={self.cluster.id}"
        if self.backup_id is not None and self.backup_id != "":
            logger.info(_("指定了backup_id {} 查询,其他条件失效".format(self.backup_id)))
            conditions = f" {conditions} and backup_id='{self.backup_id}'"
        else:
            if self.is_full_backup:
                # spider dbctl 节点只是备份权限。
                logger.info(_("指定查询全备，spider_master/TDBCTL 除外"))
                conditions = f" {conditions} and (is_full_backup=1 or mysql_role in ('spider_master', 'TDBCTL')) "
            # if self.check_instance_exist:
            #     server_id=@@server_id 已经检查
            if self.deadlines_days > 0:
                logger.info(_("指定备份最小时间 {} 天前").format(self.deadlines_days))
                # rollback_time = datetime.now(timezone.utc)
                begin_time = datetime.now(timezone.utc) - timedelta(days=self.deadlines_days)
                begin_time = begin_time.astimezone(timezone.utc).isoformat()
                conditions = (
                    f" {conditions} and backup_consistent_time >= CONVERT_TZ('{begin_time}',@@time_zone,'+00:00') "
                )

            if latest_time is not None:
                logger.info(_("指定备份最迟时间 {} ").format(latest_time))
                latest_time = latest_time.astimezone(timezone.utc).isoformat()
                conditions = (
                    f" {conditions} and backup_consistent_time <= CONVERT_TZ('{latest_time}',@@time_zone,'+00:00') "
                )
        query_cmds = cmds.format(condition=conditions, limit=limit)
        logger.info(query_cmds)
        backup_infos = []
        this_instances = instances
        if instances is None or len(instances) == 0:
            this_instances = copy.deepcopy(self.instances)
        for addr in this_instances:
            res = DRSApi.rpc(
                {
                    "addresses": [addr],
                    "cmds": [query_cmds],
                    "force": False,
                    "bk_cloud_id": self.cluster.bk_cloud_id,
                }
            )
            if res[0]["error_msg"]:
                logging.error("{} get backup info error {}".format(addr, res[0]["error_msg"]))
                continue
            if (
                isinstance(res[0]["cmd_results"][0]["table_data"], list)
                and len(res[0]["cmd_results"][0]["table_data"]) > 0
            ):
                backup_tmps = res[0]["cmd_results"][0]["table_data"]
                ip, port = addr.split(IP_PORT_DIVIDER)
                backup_tmps = [{"instance_ip": ip, "instance_port": port, **info} for info in backup_tmps]
                backup_infos.extend(backup_tmps)
        if backup_infos is None or len(backup_infos) == 0:
            logger.error("{} has no backup info".format(self.cluster.id))
            return None
        backup_info_dict = []
        for backup_info in backup_infos:
            backup_info["backup_dir"] = os.path.dirname(backup_info["backup_meta_file"])
            backup_info_dict.append(self._backup_info_format(backup_info))
        return backup_info_dict

    def get_tendb_latest_backup_info(self, latest_time: datetime = None) -> Dict[str, Any]:
        """
        tendbHa 获取指定集群的最近一份远程备份
        @param latest_time: 查询备份最迟时间
        @return: 返回一条远程备份记录
        """
        backup_infos = self.get_backup_infos(latest_time)
        if backup_infos is None:
            return None
        return backup_infos[0]

    def get_tendb_priv_backup_info(self, latest_time: datetime = None) -> Dict[str, Any]:
        """
        tendbHa 获取指定集群所有ip节点的最近一份远程权限备份。
        @param latest_time: 查询备份最迟时间
        @return: 返回集群的各个数据节点的权限备份记录
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
        tendbCluster 查询当前集群集群各个remote节点点的最新一份远程备份
        @param latest_time: 查询备份最迟时间
        @param shard_list: 分片列表，如果为空，则查询所有分片
        @return: 返回集群的各个数据节点的备份记录
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
        """
        tendbCluster 查询当前集群集群各个remote节点点的最新一份远程备份,且要求所有的分片backup_id是一致的。
        @param latest_time: 查询备份最迟时间
        @param limit_one: 是否限制只返回一条备份记录
        @return: 返回集群的各个数据节点的备份记录，且backup_id必须一致
        """
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

    def get_local_latest_backup_info(self, instances: list = None, latest_time: datetime = None):
        """
        查询tendbHa/tendbCluster集群指定多个实例列表下的最新一个本地备份
        @param instances:实例列表 ip:port
        @param latest_time: 备份最大时间，这里的时间需要转换成UTC时间，因为sql语句中是转换为0时区进行比较的
        @return: 返回一条本地备份记录
        """
        backup_infos = self.get_local_backup_infos(instances, latest_time, "limit 1")
        backup_time = "1999-01-01T11:11:11+08:00"
        if len(backup_infos) > 0:
            max_backup = backup_infos[0]
            for backup in backup_infos:
                if compare_time(backup["backup_consistent_time"], backup_time):
                    backup_time = backup["backup_consistent_time"]
                    max_backup = backup
            logger.info(_("使用的备份信息: {}".format(max_backup)))
            return max_backup
        else:
            return None
