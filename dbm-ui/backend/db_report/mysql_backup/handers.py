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
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from django.db.models import Q
from django.forms.models import model_to_dict
from django.utils.translation import gettext as _

from backend.components import DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterType, InstanceInnerRole, TenDBClusterSpiderRole
from backend.db_meta.models.cluster import Cluster
from backend.db_report.models.mysql_backup_result import MysqlBackupResult
from backend.db_report.models.mysql_binlog_backup_result import MysqlBinlogResult
from backend.db_report.mysql_backup.constants import BACKUP_FILE_DEADLINE_DAYS
from backend.ticket.builders.common.constants import MySQLBackupSource
from backend.utils.time import compare_time, str2datetime

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
        shard_id: int = None,
        filter_ips: list[str] = None,
        backup_method: list[str] = None,
        is_standby: bool = True,
        backup_source: str = MySQLBackupSource.REMOTE.value,
    ):
        """
        @param cluster_id: 集群ID
        @param is_full_backup: 是否过滤为全备的记录
        @param check_instance_exist: 是否检查实例是否存在当前集群
        @param deadlines_days:检查获取截止时间为n天前
        @param backup_id: 指定backup_id,
        @param shard_id: 分片ID。只有tendbCluster有。本地备份时不需要指定
        @param filter_ips: 过滤ip列表。在指定本地备份时，filster_ips即指定在哪些实例查询
        @param backup_method: 备份方法
        @param is_standby: 是否为备机
        @param backup_source: 是否从本地备份获取
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
        self.port = storages[0].port
        self.shard_id = shard_id
        self.filter_ips = filter_ips
        self.backup_method = backup_method
        self.is_standby = is_standby
        self.backup_source = backup_source
        self.query = ""
        self.errmsg = ""

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
        # 从 extra_fields 挪出来的字段
        backup_info["database_list"] = backup_info["extra_fields"].get("database_list", [])
        backup_info["total_filesize"] = backup_info["extra_fields"].get("total_filesize", 0)
        backup_info["file_retention_tag"] = backup_info["extra_fields"].get("file_retention_tag", "")
        backup_info["backup_tool"] = backup_info["extra_fields"].get("backup_tool", "")
        backup_info["storage_engine"] = backup_info["extra_fields"]["storage_engine"]
        backup_info["time_zone"] = backup_info["extra_fields"]["time_zone"]
        backup_info["backup_charset"] = backup_info["extra_fields"]["backup_charset"]
        backup_info["bk_cloud_id"] = backup_info["extra_fields"]["bk_cloud_id"]

        task_ids = []
        local_files = []
        for file in backup_info["file_list_details"]:
            task_ids.append(file["task_id"])
            local_files.append(
                os.path.join(backup_info["extra_fields"].get("original_backup_dir", ""), file["file_name"])
            )
            if file["file_type"] == "priv":
                file["mysql_role"] = backup_info["mysql_role"]
                file["backup_consistent_time"] = backup_info["backup_consistent_time"]
                backup_info["priv"] = file
            if file["file_type"] == "index":
                backup_info["index"] = file
        backup_info["task_ids"] = task_ids
        backup_info["local_files"] = local_files
        return backup_info

    def get_backup_infos(self, latest_time: datetime = None) -> list:
        """
        获取指定集群的远程备份信息，根据备份时间排序
        @param latest_time: 备份最迟时间
        @return: 返回远程备份记录的列表
        """
        conditions = Q(cluster_id=self.cluster.id, cluster_address=self.cluster.immute_domain)
        if self.backup_id is not None and self.backup_id != "":
            logger.info(_("指定了backup_id {} 查询,其他条件失效".format(self.backup_id)))
            conditions &= Q(backup_id=self.backup_id)
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
                begin_time = datetime.now().astimezone(timezone.utc) - timedelta(days=self.deadlines_days)
                conditions &= Q(backup_consistent_time__gte=begin_time)
            if latest_time is not None:
                latest_time = latest_time.astimezone(timezone.utc)
                logger.info(_("指定备份最迟时间 {} ").format(latest_time))
                # 非空说明截止时间有指定
                conditions &= Q(backup_consistent_time__lte=latest_time)
            if self.shard_id is not None:
                logger.info(_("指定shard_value {} 查询").format(self.shard_id))
                conditions &= Q(
                    shard_value=self.shard_id,
                    mysql_role__in=[InstanceInnerRole.MASTER.value, InstanceInnerRole.SLAVE.value],
                )
            if self.filter_ips is not None and len(self.filter_ips) > 0:
                logger.info(_("指定备份实例的ip必须在指定ip里 {}".format(self.filter_ips)))
                conditions &= Q(backup_host__in=self.filter_ips)

            if self.backup_method is not None and len(self.backup_method) > 0:
                logger.info(_("指定备份方法 {} 查询").format(self.backup_method))
                conditions &= Q(backup_method__in=self.backup_method)
            # 当前必须用is_standby备份来恢复数据。
            if self.is_standby:
                logger.info(_("指定查询必须从is_standby实例查询。spider_master/TDBCTL/orphan除外"))
                conditions &= Q(is_standby="yes") | Q(mysql_role__in=["spider_master", "TDBCTL", "orphan"])

        backup_infos = MysqlBackupResult.objects.filter(conditions).order_by("-backup_consistent_time")
        self.query = str(backup_infos.query)
        logger.info(self.query)
        if backup_infos is None or len(backup_infos) == 0:
            self.errmsg = _("集群id {} 没有指定过滤条件的备份信息").format(self.cluster.id)
            logger.error(self.errmsg)
            return None
        backup_info_dist = []
        for backup_info in backup_infos:
            backup_info.backup_consistent_time = backup_info.backup_consistent_time.isoformat()
            backup_info.backup_begin_time = backup_info.backup_begin_time.isoformat()
            backup_info.backup_end_time = backup_info.backup_end_time.isoformat()
            backup_info_dict = model_to_dict(backup_info)
            backup_info_dict["backup_source"] = MySQLBackupSource.REMOTE.value
            backup_info_dist.append(self._backup_info_format(backup_info_dict))

        return backup_info_dist

    def get_tendb_latest_backup_info(self, latest_time: datetime = None) -> Dict[str, Any]:
        """
        tendbHa 获取指定集群的最近一份远程备份
        @param latest_time: 查询备份最迟时间
        @return: 返回一条远程备份记录
        """
        if self.backup_source == MySQLBackupSource.LOCAL:
            return self.get_local_latest_backup_info(latest_time)
        backup_infos = self.get_backup_infos(latest_time)
        if backup_infos is None:
            return None
        logger.info(_("获取到的backup_id {} ").format(backup_infos[0]["backup_id"]))
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
            "backup_ids": [],
            "priv_files": [],
        }
        instance_ips = copy.deepcopy(self.instance_ips)
        for backup_info in backup_infos:
            if backup_info["backup_host"] in instance_ips:
                instance_ips.remove(backup_info["backup_host"])
                key_name = "{}{}{}".format(backup_info["backup_host"], IP_PORT_DIVIDER, backup_info["backup_port"])
                backup_priv_info["file_list"][key_name] = backup_info["priv"]
                backup_priv_info["task_ids"].append(backup_info["priv"]["task_id"])
                backup_priv_info["priv_files"].append(os.path.basename(backup_info["priv"]["file_name"]))
                backup_priv_info["backup_ids"].append(backup_info["backup_id"])
        if len(backup_priv_info["file_list"]) == 0:
            self.errmsg = _("集群id {} 查询不到指定过滤条件的权限文件").format(self.cluster.id)
            logger.error(self.errmsg)
            return None
        if len(instance_ips) > 0:
            logger.info("{} only part of storage instance get privilege file".format(self.cluster.id))
        return backup_priv_info

    def get_spider_rollback_backup_info(self, latest_time: datetime = None, limit_one: bool = False) -> Dict[str, Any]:
        """
        tendbCluster 查询当前集群集群各个remote节点点的最新一份远程备份,且要求所有的分片backup_id是一致的。
        @param latest_time: 查询备份最迟时间
        @param limit_one: 是否限制只返回一条备份记录
        @return: 返回集群的各个数据节点的备份记录，且backup_id必须一致
        """
        if self.backup_source == MySQLBackupSource.LOCAL:
            backup_infos = self.get_local_backup_infos(latest_time=latest_time, include_proxy=True)
        else:
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
            #  判断影响取 remote 并集? _xxx
            "database_list": [],
            "backup_method_list": [],
            "backup_tool_list": [],
            "backup_type_list": [],
            "total_filesize": 0,
            #  如果有多个就忽略
            "backup_method": "",
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
                cluster_backup_info_map[backup_info["backup_id"]]["backup_id"] = backup_info["backup_id"]
                cluster_backup_info_map[backup_info["backup_id"]]["shard_list"] = copy.deepcopy(shard_list)

            if (
                int(backup_info["shard_value"]) in cluster_backup_info_map[backup_info["backup_id"]]["shard_list"]
                and backup_info["mysql_role"] in ["master", "slave"]
                # 此处判断data_schema_grant,避免在指定backup_id查询(不做其他条件过滤)的时候,通过这里保证shard有数据。
                and (
                    str(backup_info["data_schema_grant"]).lower() == "all"
                    or (
                        "data" in str(backup_info["data_schema_grant"]).lower()
                        and "schema" in str(backup_info["data_schema_grant"]).lower()
                    )
                )
            ):
                cluster_backup_info_map[backup_info["backup_id"]]["shard_list"].remove(int(backup_info["shard_value"]))
                cluster_backup_info_map[backup_info["backup_id"]]["backup_type_list"].append(
                    backup_info["backup_type"]
                )
                cluster_backup_info_map[backup_info["backup_id"]]["backup_tool_list"].append(
                    backup_info["extra_fields"]["backup_tool"]
                )
                cluster_backup_info_map[backup_info["backup_id"]]["backup_method_list"].append(
                    backup_info["backup_method"]
                )
                cluster_backup_info_map[backup_info["backup_id"]]["total_filesize"] += backup_info.get(
                    "extra_fields", {}
                ).get("total_filesize", 0)
                shard_database_list = backup_info["extra_fields"].get("database_list", [])
                if isinstance(shard_database_list, list):
                    for db in shard_database_list:
                        shard_str = f"_{backup_info['shard_value']}"
                        cluster_backup_info_map[backup_info["backup_id"]]["database_list"].append(
                            str(db).rstrip(shard_str)
                        )
                cluster_backup_info_map[backup_info["backup_id"]]["remote_node"][
                    int(backup_info["shard_value"])
                ] = backup_info
            elif (
                len(cluster_backup_info_map[backup_info["backup_id"]]["spider_node"]) == 0
                and backup_info["mysql_role"] == "spider_master"
            ):
                cluster_backup_info_map[backup_info["backup_id"]]["total_filesize"] += backup_info.get(
                    "extra_fields", {}
                ).get("total_filesize", 0)
                database_list = backup_info["extra_fields"].get("database_list", [])
                if isinstance(database_list, list):
                    cluster_backup_info_map[backup_info["backup_id"]]["database_list"].extend(database_list)
                cluster_backup_info_map[backup_info["backup_id"]]["spider_node"] = backup_info
            elif (
                len(cluster_backup_info_map[backup_info["backup_id"]]["tdbctl_node"]) == 0
                and backup_info["mysql_role"] == "TDBCTL"
            ):
                cluster_backup_info_map[backup_info["backup_id"]]["total_filesize"] += backup_info.get(
                    "extra_fields", {}
                ).get("total_filesize", 0)
                database_list = backup_info["extra_fields"].get("database_list", [])
                if isinstance(database_list, list):
                    cluster_backup_info_map[backup_info["backup_id"]]["database_list"].extend(database_list)
                cluster_backup_info_map[backup_info["backup_id"]]["tdbctl_node"] = backup_info
        # 检查cluster_backup_info_map是否完整
        cluster_backup_info_map_tmp = copy.deepcopy(cluster_backup_info_map)
        for backup_id, backup_map in cluster_backup_info_map_tmp.items():
            cluster_backup_info_map[backup_id]["backup_method_list"] = list(set(backup_map["backup_method_list"]))
            if len(cluster_backup_info_map[backup_id]["backup_method_list"]) > 0:
                cluster_backup_info_map[backup_id]["backup_method"] = cluster_backup_info_map[backup_id][
                    "backup_method_list"
                ][0]
            cluster_backup_info_map[backup_id]["backup_type_list"] = list(set(backup_map["backup_type_list"]))
            cluster_backup_info_map[backup_id]["backup_type"] = ",".join(
                cluster_backup_info_map[backup_id]["backup_type_list"]
            )
            cluster_backup_info_map[backup_id]["database_list"] = list(set(backup_map["database_list"]))
            cluster_backup_info_map[backup_id]["backup_tool_list"] = list(set(backup_map["backup_tool_list"]))
            cluster_backup_info_map[backup_id]["backup_tool"] = ",".join(
                cluster_backup_info_map[backup_id]["backup_tool_list"]
            )

            if (
                len(backup_map["shard_list"]) > 0
                or len(backup_map.get("tdbctl_node", {})) == 0
                or len(backup_map.get("spider_node", {})) == 0
                or len(cluster_backup_info_map[backup_id]["backup_method_list"]) != 1
            ):
                logger.info(
                    "backup_id: {} not include all nodes: shards: {} spider_node: {} tdbctl_node: {}".format(
                        backup_id,
                        backup_map["shard_list"],
                        len(backup_map.get("spider_node", {})),
                        len(backup_map.get("tdbctl_node", {})),
                    )
                )
                cluster_backup_id_list.remove(backup_id)
                cluster_backup_info_map.pop(backup_id)
        if len(cluster_backup_info_map) == 0:
            self.errmsg = _("集群id {} 查询不到一份包含所有remote/DBCTL/spider_master的备份").format(self.cluster.id)
            logger.error(self.errmsg)
            return None
        if limit_one:
            return cluster_backup_info_map[cluster_backup_id_list[0]]
        return cluster_backup_info_map

    def get_binlog_backup_infos(
        self, host: str, port: int, start_time: datetime, end_time: datetime = None, binlog_start_file: str = None
    ) -> list:
        """
        获取指定备份信息的binlog备份信息
        """
        conditions = Q(cluster_id=self.cluster.id, cluster_domain=self.cluster.immute_domain, host=host, port=port)
        # 在从库备份的时候,延迟特别严重,根据backup_consistent_time查询主库的binlog可能查询不到对应的binlog。需要根据起始binlog文件的时间来查询binlog。
        if binlog_start_file is not None:
            logger.info(_("根据起始binlog文件 {} 查询binlog".format(binlog_start_file)))
            start_file_conditions = conditions & Q(filename=binlog_start_file)
            start_binlog_list = MysqlBinlogResult.objects.filter(start_file_conditions)
            self.query = str(start_binlog_list.query)
            if start_binlog_list is not None and len(start_binlog_list) > 0:
                logger.info(_("起始binlog文件的时间是 {} ".format(start_binlog_list[0].start_time)))
                start_time = str2datetime(start_binlog_list[0].start_time)
            else:
                return []

        if end_time is None:
            end_time = datetime.now().astimezone(timezone.utc)
        start_time = start_time.astimezone(timezone.utc)
        end_time = end_time.astimezone(timezone.utc)
        conditions &= Q(start_time__gte=start_time) & Q(stop_time__lte=end_time)
        logger.info(
            _("binlog查询时间范围是: {} {}".format(start_time.astimezone().isoformat(), end_time.astimezone().isoformat()))
        )
        binlog_infos = MysqlBinlogResult.objects.filter(conditions).order_by("-start_time")
        self.query = str(binlog_infos.query)
        logger.info(self.query)
        if binlog_infos is None or len(binlog_infos) == 0:
            return []
        binlog_list = []
        for binlog_info in binlog_infos:
            binlog_info.file_mtime = binlog_info.file_mtime.isoformat()
            binlog_info.start_time = binlog_info.start_time.isoformat()
            binlog_info.stop_time = binlog_info.stop_time.isoformat()
            binlog_info_dict = model_to_dict(binlog_info)
            binlog_list.append(binlog_info_dict)
        return binlog_list

    def get_binlog_for_rollback(
        self, backup_info: dict, start_time: datetime, end_time: datetime = None, minute_range=30
    ) -> dict:
        """
        获取指定备份信息用于别分使用
        """
        backup_id = backup_info["backup_id"]
        binlog_info = backup_info["binlog_info"]
        result = {}
        if end_time is None:
            end_time = datetime.now().astimezone()
        if start_time > end_time:
            result["query_binlog_error"] = _(
                "backup_id {} 备份时间点:{} 大于 回滚时间点:{}".format(backup_id, start_time, end_time)
            )
            return result
        if minute_range > 0:
            logger.info(_("指定binlog查询时间冗余宽度 {} 分钟").format(minute_range))
            start_time = start_time - timedelta(minutes=minute_range)
            end_time = end_time + timedelta(minutes=minute_range)
        if backup_info["mysql_role"] in [InstanceInnerRole.MASTER.value, InstanceInnerRole.ORPHAN.value]:
            # 备份信息来自主节点，从 show_master_status 中获取主节点信息
            binlog_list = self.get_binlog_backup_infos(
                binlog_info["show_master_status"]["master_host"],
                binlog_info["show_master_status"]["master_port"],
                start_time,
                end_time,
            )

            if binlog_info is None or len(binlog_list) == 0:
                if binlog_list is None or len(binlog_list) == 0:
                    result["query_binlog_error"] = _("backup_id {} 原备份节点{} 查询不到binlog").format(
                        backup_id, binlog_info["show_master_status"]["master_host"]
                    )
                    return result
            result["binlog_start_file"] = binlog_info["show_master_status"]["binlog_file"]
            result["binlog_start_pos"] = binlog_info["show_master_status"]["binlog_pos"]

        else:
            if "show_slave_status" in binlog_info.keys() and binlog_info.get("show_slave_status", None) is not None:
                # 备份信息来自从节点，从 show_slave_status 中获取主节点信息
                if binlog_info["show_slave_status"].get("master_host", "") == "":
                    result["query_binlog_error"] = _("backup_id {} show slave status 没有 master_host 信息").format(
                        backup_id
                    )
                    return result
                binlog_list = self.get_binlog_backup_infos(
                    binlog_info["show_slave_status"]["master_host"],
                    binlog_info["show_slave_status"]["master_port"],
                    start_time,
                    end_time,
                    binlog_info["show_slave_status"]["binlog_file"],
                )
                if binlog_info is None or len(binlog_list) == 0:
                    if binlog_list is None or len(binlog_list) == 0:
                        result["query_binlog_error"] = _("backup_id {} 原备份节点{} 查询不到binlog").format(
                            backup_id, binlog_info["show_slave_status"]["master_host"]
                        )
                        return result
                result["binlog_start_file"] = binlog_info["show_slave_status"]["binlog_file"]
                result["binlog_start_pos"] = binlog_info["show_slave_status"]["binlog_pos"]
            else:
                result["query_binlog_error"] = _("backup_id {} 找不到 show slave status 信息").format(backup_id)
                return result
        logger.info("master binlog is:", binlog_list)
        result["binlog_task_ids"] = [i["task_id"] for i in binlog_list]
        binlog_files = [i["filename"] for i in binlog_list]
        if result["binlog_start_file"] not in binlog_files:
            result["query_binlog_error"] = _("backup_id {} 查不到起始binlog文件 {}").format(
                backup_id, result["binlog_start_file"]
            )
        # 可添加从binlog_start_file开始完后判断日志连续性...
        result["binlog_files_list"] = binlog_files
        # result["binlog_files"] = ",".join(binlog_files)
        return result

    def get_local_backup_infos(
        self, latest_time: datetime = None, limit: str = "", include_proxy: bool = False
    ) -> list[dict]:
        """
        获取指定集群本地备份信息 本地查询不需要条件 check_instance_exist shard_id filter_ips is_standby
        @param latest_time: 最迟时间
        @param limit: 限制记录数
        @param include_proxy: 是否包含spider层的备份,此参数针对生成回档任务使用
        @return: 返回本地备份记录的列表
        """
        cmds = """select r.*,
        DATE_FORMAT(CONVERT_TZ(backup_begin_time,@@time_zone,"+00:00"),'%Y-%m-%dT%H:%i:%s+00:00') as backup_begin_time,
        DATE_FORMAT(CONVERT_TZ(backup_end_time,@@time_zone,"+00:00"),'%Y-%m-%dT%H:%i:%s+00:00')as backup_end_time,
        DATE_FORMAT(CONVERT_TZ(backup_consistent_time,@@time_zone,"+00:00"),'%Y-%m-%dT%H:%i:%s+00:00')
        as backup_consistent_time
        from infodba_schema.local_backup_report r
        where 1=1 {condition} order by backup_consistent_time desc {limit}"""
        conditions = (
            f" and r.cluster_id={self.cluster.id} and r.cluster_address='{self.cluster.immute_domain}' "
            f" and backup_status!='local_removed' "
        )

        if self.backup_id is not None and self.backup_id != "":
            logger.info(_("指定了backup_id {} 查询,其他条件失效".format(self.backup_id)))
            conditions = f" {conditions} and backup_id='{self.backup_id}'"
        else:
            if self.is_full_backup:
                # spider dbctl 节点只是备份权限。
                logger.info(_("指定查询全备，spider_master/TDBCTL 除外"))
                conditions = f" {conditions} and (is_full_backup=1 or mysql_role in ('spider_master', 'TDBCTL')) "

            if self.deadlines_days > 0:
                logger.info(_("指定备份最小时间 {} 天前").format(self.deadlines_days))
                begin_time = datetime.now().astimezone(timezone.utc) - timedelta(days=self.deadlines_days)
                begin_time_str = begin_time.isoformat()
                conditions = (
                    f" {conditions} and backup_consistent_time >= CONVERT_TZ('{begin_time_str}',@@time_zone,'+00:00') "
                )

            if latest_time is not None:
                logger.info(_("指定备份最迟时间 {} ").format(latest_time))
                latest_time = latest_time.astimezone(timezone.utc)
                latest_time_str = latest_time.isoformat()
                conditions = f" {conditions} and backup_consistent_time <= CONVERT_TZ('{latest_time_str}',@@time_zone,'+00:00') "

            if self.backup_method is not None and len(self.backup_method) > 0:
                logger.info(_("指定备份方法 {} 查询").format(self.backup_method))
                backup_method_str = "','".join(self.backup_method)
                conditions = f" {conditions} and backup_method in ('{backup_method_str}') "

        backup_infos = []

        # 获取实例信息
        ins_conditions = Q()
        if self.filter_ips is not None and len(self.filter_ips) > 0:
            ins_conditions &= Q(machine__ip__in=self.filter_ips)
        if self.shard_id is not None and self.cluster.cluster_type == ClusterType.TenDBCluster:
            ins_conditions &= Q(as_ejector__tendbclusterstorageset__shard_id=self.shard_id) | Q(
                as_receiver__tendbclusterstorageset__shard_id=self.shard_id
            )
        storages = self.cluster.storageinstance_set.filter(ins_conditions)
        logger.info(str(storages.query))
        this_instances = [s.ip_port for s in storages]
        if include_proxy:
            spider_masters = self.cluster.proxyinstance_set.filter(
                tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER
            )
            this_instances.extend([p.ip_port for p in spider_masters])
            primary_map = Cluster.get_cluster_id__primary_address_map([self.cluster.id])
            this_instances.append(primary_map[self.cluster.id])
        logger.info(this_instances)

        for storage in storages:
            conditions_tmp = f" {conditions} and backup_host='{storage.machine.ip}' and backup_port={storage.port} "
            query_cmds = cmds.format(condition=conditions_tmp, limit=limit)
            self.query = query_cmds
            logger.info(query_cmds)
            res = DRSApi.rpc(
                {
                    "addresses": [storage.ip_port],
                    "cmds": [query_cmds],
                    "force": False,
                    "bk_cloud_id": self.cluster.bk_cloud_id,
                }
            )

            if res[0]["error_msg"]:
                logging.error("{} get backup info error {}".format(storage.ip_port, res[0]["error_msg"]))
                continue
            if (
                isinstance(res[0]["cmd_results"][0]["table_data"], list)
                and len(res[0]["cmd_results"][0]["table_data"]) > 0
            ):
                backup_tmps = res[0]["cmd_results"][0]["table_data"]
                backup_tmps = [
                    {"instance_ip": storage.machine.ip, "instance_port": storage.port, **info} for info in backup_tmps
                ]
                backup_infos.extend(backup_tmps)
        if backup_infos is None or len(backup_infos) == 0:
            logger.error("{} has no backup info".format(self.cluster.id))
            return None
        backup_info_dict = []
        for backup_info in backup_infos:
            # backup_info["backup_dir"] = os.path.dirname(backup_info["backup_meta_file"])
            backup_info["index"] = {"file_name": os.path.basename(backup_info["backup_meta_file"]), "task_id": ""}
            backup_info_format = self._backup_info_format(backup_info)
            backup_info_format["backup_source"] = MySQLBackupSource.LOCAL.value
            if backup_info["backup_meta_file"] not in backup_info_format["local_files"]:
                backup_info_format["local_files"].append(backup_info["backup_meta_file"])
            backup_info_dict.append(backup_info_format)
        return backup_info_dict

    def get_local_latest_backup_info(self, latest_time: datetime = None) -> dict:
        """
        查询tendbHa/tendbCluster集群指定多个实例列表下的最新一个本地备份
        @param latest_time: 备份最大时间
        @return: 返回一条本地备份记录
        """
        backup_infos = self.get_local_backup_infos(latest_time, " limit 1 ")
        backup_time = "1999-01-01T11:11:11+08:00"
        if backup_infos is None or len(backup_infos) == 0:
            return None
        max_backup = backup_infos[0]
        for backup in backup_infos:
            if compare_time(backup["backup_consistent_time"], backup_time):
                backup_time = backup["backup_consistent_time"]
                max_backup = backup
        logger.info(_("使用的备份信息: {}".format(max_backup)))
        return max_backup
