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
from typing import List

from backend.db_proxy.reverse_api.common.impl.sync_report.direct_mode.writers.writers_base import DirectWriterABS
from backend.db_report.models.mysql_backup_result import MysqlBackupResult


class BackupReportResultWriter(DirectWriterABS):
    @classmethod
    def write_event(cls, bk_cloud_id: int, trace_id: str, ip: str, port_list: List[int], events: List):
        """
        ToDo 这个函数没实现完
        """
        for ev in events:
            MysqlBackupResult.objects.create(
                event_source_ip=ev["event_source_ip"],
                event_bk_cloud_id=ev["event_bk_cloud_id"],
                event_receive_timestamp=ev["event_receive_timestamp"],
                backup_id=ev["backup_id"],
                backup_type=ev["backup_type"],
                cluster_id=ev["cluster_id"],
                cluster_address=ev["cluster_address"],
                backup_host=ev["backup_host"],
                backup_port=ev["backup_port"],
                mysql_role=ev["mysql_role"],
                shard_value=ev["shard_value"],
                bill_id=ev["bill_id"],
                bk_biz_id=ev["bk_biz_id"],
                mysql_version=ev["mysql_version"],
                data_schema_grant=ev["data_schema_grant"],
                is_full_backup=ev["is_full_backup"],
                file_retention_tag=ev["file_retention_tag"],
                total_filesize=ev["total_filesize"],
                backup_consistent_time=ev["backup_consistent_time"],
                backup_begin_time=ev["backup_begin_time"],
                backup_end_time=ev["backup_end_time"],
                binlog_info=ev["binlog_info"],
                file_list=ev["file_list"],
                extra_fields="",
                backup_status="",
                backup_method="",
                is_standby="",
            )
