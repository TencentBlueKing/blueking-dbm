"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from backend.flow.engine.bamboo.scene.spider.spider_add_nodes import TenDBClusterAddNodesFlow
from backend.flow.engine.bamboo.scene.spider.spider_switch_nodes import TenDBClusterSwitchNodesFlow
from backend.flow.engine.controller.base import BaseController


class RevokeController(BaseController):
    """
    这里是定义revoke(单据终止后触发主机退回流程)之后，不同单据类型调用相对应的 revoke流程
    该类是唯一的，定义所有单据的revoke的流程的访问入口
    每个revoke流程的 def 函数名称，规定用相对应的单据名称小写命名，才能让SaaS层找到并调用， 比如单据名称是abc , 则对应是 def abc()...
    想了解所有的单据名称，查询定义：TicketType
    """

    # tendbcluster 相关
    def tendbcluster_spider_add_nodes(self):
        """
        spider扩容单据（tendbcluster_spider_add_nodes）对应revoke flow
        """
        flow = TenDBClusterAddNodesFlow(root_id=self.root_id, data=self.ticket_data)
        flow.revoke_flow()

    def tendbcluster_spider_switch_nodes(self):
        """
        spider替换单据（tendbcluster_spider_switch_nodes）对应revoke flow
        """
        flow = TenDBClusterSwitchNodesFlow(root_id=self.root_id, data=self.ticket_data)
        flow.revoke_flow()
