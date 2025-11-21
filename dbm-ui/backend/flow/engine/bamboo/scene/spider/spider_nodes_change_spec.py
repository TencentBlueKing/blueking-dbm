"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from backend.flow.engine.bamboo.scene.spider.spider_switch_nodes import TenDBClusterSwitchNodesFlow


class TenDBClusterNodesChangeSpecFlow(TenDBClusterSwitchNodesFlow):
    """
    基于spider替换的flow基类，定义集群spider整体升降配的flow
    整体的划分，基于集群的spider角色去界定，比如用户在一个单据里，只能处理某个spider角色的整体升降配
    ticket_data参数：参考spider替换
    """

    def run_flow(self):
        self.switch_spider_nodes()
