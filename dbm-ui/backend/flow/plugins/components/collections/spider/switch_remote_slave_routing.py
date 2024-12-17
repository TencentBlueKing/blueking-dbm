"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from pipeline.component_framework.component import Component

from backend.components import DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.models import Cluster
from backend.flow.consts import TDBCTL_USER
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.mysql.mysql_commom_query import create_tdbctl_user_for_remote


class SwitchRemoteSlaveRoutingService(BaseService):
    """
    定义spider(tenDB cluster)集群的替换remote slave实例的路由关系
    """

    def _alter_remote_slave_routing(
        self,
        cluster: Cluster,
        server_name: str,
        old_ip: str,
        old_port: int,
        new_ip: str,
        new_port: int,
        tdbctl_pass: str,
    ):
        """
        替换实例的路由信息的具体逻辑
        @param cluster: 关联操作的cluster对象
        @param old_ip: 待替换实例的ip
        @param old_port: 待替换实例的port
        @param new_ip: 新实例的ip
        @param new_port: 新实例的port
        @param tdbctl_pass: 新实例
        """

        # 获取最新cluster的中控 primary节点
        ctl_primary = cluster.tendbcluster_ctl_primary_address()

        rpc_params = {
            "addresses": [ctl_primary],
            "cmds": [
                "set tc_admin=1",
                f"select Server_name from mysql.servers where Server_name = '{server_name}'",
            ],
            "force": False,
            "bk_cloud_id": cluster.bk_cloud_id,
        }
        # drs服务远程请求
        res = DRSApi.rpc(rpc_params)

        if res[0]["error_msg"]:
            self.log_error(f"select mysql.servers failed: {res[0]['error_msg']}")
            return False

        if not res[0]["cmd_results"][1]["table_data"]:
            self.log_error(f"Node [{old_ip}{IP_PORT_DIVIDER}{old_port}] no longer has routing information")
            return False

        # 添加tdbctl账号
        create_tdbctl_user_for_remote(
            cluster=cluster, ctl_primary=ctl_primary, new_ip=new_ip, new_port=new_port, tdbctl_pass=tdbctl_pass
        )

        # 获取待切换的分片信息，拼接alter node语句
        server_name = res[0]["cmd_results"][1]["table_data"][0]["Server_name"]

        # 执行替换节点路由信息
        exec_sql = [
            "set tc_admin=1",
            f"TDBCTL ALTER NODE "
            f"{server_name} OPTIONS(host '{new_ip}', port {new_port}, password '{tdbctl_pass}', user '{TDBCTL_USER}')",
            "TDBCTL FLUSH ROUTING",
        ]
        rpc_params["cmds"] = exec_sql
        res = DRSApi.rpc(rpc_params)
        if res[0]["error_msg"]:
            self.log_error(f"exec TDBCTL-ALTER-NODE failed: {res[0]['error_msg']}")
            return False

        self.log_info(f"exec TDBCTL-ALTER-NODE success: [{server_name}->{new_ip}:{new_port}]")
        return True

    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")

        switch_remote_instance_pairs = kwargs["switch_remote_instance_pairs"]

        # 获取cluster对象，包括中控实例、 spider端口等
        cluster = Cluster.objects.get(id=kwargs["cluster_id"])
        for pairs in switch_remote_instance_pairs:
            if not self._alter_remote_slave_routing(
                cluster=cluster,
                old_ip=pairs["old_ip"],
                old_port=pairs["old_port"],
                new_ip=pairs["new_ip"],
                new_port=pairs["new_port"],
                server_name=pairs["server_name"],
                tdbctl_pass=pairs["tdbctl_pass"],
            ):
                return False

        return True


class SwitchRemoteSlaveRoutingComponent(Component):
    name = __name__
    code = "switch_remote_slave_routing"
    bound_service = SwitchRemoteSlaveRoutingService
