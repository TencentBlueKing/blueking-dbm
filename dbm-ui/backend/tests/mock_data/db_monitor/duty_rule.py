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
LIST_DUTY_RULE = [
    {
        "name": "周末轮值1",
        "priority": 1,
        "monitor_duty_rule_id": 0,
        "db_type": "mysql",
        "category": "handoff",
        "effective_time": "2023-09-05 00:00:00",
        "duty_arranges": [
            {
                "duty_number": 2,
                "duty_day": 1,
                "members": ["admin"],
                "work_type": "weekly",
                "work_days": [6, 7],
                "work_times": ["00:00--11:59", "12:00--23:59"],
            }
        ],
    },
    {
        "name": "周末轮值2",
        "priority": 1,
        "monitor_duty_rule_id": 0,
        "db_type": "kafka",
        "category": "handoff",
        "effective_time": "2023-09-05 00:00:00",
        "duty_arranges": [
            {
                "duty_number": 2,
                "duty_day": 1,
                "members": ["admin"],
                "work_type": "weekly",
                "work_days": [6, 7],
                "work_times": ["00:00--11:59", "12:00--23:59"],
            }
        ],
    },
    {
        "name": "周末轮值3",
        "priority": 2,
        "monitor_duty_rule_id": 0,
        "db_type": "mysql",
        "category": "handoff",
        "effective_time": "2023-09-05 00:00:00",
        "duty_arranges": [
            {
                "duty_number": 2,
                "duty_day": 1,
                "members": ["admin"],
                "work_type": "weekly",
                "work_days": [6, 7],
                "work_times": ["00:00--11:59", "12:00--23:59"],
            }
        ],
    },
]
