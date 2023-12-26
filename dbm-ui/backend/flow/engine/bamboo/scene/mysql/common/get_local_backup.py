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
import datetime
import json
import logging.config
import os.path

from django.utils.translation import ugettext as _

from backend.components import DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.models import Cluster
from backend.utils.time import compare_time, datetime2str

logger = logging.getLogger("root")


def get_local_backup(instances: list, cluster: Cluster, end_time: str = None):
    """
    @param instances:实例列表 ip:port
    @param cluster: 集群
    @param end_time: 备份最大时间
    @return: dict
    """
    if end_time:
        cmds = (
            "select * from infodba_schema.local_backup_report where "
            "server_id=@@server_id AND backup_end_time<'{}' AND backup_end_time>DATE_SUB(CURDATE(),INTERVAL 1 WEEK) "
            "and is_full_backup=1 order by backup_end_time desc limit 1".format(end_time)
        )
    else:
        cmds = (
            "select * from infodba_schema.local_backup_report where "
            "server_id=@@server_id AND backup_end_time>DATE_SUB(CURDATE(),INTERVAL 1 WEEK) "
            "and is_full_backup=1 order by backup_end_time desc limit 1"
        )
    backups = []

    logger.info(_("备份信息: {}".format(backups)))
    for addr in instances:
        res = DRSApi.rpc(
            {
                "addresses": [addr],
                "cmds": [cmds],
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
            backup_tmp = res[0]["cmd_results"][0]["table_data"][0]
            addr_split = addr.split(IP_PORT_DIVIDER)
            backup_tmp["instance_ip"] = addr_split[0]
            backup_tmp["instance_port"] = addr_split[1]
            backup_time = datetime.datetime.strptime(backup_tmp["backup_consistent_time"], "%Y-%m-%d %H:%M:%S")
            backup_time = backup_time - datetime.timedelta(hours=8)
            # utc_time = backup_time.strftime('%Y-%m-%dT%H:%M:%S')
            backup_time_utc = backup_time.astimezone(datetime.timezone.utc)
            utc_time_str = datetime2str(backup_time_utc)
            backup_tmp["backup_consistent_time"] = utc_time_str
            backup_tmp["backup_time"] = utc_time_str
            backups.append(backup_tmp)

    # 多份备份比较 backup map 列表....
    backup_time = "1999-01-01T11:11:11+08:00"
    if len(backups) > 0:
        max_backup = backups[0]
        for backup in backups:
            if compare_time(backup["backup_consistent_time"], backup_time):
                backup_time = backup["backup_consistent_time"]
                max_backup = backup
        #  截取路径
        max_backup["backup_dir"] = os.path.dirname(max_backup["backup_meta_file"])
        max_backup["index"] = {"file_name": os.path.basename(max_backup["backup_meta_file"])}
        # max_backup["backup_time"] = max_backup["backup_consistent_time"]
        binlog_info = json.loads(max_backup["binlog_info"])
        max_backup["binlog_info"] = binlog_info
        extra_fields = json.loads(max_backup["extra_fields"])
        max_backup["extra_fields"] = extra_fields
        file_list = json.loads(max_backup["file_list"])
        max_backup["file_list"] = file_list

        logger.info(_("使用的备份信息: {}".format(max_backup)))
        return max_backup
    else:
        return None
