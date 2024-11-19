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
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Union

from django.utils.translation import ugettext as _

from backend.components.bklog.handler import BKLogHandler
from backend.db_meta.enums import ClusterType, InstanceInnerRole, InstanceStatus
from backend.db_meta.models.cluster import Cluster
from backend.db_services.mysql.fixpoint_rollback.constants import (
    BACKUP_LOG_RANGE_DAYS,
    BACKUP_LOG_ROLLBACK_TIME_RANGE_DAYS,
)
from backend.exceptions import AppBaseException
from backend.flow.engine.bamboo.scene.mysql.common.get_local_backup import get_local_backup_list
from backend.ticket.builders.common.constants import MySQLBackupSource
from backend.utils.time import compare_time, datetime2str, find_nearby_time

logger = logging.getLogger("flow")


class FixPointRollbackHandler:
    """
    封装定点回档相关接口
    """

    def __init__(self, cluster_id: int, check_full_backup=False):
        """
        @param cluster_id: 集群ID
        @param check_full_backup: 是否过滤为全备的记录
        """
        self.cluster = Cluster.objects.get(id=cluster_id)
        self.check_full_backup = check_full_backup

    def _check_data_schema_grant(self, log) -> bool:
        # 全备记录看is_full_backup
        if self.check_full_backup:
            return log["is_full_backup"]
        # 有效的备份记录看data_schema_grant
        if str(log["data_schema_grant"]).lower() == "all" or (
            "schema" in str(log["data_schema_grant"]).lower() and "data" in str(log["data_schema_grant"]).lower()
        ):
            return True

        return False

    @staticmethod
    def _check_backup_log_task_id(log) -> bool:
        # task_id 不存在或者-1 时，是较老的备份程序产生的，不符合预期，这里做兼容处理
        task_ids = [str(file.get("task_id", "-1")) for file in log["file_list"]]
        return "-1" not in task_ids

    @staticmethod
    def _get_log_from_bklog(collector: str, start_time: datetime, end_time: datetime, query_string="*") -> List[Dict]:
        return BKLogHandler.query_logs(collector, start_time, end_time, query_string)

    def aggregate_tendb_dbbackup_logs(self, backup_logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        聚合tendb的mysql_backup_result日志，按照backup_id聚合mysql备份记录
        :param backup_logs: 备份记录列表
        """
        valid_backup_logs: List[Dict[str, Any]] = []
        for log in backup_logs:
            # 过滤掉不合法的日志记录
            if not self._check_backup_log_task_id(log):
                continue

            if not self._check_data_schema_grant(log):
                continue

            file_list_infos = log.pop("file_list")
            log["file_list"], log["file_list_details"] = [], []
            log["backup_time"] = log["backup_consistent_time"]
            for info in file_list_infos:
                file_detail = {"file_name": info["file_name"], "size": info["file_size"], "task_id": info["task_id"]}
                # 聚合备份文件信息
                log["file_list_details"].append(file_detail)
                # 聚合备份文件名
                log["file_list"].append(file_detail["file_name"])
                # 补充priv、index文件信息
                if info["file_type"] in ["index", "priv"]:
                    log[info["file_type"]] = file_detail

            valid_backup_logs.append(log)

        return valid_backup_logs

    def aggregate_tendbcluster_dbbackup_logs(self, backup_logs: List[Dict], shard_list: List = None) -> List[Dict]:
        """
        聚合tendbcluster的mysql_backup_result日志，按照backup_id聚合tendb备份记录
        :param backup_logs: 备份记录列表
        :param shard_list: 指定备份分片数
        """

        def insert_time_field(_back_log, _log):
            # 如果不具有时间字段则插入，否则更新
            if "backup_begin_time" not in _back_log:
                _back_log["backup_begin_time"] = _log["backup_begin_time"]
                _back_log["backup_end_time"] = _log["backup_end_time"]
                _back_log["backup_time"] = _log["backup_time"]
            else:
                _back_log["backup_begin_time"] = min(_back_log["backup_begin_time"], _log["backup_begin_time"])
                _back_log["backup_end_time"] = max(_back_log["backup_end_time"], _log["backup_end_time"])
                _back_log["backup_time"] = max(_back_log["backup_time"], _log["backup_time"])

        def insert_log_into_node(_backup_node, _log):
            if _log["mysql_role"] in ["master", "slave"] and not self._check_data_schema_grant(log):
                return None

            if not self._check_backup_log_task_id(log):
                return None

            if not _backup_node or (
                # TODO: 此条件永真，后续可以去掉
                _log["backup_host"] not in _backup_node
                and (
                    # 能覆盖的条件：
                    # 1. 如果是remote角色，则master能覆盖slave记录。同种角色可以时间接近rollback_time可以覆盖
                    # 2. 如果是spider角色，则时间接近rollback_time可以覆盖
                    # 3. 如果是TDBCTL角色，则时间接近rollback_time可以覆盖
                    (
                        _log["mysql_role"] in ["spider_master", "spider_slave", "TDBCTL"]
                        and _log["consistent_backup_time"] > _backup_node["backup_time"]
                    )
                    or (
                        _log["mysql_role"] in ["master", "slave"]
                        and _log["mysql_role"] == "master"
                        and _backup_node.get("mysql_role", "slave") == "slave"
                    )
                    or (
                        _log["mysql_role"] in ["master", "slave"]
                        and _log["mysql_role"] == _backup_node["mysql_role"]
                        and _log["consistent_backup_time"] > _backup_node.get("backup_time", "")
                    )
                )
            ):
                # 初始化该角色的备份信息
                insert_time_field(_backup_node, _log)
                _backup_node["mysql_role"] = _log["mysql_role"]
                _backup_node["host"], _backup_node["port"] = _log["backup_host"], _log["backup_port"]
                _backup_node["file_list_details"] = []
                _backup_node["binlog_info"] = _log.get("binlog_info")

            # 更新备份时间，并插入文件列表信息
            insert_time_field(_backup_node, _log)
            for file_detail in _log["file_list"]:
                file_info = {
                    "file_name": file_detail["file_name"],
                    "size": file_detail["file_size"],
                    "task_id": file_detail["task_id"],
                }
                _backup_node["file_list_details"].append(file_info)
                # 如果是index/priv文件 则额外记录
                if file_detail["file_type"] in ["index", "priv"]:
                    _backup_node[file_detail["file_type"]] = file_info

            return _backup_node

        backup_id__backup_logs_map = defaultdict(dict)
        for log in backup_logs:
            backup_id, log["backup_time"] = log["backup_id"], log["consistent_backup_time"]
            if not backup_id__backup_logs_map.get(backup_id):
                # 初始化整体的角色信息
                backup_id__backup_logs_map[backup_id]["spider_node"] = {}
                backup_id__backup_logs_map[backup_id]["spider_slave"] = {}
                backup_id__backup_logs_map[backup_id]["tdbctl_node"] = {}
                backup_id__backup_logs_map[backup_id]["remote_node"] = defaultdict(dict)
                # 保留聚合需要的通用字段
                common_fields = [
                    "backup_id",
                    "bill_id",
                    "bk_biz_id",
                    "bk_cloud_id",
                    "time_zone",
                    "cluster_id",
                    "cluster_address",
                    "backup_begin_time",
                    "backup_end_time",
                    "backup_time",
                ]
                for field in common_fields:
                    backup_id__backup_logs_map[backup_id][field] = log[field]

            # 把该日志插入对应的角色字典中
            if log["mysql_role"] in ["master", "slave"]:
                backup_node = backup_id__backup_logs_map[backup_id]["remote_node"][log["shard_value"]]
                backup_node = insert_log_into_node(backup_node, log)
            else:
                role_map = {"spider_master": "spider_node", "TDBCTL": "tdbctl_node", "spider_slave": "spider_slave"}
                node_role = role_map.get(log["mysql_role"], log["mysql_role"])
                backup_node = backup_id__backup_logs_map[backup_id][node_role]
                backup_node = insert_log_into_node(backup_node, log)

            # 更新备份时间
            if backup_node:
                insert_time_field(backup_id__backup_logs_map[backup_id], backup_node)

        logger.info("backup info:", backup_id__backup_logs_map)
        # 获取合法的备份记录
        if shard_list is not None and len(shard_list) > 0:
            shard_list = sorted(shard_list)
        else:
            cluster_shard_num = self.cluster.tendbclusterstorageset_set.count()
            shard_list = list(range(0, cluster_shard_num))

        backup_id__valid_backup_logs = defaultdict(dict)
        for backup_id, backup_log in backup_id__backup_logs_map.items():
            # 获取合法分片ID，如果分片数不完整，则忽略
            shard_value_list = [int(s) for s in backup_log["remote_node"].keys() if backup_log["remote_node"][s]]
            if not set(shard_value_list).issuperset(set(shard_list)):
                logger.warning(_("back[{}]的shard_list{}和预期{}不匹配").format(backup_id, shard_value_list, shard_list))
                continue

            # 如果没有指定分片列表，且不存在spider master记录，则忽略
            if not backup_log["spider_node"] and not shard_list:
                logger.warning(_("back[{}]不包含spider_node备份").format(backup_id))
                continue

            # 如果没有指定分片列表，且不存在中控备份记录，则忽略
            if not backup_log["tdbctl_node"] and not shard_list:
                logger.warning(_("back[{}]不包含tdbctl_node备份").format(backup_id))
                continue

            # 如果存在多条完整的backup记录，则保留最接近rollback time的记录
            if backup_id not in backup_id__valid_backup_logs or (
                compare_time(backup_id__valid_backup_logs[backup_id]["backup_time"], backup_log["backup_time"])
            ):
                backup_id__valid_backup_logs[backup_id] = backup_log

        return list(backup_id__valid_backup_logs.values())

    def query_backup_log_from_bklog(self, start_time: datetime, end_time: datetime, **kwargs) -> List[Dict]:
        """
        通过日志平台查询集群的时间范围内的备份记录
        :param start_time: 开始时间
        :param end_time: 结束时间
        :param shard_list: tendbcluster专属，备份分片数
        """

        backup_logs = self._get_log_from_bklog(
            collector="mysql_dbbackup_result",
            start_time=start_time,
            end_time=end_time,
            query_string=f'log: "cluster_id: \\"{self.cluster.id}\\""',
        )

        if self.cluster.cluster_type == ClusterType.TenDBCluster:
            shard_list = kwargs.get("shard_list", [])
            return self.aggregate_tendbcluster_dbbackup_logs(backup_logs, shard_list)
        else:
            return self.aggregate_tendb_dbbackup_logs(backup_logs)

    def query_instance_backup_logs(self, end_time: datetime, **kwargs) -> Dict:
        """
        通过日志平台查询集群实例一周内最近的权限备份日志
        :param end_time: 结束时间
        """

        backup_logs = self._get_log_from_bklog(
            collector="mysql_dbbackup_result",
            start_time=end_time - timedelta(days=BACKUP_LOG_RANGE_DAYS),
            end_time=end_time,
            query_string=f'log: "cluster_id: \\"{self.cluster.id}\\""',
        )
        backup_instance_record: Dict[str, Any] = {}

        def init_backup_record(log):
            # 如果备份ID相同或者当前备份ID时间更接近，则忽略
            if backup_instance_record.get("backup_id") == log["backup_id"]:
                return
            if backup_instance_record.get("backup_consistent_time", "") > log["backup_consistent_time"]:
                return
            # 保留聚合需要的通用字段
            common_fields = [
                "backup_id",
                "backup_type",
                "cluster_id",
                "cluster_address",
                "bill_id",
                "bk_biz_id",
                "mysql_version",
                "backup_begin_time",
                "backup_end_time",
                "backup_consistent_time",
                "bk_cloud_id",
            ]
            for field in common_fields:
                backup_instance_record[field] = log[field]
            # 初始化实例的file_list
            backup_instance_record["file_list"]: Dict[str, str] = {}

        def init_file_list(log):
            # 找到备份日志的priv文件
            priv_file = next((file for file in log["file_list"] if file["file_type"] == "priv"), None)
            inst = f"{log['backup_host']}:{log['backup_port']}"
            if not priv_file:
                return
            priv_file.update(mysql_role=log["mysql_role"])
            # 覆盖更新，priv_file在同一个实例，同一个备份仅有一条记录的
            backup_instance_record["file_list"][inst] = priv_file

        for log in backup_logs:
            init_backup_record(log)
            init_file_list(log)

        return backup_instance_record

    def query_binlog_from_bklog(
        self,
        start_time: datetime,
        end_time: datetime,
        host_ip: str = None,
        port: int = None,
        minute_range: int = 20,
    ) -> Dict:
        """
        通过日志平台查询集群的时间范围内的binlog记录
        :param start_time: 开始时间
        :param end_time: 结束时间
        :param host_ip: 过滤的主机IP
        :param port: 端口
        :param minute_range: 放大的前后时间范围
        """
        if not host_ip:
            master = self.cluster.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER)
            host_ip, port = master.machine.ip, master.port

        binlogs = self._get_log_from_bklog(
            collector="mysql_binlog_result",
            # 时间范围前后放大避免日志平台上传延迟
            start_time=start_time - timedelta(minutes=minute_range),
            end_time=end_time + timedelta(minutes=minute_range),
            query_string=f"host: {host_ip} AND port: {port} AND cluster_id: {self.cluster.id}",
        )

        if not binlogs:
            return {}
            # raise AppBaseException(_("无法查找在时间范围内{}-{}，主机{}的binlog日志").format(start_time, end_time, host_ip))

        # 根据stop_time和host进行过滤(字典外层参数cluster_domain,cluster_id,host,port都一样)
        binlog_record: Dict[str, Union[str, List]] = {
            "cluster_domain": binlogs[0]["cluster_domain"],
            "cluster_id": binlogs[0]["cluster_id"],
            "host": binlogs[0]["host"],
            "port": binlogs[0]["port"],
            "file_list_details": [],
        }
        collector_fields = ["file_mtime", "start_time", "stop_time", "size", "task_id", "filename"]
        # 记录file task id，用于去重
        file_task_id_list = []
        for log in binlogs:
            if log["task_id"] in file_task_id_list:
                continue

            detail = {field: log[field] for field in collector_fields}
            detail["file_name"] = detail.pop("filename")
            file_task_id_list.append(detail["task_id"])
            binlog_record["file_list_details"].append(detail)

        return binlog_record

    def query_backup_log_from_local(self) -> List[Dict[str, Any]]:
        """
        查询集群本地的备份记录
        """
        # 获取集群所有正在运行中的master/slave实例
        instances = self.cluster.storageinstance_set.filter(status=InstanceStatus.RUNNING).values(
            "machine__ip", "port"
        )
        instances = [f"{inst['machine__ip']}:{inst['port']}" for inst in instances]
        # 查询集群本地的备份记录
        local_backup_logs = get_local_backup_list(instances=instances, cluster=self.cluster)
        return local_backup_logs

    def query_latest_backup_log(
        self, rollback_time: datetime, backup_source: str = MySQLBackupSource.REMOTE.value, **kwargs
    ) -> Dict[str, Any]:
        """
        根据回档时间查询最新一次的备份记录
        """
        if backup_source == MySQLBackupSource.LOCAL.value:
            # 本地查询
            backup_logs = self.query_backup_log_from_local()
        else:
            # 日志平台查询
            end_time = rollback_time
            start_time = end_time - timedelta(days=BACKUP_LOG_ROLLBACK_TIME_RANGE_DAYS)
            backup_logs = self.query_backup_log_from_bklog(start_time, end_time, **kwargs)

        if not backup_logs:
            return None

        backup_logs.sort(key=lambda x: x["backup_time"])
        time_keys = [log["backup_time"] for log in backup_logs]
        try:
            latest_log = backup_logs[find_nearby_time(time_keys, datetime2str(rollback_time), 1)]
        except IndexError:
            raise AppBaseException(_("无法找到小于时间点{}附近的日志记录，请检查时间点的合法性或稍后重试").format(rollback_time))

        return latest_log
