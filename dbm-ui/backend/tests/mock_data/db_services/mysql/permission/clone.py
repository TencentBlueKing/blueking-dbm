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

CLONE_CLIENT_LIST_DATA = {
    "clone_type": "client",
    "clone_list": [
        {"source": "127.0.0.1", "target": "127.0.0.2\n127.0.0.3", "bk_cloud_id": 0},
        {"source": "127.0.1.1", "target": "127.0.0.2\n127.0.0.3", "bk_cloud_id": 0},
        {"source": "127.0.2.1", "target": "127.0.0.2\n127.0.0.3", "bk_cloud_id": 0},
    ],
}

EXCEL_CLONE_CLIENT_LIST_DATA = [
    {"旧客户端IP": "127.0.0.1", "新客户端IP": "127.0.0.2\n127.0.0.3", "bk_cloud_id": 0},
    {"旧客户端IP": "127.0.0.2", "新客户端IP": "127.0.0.2\n127.0.0.3", "bk_cloud_id": 0},
    {"旧客户端IP": "127.0.0.3", "新客户端IP": "127.0.0.2\n127.0.0.3", "bk_cloud_id": 0},
]
