"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from django.utils.translation import ugettext_lazy as _
from pipeline.component_framework.component import Component

from backend.components import DRSApi
from backend.db_meta.models import Cluster, ProxyInstance
from backend.flow.engine.bamboo.scene.spider.common.exceptions import DropSpiderNodeFailedException
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.spider.spider_db_function import get_flush_routing_sql_for_server


class DropSpiderRoutingService(BaseService):
    def flush_routing(self, ctl_master: str, bk_cloud_id: int):
        """
        @param ctl_master: 当前集群的中控primary
        @param bk_cloud_id: 云区域id
        """
        get_flush_routing_sql_list = get_flush_routing_sql_for_server(
            ctl_master=ctl_master,
            bk_cloud_id=bk_cloud_id,
        )
        self.log_info(f"exec flush_routing cmds:[{get_flush_routing_sql_list}]")

        # 如果返回为空，直接返回
        if not get_flush_routing_sql_list:
            return True

        res = DRSApi.rpc(
            {
                "addresses": [ctl_master],
                "cmds": ["set tc_admin=1"] + get_flush_routing_sql_list,
                "force": False,
                "bk_cloud_id": bk_cloud_id,
            }
        )
        if res[0]["error_msg"]:
            self.log_error(f"flush routing failed:[{res[0]['error_msg']}]")
            return False
        return True

    def _exec_drop_routing(self, cluster: Cluster, ctl_primary: str, spider: ProxyInstance, is_reduce_tdbctl: bool):
        """
        执行删除节点路由逻辑
        """

        rpc_params = {
            "addresses": [ctl_primary],
            "cmds": [],
            "force": False,
            "bk_cloud_id": cluster.bk_cloud_id,
        }
        if is_reduce_tdbctl:
            port = spider.admin_port
        else:
            port = spider.port

        select_sqls = [
            "set tc_admin=1",
            f"select Server_name from mysql.servers where host = '{spider.machine.ip}' and port = {port}",
        ]

        rpc_params["cmds"] = select_sqls
        res = DRSApi.rpc(rpc_params)

        if res[0]["error_msg"]:
            raise DropSpiderNodeFailedException(
                message=_("select mysql.servers failed: {}".format(res[0]["error_msg"]))
            )

        if not res[0]["cmd_results"][1]["table_data"]:
            self.log_warning(f"Node [{spider.machine.ip}:{spider.port}] no longer has routing information")
            return True

        else:
            server_name = res[0]["cmd_results"][1]["table_data"][0]["Server_name"]

            # 删除节点路由信息
            exec_sql = [
                "set tc_admin=1",
                f"TDBCTL DROP NODE IF EXISTS {server_name}",
            ]
            self.log_info(f"exec drop node cmds: [{exec_sql}]")
            rpc_params["cmds"] = exec_sql
            res = DRSApi.rpc(rpc_params)
            if res[0]["error_msg"]:
                raise DropSpiderNodeFailedException(
                    message=_("exec TDBCTL-DROP-NODE failed: {}".format(res[0]["error_msg"]))
                )
            return True

    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")

        reduce_spiders = kwargs["reduce_spiders"]
        is_reduce_tdbctl = kwargs["is_reduce_tdbctl"]
        cluster = Cluster.objects.get(id=kwargs["cluster_id"])
        ctl_primary = cluster.tendbcluster_ctl_primary_address()
        self.log_info(f"[{cluster.immute_domain}] the cluster_ctl_primary is {ctl_primary} ")

        for spider in reduce_spiders:
            # spider机器是专属于一套集群，单机单实例
            s = cluster.proxyinstance_set.get(machine__ip=spider["ip"])

            # 执行删除路由
            if is_reduce_tdbctl:
                self.log_info(f"exec drop node [{s.machine.ip}:{s.admin_port}]")
            else:
                self.log_info(f"exec drop node [{s.ip_port}]")
            self._exec_drop_routing(cluster, ctl_primary, s, is_reduce_tdbctl)

        # 统一刷新路由信息
        self.log_info("exec flush routing ....")
        if not self.flush_routing(ctl_master=ctl_primary, bk_cloud_id=cluster.bk_cloud_id):
            return False
        self.log_info("exec flush routing successfully")
        return True


class DropSpiderRoutingComponent(Component):
    name = __name__
    code = "drop_spider_routing"
    bound_service = DropSpiderRoutingService
