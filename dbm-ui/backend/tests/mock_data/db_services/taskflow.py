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

# 流程树数据
TREE_DATA = {
    "id": "0006e5f639a911ed97a4c2afcf9e926b",
    "data": {"outputs": [], "pre_render_keys": []},
    "flows": {
        "f8ea8100ec7e54c3089e29fd3e35ab642": {
            "id": "f8ea8100ec7e54c3089e29fd3e35ab642",
            "source": "ea88cad9613794244a915a0a17afd69c6",
            "target": "ed8ddc04ae8824d05ba98ed8888a16ce6",
            "is_default": False,
        },
        "feaa53b43faef4ccca7f2111464eb049d": {
            "id": "feaa53b43faef4ccca7f2111464eb049d",
            "source": "e657e2a54081d47ea855d4b426c7d6063",
            "target": "ea88cad9613794244a915a0a17afd69c6",
            "is_default": False,
        },
    },
    "gateways": {},
    "end_event": {
        "id": "ed8ddc04ae8824d05ba98ed8888a16ce6",
        "name": None,
        "type": "EmptyEndEvent",
        "incoming": ["f8ea8100ec7e54c3089e29fd3e35ab642"],
        "outgoing": "",
    },
    "activities": {
        "ea88cad9613794244a915a0a17afd69c6": {
            "id": "ea88cad9613794244a915a0a17afd69c6",
            "name": "虚假执行",
            "type": "ServiceActivity",
            "timeout": None,
            "incoming": ["feaa53b43faef4ccca7f2111464eb049d"],
            "optional": False,
            "outgoing": "f8ea8100ec7e54c3089e29fd3e35ab642",
            "component": {"code": "fake_execute"},
            "retryable": True,
            "skippable": True,
            "error_ignorable": False,
        }
    },
    "start_event": {
        "id": "e657e2a54081d47ea855d4b426c7d6063",
        "name": None,
        "type": "EmptyStartEvent",
        "incoming": "",
        "outgoing": "feaa53b43faef4ccca7f2111464eb049d",
    },
}

ROOT_ID = "9cf961d23a2511edbf0bc2afcf9e926b"
NODE_ID = "ed8ddc04ae8824d05ba98ed8888a16ce6"
VERSION_ID = "v60935b6accd647829341b5b062b947c4"
