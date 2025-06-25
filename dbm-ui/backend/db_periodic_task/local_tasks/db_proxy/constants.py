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
from backend import env
from backend.flow.consts import CloudServiceName

CLOUD_COMMON_UNIFY_QUERY_PARAMS = {
    "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
    "query_configs": [
        {
            "data_label": "process",
            "data_source_label": "bk_monitor",
            "data_type_label": "time_series",
            "group_by": ["process_name", "bk_target_ip"],
            "where": [{"condition": "and", "key": "process_name", "method": "eq", "value": []}],
            "metrics": [],
            "interval_unit": "s",
            "interval": 60,
        }
    ],
    "expression": "a",
    "alias": "a",
    # 单位：s
    "start_time": "",
    "end_time": "",
    "slimit": 500,
    "down_sample_range": "30s",
    "type": "range",
}


QUERY_TEMPLATE_CLOUD_MAP = {
    CloudServiceName.Nginx: {
        "metrics": [{"field": "alive", "method": "MAX", "alias": "a"}],
        "process_name": "nginx",
        "range": 5,
    },
    CloudServiceName.DRS: {
        "metrics": [{"field": "alive", "method": "MAX", "alias": "a"}],
        "process_name": "db-remote-service",
        "range": 5,
    },
    CloudServiceName.DBHA: {
        "metrics": [{"field": "cpu_start_time", "method": "AVG", "alias": "a"}],
        "process_name": "dbha",
        "range": 5,
    },
}
