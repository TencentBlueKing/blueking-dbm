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
from datetime import datetime, timedelta
from typing import Any, Dict, List

from django.utils.translation import ugettext as _

from backend import env
from backend.components import BKLogApi
from backend.db_meta.models import Cluster
from backend.db_services.mongodb.restore.constants import BACKUP_LOG_RANGE_DAYS, PitrFillType
from backend.exceptions import AppBaseException
from backend.utils.string import pascal_to_snake
from backend.utils.time import datetime2str, find_nearby_time, timezone2timestamp


class MongoDBRestoreHandler(object):
    """mongodb定点构造函数封装"""

    def __init__(self, cluster_id: int):
        self.cluster = Cluster.objects.get(id=cluster_id)

    def _get_log_from_bklog(
        self, collector: str, start_time: datetime, end_time: datetime, query_string="*"
    ) -> List[Dict]:
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
                "query_string": query_string,
                "start": 0,
                "size": 1000,
                "sort_list": [["dtEventTimeStamp", "asc"], ["gseIndex", "asc"], ["iterationIndex", "asc"]],
            },
            use_admin=True,
        )
        backup_logs = []
        for hit in resp["hits"]["hits"]:
            raw_log = json.loads(hit["_source"]["log"])
            backup_logs.append({pascal_to_snake(key): value for key, value in raw_log.items()})

        return backup_logs

    def _query_latest_log_and_index(self, rollback_time: datetime, query_string: str, time_key: str, flag: int):
        """查询距离rollback_time最近的备份记录"""
        end_time = rollback_time
        start_time = end_time - timedelta(days=BACKUP_LOG_RANGE_DAYS)

        backup_logs = self._get_log_from_bklog(
            collector="mongo_backup_result",
            start_time=start_time,
            end_time=end_time,
            query_string=query_string,
        )
        if not backup_logs:
            raise AppBaseException(_("距离回档时间点7天内没有备份日志").format(rollback_time))

        # 获取距离回档时间最近的全备日志
        backup_logs.sort(key=lambda x: x[time_key])
        time_keys = [log[time_key] for log in backup_logs]
        try:
            latest_backup_log_index = find_nearby_time(time_keys, timezone2timestamp(rollback_time), flag)
        except IndexError:
            raise AppBaseException(_("无法找到时间点{}附近的全备日志记录").format(rollback_time))

        return backup_logs, latest_backup_log_index

    def query_latest_backup_log(self, rollback_time: datetime) -> Dict[str, Any]:
        """
        查询距离rollback_time最近的全备-增量备份文件
        @param rollback_time: 回档时间
        """
        # 获取距离回档时间最近的全备日志
        query_string = f"cluster: {self.cluster.id} AND pitr_file_type: {PitrFillType.FULL}"
        full_backup_logs, full_latest_index = self._query_latest_log_and_index(
            rollback_time, query_string, time_key="pitr_last_pos", flag=1
        )
        latest_full_backup_log = full_backup_logs[full_latest_index]

        # 找到与全备日志pitr_fullname相同的增量备份日志
        pitr_fullname = latest_full_backup_log["pitr_fullname"]
        query_string = (
            f"cluster: {self.cluster.id} AND pitr_file_type: {PitrFillType.INCR} AND pitr_fullname: {pitr_fullname}"
        )
        incr_backup_logs, incr_latest_index = self._query_latest_log_and_index(
            rollback_time, query_string, time_key="pitr_last_pos", flag=0
        )
        # 找到第一个大于等于rollback_time的增量备份ai, 此时a1, a2, ..., ai为合法的增量备份
        incr_backup_logs = incr_backup_logs[: incr_latest_index + 1]

        return {"full_backup_log": latest_full_backup_log, "incr_backup_logs": incr_backup_logs}

    def query_ticket_backup_log(self, start_time: datetime, end_time: datetime):
        """查询通过单据备份的备份记录"""
        backup_logs = self._get_log_from_bklog(
            collector="mongo_backup_result",
            start_time=start_time,
            end_time=end_time,
            query_string=f"cluster_id: {self.cluster.id} AND releate_bill_id: /[0-9]*/",
        )
        if not backup_logs:
            raise AppBaseException(_("{}-{}内没有通过单据备份的日志").format(start_time, end_time))

        return backup_logs
