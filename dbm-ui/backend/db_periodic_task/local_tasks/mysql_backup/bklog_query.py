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
from typing import Dict, List

from backend import env
from backend.components.bklog.client import BKLogApi
from backend.utils.string import pascal_to_snake
from backend.utils.time import datetime2str


def _get_log_from_bklog(collector, start_time, end_time, query_string="*") -> List[Dict]:
    """
    从日志平台获取对应采集项的日志
    @param collector: 采集项名称
    @param start_time: 开始时间
    @param end_time: 结束时间
    @param query_string: 过滤条件
    """
    resp = BKLogApi.esquery_search(
        {
            "indices": f"{env.DBA_APP_BK_BIZ_ID}_bklog.{collector}",
            "start_time": datetime2str(start_time),
            "end_time": datetime2str(end_time),
            # 这里需要精确查询集群域名，所以可以通过log: "key: \"value\""的格式查询
            "query_string": query_string,
            "start": 0,
            "size": 6000,
            "sort_list": [["dtEventTimeStamp", "asc"], ["gseIndex", "asc"], ["iterationIndex", "asc"]],
        },
        use_admin=True,
    )
    backup_logs = []
    for hit in resp["hits"]["hits"]:
        raw_log = json.loads(hit["_source"]["log"])
        backup_logs.append({pascal_to_snake(key): value for key, value in raw_log.items()})

    return backup_logs


class ClusterBackup:
    """
    集群前一天备份信息，包括全备和binlog
    """

    def __init__(self, cluster_id: int, cluster_domain: str):
        self.cluster_id = cluster_id
        self.cluster_domain = cluster_domain
        self.backups = {}
        self.success = False

    def query_backup_log_from_bklog(self, start_time: datetime.datetime, end_time: datetime.datetime) -> List[Dict]:
        """
        通过日志平台查询集群的时间范围内的全备备份记录
        :param start_time: 开始时间
        :param end_time: 结束时间
        """
        backup_files = []
        backup_logs = _get_log_from_bklog(
            collector="mysql_dbbackup_result",
            start_time=start_time,
            end_time=end_time,
            query_string=f'log: "cluster_id: {self.cluster_id}"',
            # query_string=f'log: "cluster_address: \\"{self.cluster_domain}\\""',
        )
        for log in backup_logs:
            bf = {
                "bk_biz_id": log["bk_biz_id"],
                "backup_id": log["backup_id"],
                "cluster_domain": log["cluster_address"],
                "cluster_id": log["cluster_id"],
                "mysql_host": log["mysql_host"],
                "mysql_port": log["mysql_port"],
                "mysql_role": log["mysql_role"],
                "backup_type": log["backup_type"],
                "file_list": log["file_list"],
                "data_schema_grant": log["data_schema_grant"],
                "is_full_backup": log["is_full_backup"],
                "total_filesize": log["total_filesize"],
                "encrypt_enable": log["encrypt_enable"],
                "mysql_version": log["mysql_version"],
                "backup_begin_time": log["backup_begin_time"],
                "backup_end_time": log["backup_end_time"],
                "backup_consistent_time": log["backup_consistent_time"],
                "shard_value": log["shard_value"],
            }
            backup_files.append(bf)
        return backup_files

    def query_binlog_from_bklog(self, start_time: datetime.datetime, end_time: datetime.datetime) -> List[Dict]:
        """
        通过日志平台查询集群的时间范围内的binlog 备份记录
        :param cluster_domain: 集群
        :param start_time: 开始时间
        :param end_time: 结束时间
        """
        binlogs = []
        backup_logs = _get_log_from_bklog(
            collector="mysql_binlog_result",
            start_time=start_time,
            end_time=end_time,
            query_string=f'log: "cluster_id: {self.cluster_id}"',
            # query_string=f'log: "cluster_address: \\"{self.cluster_domain}\\""',
        )
        for log in backup_logs:
            bl = {
                "cluster_domain": log["cluster_domain"],
                "cluster_id": log["cluster_id"],
                "task_id": log["task_id"],
                "file_name": log["filename"],  # file_name
                "file_size": log["size"],
                "file_mtime": log["file_mtime"],
                "file_type": "binlog",
                "mysql_host": log["host"],
                "mysql_port": log["port"],
                "mysql_role": log["db_role"],
                "backup_status": log["backup_status"],
                "backup_status_info": log["backup_status_info"],
            }
            binlogs.append(bl)
        return binlogs
