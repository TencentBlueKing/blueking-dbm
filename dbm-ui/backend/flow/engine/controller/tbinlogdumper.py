"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from backend.flow.engine.bamboo.scene.tbinlogdumper.add_nodes import TBinlogDumperAddNodesFlow
from backend.flow.engine.bamboo.scene.tbinlogdumper.reduce_node import TBinlogDumperReduceNodesFlow
from backend.flow.engine.bamboo.scene.tbinlogdumper.switch_nodes import TBinlogDumperSwitchNodesFlow
from backend.flow.engine.controller.base import BaseController


class TBinlogDumperController(BaseController):
    """
    TBinlogDumper相关调用
    """

    def add_nodes_scene(self):
        flow = TBinlogDumperAddNodesFlow(root_id=self.root_id, data=self.ticket_data)
        flow.add_nodes()

    def reduce_nodes_scene(self):
        flow = TBinlogDumperReduceNodesFlow(root_id=self.root_id, data=self.ticket_data)
        flow.reduce_nodes()

    def switch_nodes_scene(self):
        flow = TBinlogDumperSwitchNodesFlow(root_id=self.root_id, data=self.ticket_data)
        flow.switch_nodes()
