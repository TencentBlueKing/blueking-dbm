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

ACTION_CHECK_ALLOWED = [{"action_id": "mysql_apply", "is_allowed": True}]

GET_APPLY_DATA = {
    "permission": {
        "system_id": "bk_dbm",
        "system_name": "DB管理平台",
        "actions": [
            {
                "id": "mysql_apply",
                "name": "MySQL 部署",
                "related_resource_types": [
                    {
                        "system_id": "bk_cmdb",
                        "system_name": "配置平台",
                        "type": "biz",
                        "type_name": "业务",
                        "instances": [
                            [{"type": "biz", "type_name": "业务", "id": "1", "name": ""}],
                        ],
                    }
                ],
            }
        ],
    },
    "apply_url": "https://iam.example.com",
}
