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
from backend.db_report.models.mysql_backup_result import MysqlBackupResult
from backend.db_report.models.mysql_binlog_backup_result import MysqlBinlogResult
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

    def query_backup_from_dbreport(
        self, start_time: datetime.datetime, end_time: datetime.datetime
    ) -> List[MysqlBackupResult]:
        """
        通过 bk_dbm_dbreport 库查询集群的时间范围内的全备备份记录
        :param start_time: 开始时间
        :param end_time: 结束时间
        """
        backups = MysqlBackupResult.objects.filter(
            cluster_id=self.cluster_id,
            cluster_address=self.cluster_domain,
            backup_consistent_time__range=(start_time, end_time),
        )
        return list(backups)

    def query_binlog_from_dbreport(
        self, start_time: datetime.datetime, end_time: datetime.datetime
    ) -> List[MysqlBinlogResult]:
        """
        通过 bk_dbm_dbreport 查询集群的时间范围内的binlog 备份记录
        :param start_time: 开始时间
        :param end_time: 结束时间
        """
        binlogs = MysqlBinlogResult.objects.filter(
            cluster_id=self.cluster_id, cluster_domain=self.cluster_domain, start_time__range=(start_time, end_time)
        )
        return list(binlogs)
