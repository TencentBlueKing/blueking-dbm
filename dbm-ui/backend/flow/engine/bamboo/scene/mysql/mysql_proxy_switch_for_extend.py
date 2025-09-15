"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from django.utils.translation import ugettext as _

from backend.flow.engine.bamboo.scene.mysql.common.exceptions import ProxyFlowFailedException
from backend.flow.engine.bamboo.scene.mysql.mysql_proxy_cluster_switch import MySQLProxyClusterSwitchFlow


class ProxySwitchForExtendFlow(MySQLProxyClusterSwitchFlow):
    """
    构建mysql集群整体proxy实例扩缩容的流程类
    本质上 proxy的扩缩容，就是做proxy替换过程，所以流程可以复用proxy替换流程
    唯一的区别是扩缩容是必须要集群所有proxy实例进行替换，而替换则按需选择proxy
    兼容跨云区域的场景支持
    {
        "uid": "2022051612120001",
        "created_by": "xxx",
        "bk_biz_id": "152",
        "ticket_type": "MYSQL_PROXY_SWITCH_FOR_MIGRATE",
        "is_safe": true/false # 是否安全模式，默认True,
        "infos": [ #对应前端每一行的入参信息
              {
                "cluster_ids": [1,2], # 选择的集群ID列表
                "target_spec" : {},  # 最终的目标规格信息
                "origin_proxy_ips":[
                    {
                        "ip": "2.2.2.2",
                        "bk_cloud_id": 0,
                        "bk_host_id": 2,
                        "bk_biz_id": 2005000002,
                        "spce":{...}
                    }, ...
                ] # 旧proxy 机器的信息 （选择集群后，自动渲染出来）
                "target_proxy_ips":[
                    {
                        "ip": "2.2.2.2",
                        "bk_cloud_id": 0,
                        "bk_host_id": 2,
                        "bk_biz_id": 2005000002,
                        "spce":{...}
                    }, ....
                ] # 新proxy 机器信息
              }
        ]
    }
    """

    def tran_ticket_data_for_flow(self):
        """
        将传入的ticket_data参数，转换成proxy替换流程MySQLProxyClusterSwitchFlow支持的参数
        """
        new_infos = []
        for info in self.data["infos"]:
            # 根据origin_proxy_ips和target_proxy_ips的维度，拆开重新赋值到new_info列表，
            # 首先要判断每一行origin_proxy_ips/target_proxy_ips的长度是否一致，如果不一致，则代表机器申请资源不对等，抛出异常
            if len(info["origin_proxy_ips"]) != len(info["target_proxy_ips"]):
                raise ProxyFlowFailedException(_("替换的主机数量和新申请到的主机数量不相等"))

            for index, origin_proxy_ip in enumerate(info["origin_proxy_ips"]):
                target_proxy_ip = info["target_proxy_ips"][index]
                new_infos.append(
                    {
                        "origin_proxy_ip": origin_proxy_ip,
                        "target_proxy_ip": target_proxy_ip,
                        "cluster_ids": info["cluster_ids"],
                    }
                )
        # 返回更新后的数据
        self.data["infos"] = new_infos
        return None

    def switch_proxy_for_extend_flow(self):
        """
        定义扩缩容proxy流程
        """
        self.tran_ticket_data_for_flow()
        self.switch_mysql_cluster_proxy_flow()
