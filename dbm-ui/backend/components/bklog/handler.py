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
import logging
from datetime import datetime
from typing import Dict, List

from backend import env
from backend.components import BKLogApi
from backend.utils.string import pascal_to_snake
from backend.utils.time import datetime2str

logger = logging.getLogger("root")


class BKLogHandler(object):
    """封装bklog查询的通用函数"""

    @classmethod
    def query_logs(
        cls,
        collector: str,
        start_time: datetime,
        end_time: datetime,
        query_string="*",
        size=1000,
        sorting_rule: str = "asc",
    ) -> List[Dict]:
        """
        从日志平台获取对应采集项的日志
        @param collector: 采集项名称
        @param start_time: 开始时间
        @param end_time: 结束时间
        @param query_string: 过滤条件
        @param size: 返回条数，-1表示无限制
        @param sorting_rule: 排序规则，默认是 asc升序； desc倒序
        """
        total_backup_logs = []
        search_after = []

        while len(total_backup_logs) < size or size == -1:
            resp = BKLogApi.esquery_search(
                {
                    "indices": f"{env.DBA_APP_BK_BIZ_ID}_bklog.{collector}",
                    "start_time": datetime2str(start_time),
                    "end_time": datetime2str(end_time),
                    "query_string": query_string,
                    "start": 0,
                    "size": 1000,
                    "sort_list": [
                        ["dtEventTimeStamp", sorting_rule],
                        ["gseIndex", sorting_rule],
                        ["iterationIndex", sorting_rule],
                    ],
                    "search_after": search_after,
                },
                use_admin=True,
            )

            # 格式化日志结构
            backup_logs = []
            for hit in resp["hits"]["hits"]:
                raw_log = json.loads(hit["_source"]["log"])
                backup_logs.append({pascal_to_snake(key): value for key, value in raw_log.items()})

            # 无更多日志则退出
            if not backup_logs:
                break

            # 加入格式化日志，并更新搜索起始索引
            total_backup_logs.extend(backup_logs)
            search_after = resp["hits"]["hits"][-1]["sort"]

        return total_backup_logs[:size]
