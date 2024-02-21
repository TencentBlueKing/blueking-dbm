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

from django.utils import timezone
from django.utils.translation import ugettext as _

from backend.components import DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.models import Cluster
from backend.utils.time import compare_time, str2datetime

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


def get_local_backup(instances: list, cluster: Cluster, end_time: str = None):
    """
    查询集群的最近备份记录
    @param instances:实例列表 ip:port
    @param cluster: 集群
    @param end_time: 备份最大时间，这里的时间需要转换成UTC时间，因为sql语句中是转换为0时区进行比较的
    @return: dict
    """
    #  为了兼容 backup_time和backup_consistent_time是一样的
    if end_time:
        end_time = str2datetime(end_time).astimezone(timezone.utc).isoformat()
        cond = f"backup_consistent_time<\"CONVERT_TZ('{end_time}',@@time_zone,'+00:00')\""
        query_cmds = cmds.format(cond=cond, limit="limit 1")
    else:
        query_cmds = cmds.format(cond="true", limit="limit 1")

    backups = get_local_backup_list(instances, cluster, query_cmds)
    # 多份备份比较 backup map 列表....
    backup_time = "1999-01-01T11:11:11+08:00"
    if len(backups) > 0:
        max_backup = backups[0]
        for backup in backups:
            if compare_time(backup["backup_consistent_time"], backup_time):
                backup_time = backup["backup_consistent_time"]
                max_backup = backup

        logger.info(_("使用的备份信息: {}".format(max_backup)))
        return max_backup
    else:
        return None
