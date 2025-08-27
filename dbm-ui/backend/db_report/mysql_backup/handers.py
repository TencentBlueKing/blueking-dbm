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
from django.utils.translation import ugettext as _

from backend.components import DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import InstanceInnerRole
from backend.db_meta.models.cluster import Cluster
from backend.db_meta.models.mysql_backup_result import MysqlBackupResult
from backend.db_meta.models.mysql_binlog_backup_result import MysqlBinlogResult
from backend.db_report.mysql_backup.constants import BACKUP_FILE_DEADLINE_DAYS
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
        shard_id: int = None,
        filter_ips: list[str] = None,
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
        self.shard_id = shard_id
        self.filter_ips = filter_ips
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
                begin_time = datetime.now().astimezone() - timedelta(days=self.deadlines_days)
                conditions &= Q(backup_consistent_time__gte=begin_time)
            if latest_time is not None:
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

        backup_infos = (
            MysqlBackupResult.objects.using("report_db").filter(conditions).order_by("-backup_consistent_time")
        )
        self.query = str(backup_infos.query)
        logger.info(self.query)
        if backup_infos is None or len(backup_infos) == 0:
            self.errmsg = _("集群id {} 没有指定过滤条件的备份信息").format(self.cluster.id)
            logger.error(self.errmsg)
            return None
        backup_info_dist = []
        for backup_info in backup_infos:
            # backup_info.backup_consistent_time = backup_info.backup_consistent_time.strftime("%Y-%m-%dT%H:%M:%S%z")
            # backup_info.backup_begin_time = backup_info.backup_begin_time.strftime("%Y-%m-%dT%H:%M:%S%z")
            # backup_info.backup_end_time = backup_info.backup_end_time.strftime("%Y-%m-%dT%H:%M:%S%z")
            backup_info.backup_consistent_time = backup_info.backup_consistent_time.isoformat()
            backup_info.backup_begin_time = backup_info.backup_begin_time.isoformat()
            backup_info.backup_end_time = backup_info.backup_end_time.isoformat()
            backup_info_dict = model_to_dict(backup_info)
            backup_info_dist.append(self._backup_info_format(backup_info_dict))

        return backup_info_dist

    def get_tendb_latest_backup_info(self, latest_time: datetime = None) -> Dict[str, Any]:
        """
        tendbHa 获取指定集群的最近一份远程备份
        @param latest_time: 查询备份最迟时间
        @return: 返回一条远程备份记录
        """
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
            self.errmsg = _("集群id {} 查询不到 {} shard 分片的备份").format(self.cluster.id, shard_list)
            logger.error(self.errmsg)
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
                logger.info("backup_id: {} not include all remote nodes".format(backup_id))
                cluster_backup_id_list.remove(backup_id)
                cluster_backup_info_map.pop(backup_id)
        if len(cluster_backup_info_map) == 0:
            self.errmsg = _("集群id {} 查询不到一份包含所有remote/DBCTL/spider_master的备份").format(self.cluster.id)
            logger.error(self.errmsg)
            return None
        if limit_one:
            return cluster_backup_info_map[cluster_backup_id_list[0]]
        return cluster_backup_info_map

    def get_binlog_backup_infos(self, host: str, port: int, start_time: datetime, end_time: datetime = None) -> list:
        """
        获取指定备份信息的binlog备份信息
        """
        conditions = Q(cluster_id=self.cluster.id, host=host, port=port)
        if end_time is None:
            end_time = datetime.now().astimezone()
        conditions &= Q(start_time__gte=start_time) & Q(stop_time__lte=end_time)
        logger.info(
            _("binlog查询时间范围是: {} {}".format(start_time.astimezone().isoformat(), end_time.astimezone().isoformat()))
        )
        binlog_infos = MysqlBinlogResult.objects.using("report_db").filter(conditions).order_by("-start_time")
        self.query = str(binlog_infos.query)
        logger.info(self.query)
        if binlog_infos is None or len(binlog_infos) == 0:
            return []
        binlog_list = []
        for binlog_info in binlog_infos:
            # binlog_info.file_mtime = binlog_info.file_mtime.strftime("%Y-%m-%dT%H:%M:%S%z")
            # binlog_info.start_time = binlog_info.start_time.strftime("%Y-%m-%dT%H:%M:%S%z")
            # binlog_info.stop_time = binlog_info.stop_time.strftime("%Y-%m-%dT%H:%M:%S%z")
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
        binlog_info = backup_info["binlog_info"]
        result = {}
        if end_time is None:
            end_time = datetime.now().astimezone()
        if start_time > end_time:
            result["query_binlog_error"] = _("备份时间点:{} 大于 回滚时间点:{}".format(start_time, end_time))
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
                    result["query_binlog_error"] = _("原备份节点{} 查询不到binlog").format(
                        binlog_info["show_master_status"]["master_host"]
                    )
                    return result
            result["binlog_start_file"] = binlog_info["show_master_status"]["binlog_file"]
            result["binlog_start_pos"] = binlog_info["show_master_status"]["binlog_pos"]

        else:
            if "show_slave_status" in binlog_info.keys() and binlog_info.get("show_slave_status", None) is not None:
                # 备份信息来自从节点，从 show_slave_status 中获取主节点信息
                if binlog_info["show_slave_status"].get("master_host", "") == "":
                    result["query_binlog_error"] = _("show slave status 没有 master_host 信息")
                    return result
                binlog_list = self.get_binlog_backup_infos(
                    binlog_info["show_slave_status"]["master_host"],
                    binlog_info["show_slave_status"]["master_port"],
                    start_time,
                    end_time,
                )
                if binlog_info is None or len(binlog_list) == 0:
                    if binlog_list is None or len(binlog_list) == 0:
                        result["query_binlog_error"] = _("原备份节点{} 查询不到binlog").format(
                            binlog_info["show_slave_status"]["master_host"]
                        )
                        return result
                result["binlog_start_file"] = binlog_info["show_slave_status"]["binlog_file"]
                result["binlog_start_pos"] = binlog_info["show_slave_status"]["binlog_pos"]
            else:
                result["query_binlog_error"] = _("找不到 show slave status 信息")
                return result
        logger.info("master binlog is:", binlog_list)
        result["binlog_task_ids"] = [i["task_id"] for i in binlog_list]
        binlog_files = [i["filename"] for i in binlog_list]
        if result["binlog_start_file"] not in binlog_files:
            result["query_binlog_error"] = _("查不到起始binlog文件 {}").format(result["binlog_start_file"])
        # 可添加从binlog_start_file开始完后判断日志连续性...
        result["binlog_files"] = ",".join(binlog_files)
        return result

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
                begin_time = datetime.now().astimezone() - timedelta(days=self.deadlines_days)
                begin_time_str = begin_time.isoformat()
                conditions = (
                    f" {conditions} and backup_consistent_time >= CONVERT_TZ('{begin_time_str}',@@time_zone,'+00:00') "
                )

            if latest_time is not None:
                logger.info(_("指定备份最迟时间 {} ").format(latest_time))
                latest_time = latest_time.astimezone().isoformat()
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
            backup_info["index"] = {"file_name": os.path.basename(backup_info["backup_meta_file"]), "task_id": ""}
            backup_info_format = self._backup_info_format(backup_info)
            if backup_info["index"] not in backup_info_format["file_list"]:
                backup_info_format["file_list"].append(backup_info["index"])
            backup_info_dict.append(backup_info_format)
        return backup_info_dict

    def get_local_latest_backup_info(self, instances: list = None, latest_time: datetime = None):
        """
        查询tendbHa/tendbCluster集群指定多个实例列表下的最新一个本地备份
        @param instances:实例列表 ip:port
        @param latest_time: 备份最大时间
        @return: 返回一条本地备份记录
        """
        backup_infos = self.get_local_backup_infos(instances, latest_time, "limit 1")
        backup_time = "1999-01-01T11:11:11+08:00"
        if backup_infos is None or len(backup_infos) == 0:
            return None
        max_backup = backup_infos[0]
        for backup in backup_infos:
            if compare_time(backup["backup_consistent_time"], backup_time):
                backup_time = backup["backup_consistent_time"]
                max_backup = backup
        local_files = ["{}/{}".format(max_backup["backup_dir"], i["file_name"]) for i in max_backup["file_list"]]
        max_backup["local_files"] = local_files
        logger.info(_("使用的备份信息: {}".format(max_backup)))
        return max_backup
