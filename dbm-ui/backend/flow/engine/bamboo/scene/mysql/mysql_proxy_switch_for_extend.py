"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from backend.flow.engine.bamboo.scene.mysql.mysql_proxy_cluster_switch import MySQLProxyClusterSwitchFlow


class ProxySwitchForExtendFlow(MySQLProxyClusterSwitchFlow):
    """
    构建mysql集群整体proxy实例扩缩容的流程类
    本质上 proxy的扩缩容，就是做proxy替换过程，所以流程可以复用proxy替换流程
    唯一的区别是扩缩容是必须要集群所有proxy实例进行替换，而替换则按需选择proxy
    兼容跨云区域的场景支持
    flow协议参考 proxy替换单据
    """

    def switch_proxy_for_extend_flow(self):
        """
        定义扩缩容proxy流程
        """
        self.switch_mysql_cluster_proxy_flow()
