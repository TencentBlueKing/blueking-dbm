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
import json
import logging.config
import os.path

from django.db.models import Q
from django.utils.translation import gettext as _

from backend.components import DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterType, InstanceInnerRole, InstanceStatus, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster

logger = logging.getLogger("root")

cmds = """select backup_id, mysql_role, shard_value, backup_type, cluster_id, cluster_address, backup_host, backup_port,
server_id, bill_id, bk_biz_id, mysql_version, data_schema_grant, is_full_backup,
backup_status, backup_meta_file, binlog_info, file_list, extra_fields, backup_config_file,
DATE_FORMAT(CONVERT_TZ(backup_begin_time,@@time_zone,"+00:00"),'%Y-%m-%dT%H:%i:%s+00:00') as backup_begin_time,
DATE_FORMAT(CONVERT_TZ(backup_end_time,@@time_zone,"+00:00"),'%Y-%m-%dT%H:%i:%s+00:00')as backup_end_time,
DATE_FORMAT(CONVERT_TZ(backup_consistent_time,@@time_zone,"+00:00"),'%Y-%m-%dT%H:%i:%s+00:00') as backup_consistent_time,
DATE_FORMAT(CONVERT_TZ(backup_consistent_time,@@time_zone,"+00:00"),'%Y-%m-%dT%H:%i:%s+00:00') as backup_time
from infodba_schema.local_backup_report
where {cond} and server_id=@@server_id and backup_consistent_time>DATE_SUB(CURDATE(),INTERVAL 1 WEEK) and is_full_backup=1 order by backup_consistent_time desc {limit}"""  # noqa


def get_local_backup_list(instances: list, cluster: Cluster, query_cmds: str = None) -> list:
    """
    查询集群的备份记录列表
    @param instances:实例列表 ip:port
    @param cluster: 集群
    @param query_cmds: 查询的sql语句
    @return: dict
    """
    #  为了兼容 backup_time和backup_consistent_time是一样的
    query_cmds = query_cmds or cmds.format(cond="true", limit="")
    backups = []
    for addr in instances:
        res = DRSApi.rpc(
            {
                "addresses": [addr],
                "cmds": [query_cmds],
                "force": False,
                "bk_cloud_id": cluster.bk_cloud_id,
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
            backups.extend(backup_tmps)

    for one_backup in backups:
        #  截取路径
        one_backup["backup_dir"] = os.path.dirname(one_backup["backup_meta_file"])
        one_backup["index"] = {"file_name": os.path.basename(one_backup["backup_meta_file"])}
        # one_backup["backup_time"] = max_backup["backup_consistent_time"]
        binlog_info = json.loads(one_backup["binlog_info"])
        one_backup["binlog_info"] = binlog_info
        extra_fields = json.loads(one_backup["extra_fields"])
        one_backup["extra_fields"] = extra_fields
        file_list = json.loads(one_backup["file_list"])
        one_backup["file_list"] = file_list

    return backups


def check_storage_database(bk_cloud_id: int, ip: str, port: int) -> bool:
    """
    检查数据库是否为空实例
    @param ip: 实例ip
    @param port: 实例端口
    @param bk_cloud_id: bk_cloud_id
    @return:
    """
    query_cmds = """select SCHEMA_NAME from information_schema.schemata where SCHEMA_NAME not in
    ('information_schema','db_infobase','infodba_schema','mysql','test',
    'sys','performance_schema','__cdb_recycle_bin__')"""
    res = DRSApi.rpc(
        {
            "addresses": ["{}{}{}".format(ip, IP_PORT_DIVIDER, port)],
            "cmds": [query_cmds],
            "force": False,
            "bk_cloud_id": bk_cloud_id,
        }
    )
    if res[0]["error_msg"]:
        logging.error("get databases  error {}".format(res[0]["error_msg"]))
        return False
    if isinstance(res[0]["cmd_results"][0]["table_data"], list) and len(res[0]["cmd_results"][0]["table_data"]) == 0:
        logging.info(res[0]["cmd_results"])
        return True
    else:
        return False


def check_rollback_databases(cluster_id: int, database_list: list[str], shard_id: int = None) -> (str, bool):
    """
    检查回档的数据库是否在源集群存在
    @param cluster_id: 目标集群id
    @param database_list: 逻辑备份数据库列表
    """
    target_cluster = Cluster.objects.get(id=cluster_id)
    if target_cluster.cluster_type == ClusterType.TenDBCluster.value:
        if shard_id is None:
            spider_master = target_cluster.proxyinstance_set.filter(
                status=InstanceStatus.RUNNING, tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER
            ).first()
            rds_instance = spider_master.ip_port
        else:
            remote_master = target_cluster.storageinstance_set.filter(
                status=InstanceStatus.RUNNING, as_ejector__tendbclusterstorageset__shard_id=shard_id
            ).first()
            rds_instance = remote_master.ip_port
    else:
        filters = Q(
            cluster__cluster_type=ClusterType.TenDBSingle.value, instance_inner_role=InstanceInnerRole.ORPHAN.value
        ) | Q(cluster__cluster_type=ClusterType.TenDBHA.value, instance_inner_role=InstanceInnerRole.MASTER.value)
        master = target_cluster.storageinstance_set.get(filters)
        rds_instance = master.ip_port
    ignore_database_list = [
        "information_schema",
        "db_infobase",
        "infodba_schema",
        "mysql",
        "test",
        "sys",
        "performance_schema",
        "__cdb_recycle_bin__",
    ]
    ignore_database_list_str = "','".join(ignore_database_list)
    database_list_str = "','".join(database_list)
    query_cmds = """select SCHEMA_NAME from information_schema.schemata where
    SCHEMA_NAME not in ('{}') and SCHEMA_NAME in ('{}')""".format(
        ignore_database_list_str, database_list_str
    )
    logger.info(query_cmds)
    res = DRSApi.rpc(
        {
            "addresses": [rds_instance],
            "cmds": [query_cmds],
            "force": False,
            "bk_cloud_id": target_cluster.bk_cloud_id,
        }
    )
    if res[0]["error_msg"]:
        return _("获取目标集群 {} 的库列表失败").format(target_cluster.name, res[0]["error_msg"]), False
    if isinstance(res[0]["cmd_results"][0]["table_data"], list) and len(res[0]["cmd_results"][0]["table_data"]) == 0:
        logging.info(res[0]["cmd_results"])
        return "", True
    else:
        return _("目标集群 {} 存在和指定回档备份相同的库名。回档会发生覆盖").format(target_cluster.name), False


def check_binlog_missing(binlog_file_list: list[str]) -> (list[str], bool):
    binlog_ids = []
    missing_binlog_files = []
    if len(binlog_file_list) == 0:
        return [], True
    binlog_pre = binlog_file_list[0].split(".")[0]
    for binlog_file in binlog_file_list:
        binlog_file_split = binlog_file.split(".")
        if len(binlog_file_split) < 2:
            return [f"binlog {binlog_file} for is not binlogPORT.xxxx "], False
        #  int 转换可能出错
        try:
            binlog_file_id = int(binlog_file_split[1])
        except ValueError:
            return [f" {binlog_file} binlog number str to int error "], False
        binlog_ids.append(binlog_file_id)
    binlog_ids.sort()
    for i in range(1, len(binlog_ids)):
        diff = binlog_ids[i] - binlog_ids[i - 1]
        if diff > 1:
            for j in range(binlog_ids[i - 1] + 1, binlog_ids[i]):
                missing_binlog_files.append(f"{binlog_pre}.{j}")
    if len(missing_binlog_files) == 0:
        return [], True
    else:
        return missing_binlog_files, False
