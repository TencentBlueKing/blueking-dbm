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

# -*- coding: utf-8 -*-

import collections

from bamboo_engine.eri import State

from backend.tests.mock_data.ticket.mysql_flow import SQL_IMPORT_DATA, SQL_IMPORT_NODE_ID

NodeInput = collections.namedtuple(
    "NodeInput",
    [
        "data",
    ],
)

STATE_DATA = {
    "node_id": "efb0152xxxxxx6c5",
    "root_id": "2024051737b98b",
    "parent_id": "2024051737b98b",
    "name": "FINISHED",
    "version": "v3b180815xxxxxx4b992c",
    "loop": 1,
    "inner_loop": 1,
    "retry": 0,
    "skip": False,
    "error_ignored": False,
    "created_time": "",
    "started_time": "",
    "archived_time": "",
}


class BambooEngineMock(object):
    """bamboo engine类的mock"""

    def __init__(self, root_id):
        self.root_id = root_id

    def get_node_input_data(self, node_id):
        """可以根据不同的node_id，mock不同的输入数据"""
        node_input = NodeInput(data={})
        if node_id == SQL_IMPORT_NODE_ID:
            node_input.data["global_data"] = SQL_IMPORT_DATA["details"]

        return node_input

    def get_node_state(self, node_id):
        return State(**STATE_DATA)
