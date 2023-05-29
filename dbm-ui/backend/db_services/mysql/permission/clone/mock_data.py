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


CLONE_INSTANCE_DATA = {"source_address": "127.0.0.1:20000", "target_address": "127.0.0.2:20000"}
CLONE_INSTANCE_LIST_DATA = {
    "clone_type": "instance",
    "clone_list": [
        {"source": "127.0.0.1:20000", "target": "127.0.0.2:20000", "module": "biz/svr1/game1"},
        {"source": "127.0.0.1:20001", "target": "127.0.0.2:20001", "module": "biz/svr1/game1"},
        {"source": "127.0.0.1:20002", "target": "127.0.0.2:20002", "module": "biz/svr1/game1"},
    ],
}

CLONE_CLIENT_LIST_DATA = {
    "clone_type": "client",
    "clone_list": [
        {"source": "127.0.0.1", "target": "127.0.0.2\n127.0.0.3", "module": "biz/svr1/game1"},
        {"source": "127.0.1.1", "target": "127.0.0.2\n127.0.0.3", "module": "biz/svr1/game1"},
        {"source": "127.0.2.1", "target": "127.0.0.2\n127.0.0.3", "module": "biz/svr1/game1"},
    ],
}

CLONE_INSTANCE_LIST_RESPONSE_DATA = {
    "pre_check": True,
    "message": "ok",
    "clone_uid": "7d9d698c35b111edb0abc2afcf9e926b",
    "clone_data_list": [
        {"source": "127.0.0.1:20000", "target": "127.0.0.2:20000", "message": "Permission clone succeeded"},
        {"source": "127.0.0.1:20001", "target": "127.0.0.2:20001", "message": "Permission clone succeeded"},
        {"source": "127.0.0.1:20002", "target": "127.0.0.2:20002", "message": "Permission clone succeeded"},
    ],
}

CLONE_EXCEL_INSTANCE_LIST_RESPONSE_DATA = {
    "pre_check": True,
    "clone_uid": "7d9d698c35b111edb0abc2afcf9e926b",
    "excel_url": "http://example.com",
}
