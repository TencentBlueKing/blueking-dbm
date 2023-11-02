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
import logging
from typing import Dict, List

from django.utils.translation import ugettext as _

from backend import env
from backend.components.bklog.client import BKLogApi
from backend.utils.string import pascal_to_snake

logger = logging.getLogger("root")


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
            "start_time": start_time,
            "end_time": end_time,
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
    集群前一天备份信息，
    tendisplus和tendis ssd包括全备和binlog,
    tendis cache 集群只有全备
    """

    def __init__(self, cluster_id: int, cluster_domain: str):
        self.cluster_id = cluster_id
        self.cluster_domain = cluster_domain

    def query_full_log_from_bklog(self, start_time: datetime.datetime, end_time: datetime.datetime) -> List[Dict]:
        """
        通过日志平台查询集群的时间范围内的全备备份记录
        :param start_time: 开始时间
        :param end_time: 结束时间
        """
        backup_files = []
        # status = "to_backup_system_success"
        backup_logs = _get_log_from_bklog(
            collector="redis_fullbackup_result",
            start_time=start_time.strftime("%Y-%m-%d %H:%M:%S"),
            end_time=end_time.strftime("%Y-%m-%d %H:%M:%S"),
            query_string=f"domain: {self.cluster_domain}",
            # query_string=f"domain: {self.cluster_domain} AND status: {status}",
        )
        if not backup_logs:
            logger.error(_("无法查找到在时间范围内{}-{}，集群{}的全备份日志").format(start_time, end_time, self.cluster_domain))
        for bklog in backup_logs:
            backup_files.append(self.convert_to_backup_system_format(bklog))
        return backup_files

    def query_binlog_from_bklog(
        self,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        host_ip: str = None,
        port: int = None,
    ) -> List[Dict]:
        """
        通过日志平台查询集群的时间范围内的binlog 备份记录
        :param cluster_domain: 集群
        :param start_time: 开始时间
        :param end_time: 结束时间
        :param cluster_domain: 集群
        :param host_ip: 过滤的主机IP
        :param port: 端口
        """
        binlogs = []
        backup_logs = _get_log_from_bklog(
            collector="redis_binlog_backup_result",
            start_time=start_time.strftime("%Y-%m-%d %H:%M:%S"),
            end_time=end_time.strftime("%Y-%m-%d %H:%M:%S"),
            # query_string=f'log: "cluster_id: {self.cluster_id}"',
            # 这里redis备份没有上传cluster_id ,通过域名查询
            query_string=f"domain: {self.cluster_domain} AND server_ip: {host_ip} AND server_port: {port} ",
        )
        if not backup_logs:
            logger.error(_("无法查找到在时间范围内{}-{}，集群{}的binlog备份日志").format(start_time, end_time, self.cluster_domain))
        for bklog in backup_logs:
            binlogs.append(self.convert_to_backup_system_format(bklog))
        return binlogs

    @staticmethod
    def convert_to_backup_system_format(bk_log):
        return {
            "cluster_domain": bk_log["domain"],
            "task_id": bk_log["backup_taskid"],
            "file_type": bk_log["backup_tag"],
            "uptime": bk_log["end_time"],
            # to_backup_system_start、to_backup_system_failed,to_backup_system_success
            "backup_status": bk_log["status"],
            "backup_status_info": bk_log["message"],
            "redis_ip": bk_log["server_ip"],
            "redis_port": bk_log["server_port"],
            "redis_role": bk_log["role"],
            "file_size": bk_log["backup_file_size"],
            "file_name": bk_log["backup_file"].split("/")[-1],
            # bk_log["start_time"] 是全备份快照开始的时间-》文件最后写入时间作为binlog查询开始的时间
            "file_last_mtime": bk_log["start_time"],
        }
