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
from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.spider.common.exceptions import CtlSwitchToSlaveFailedException
from backend.flow.plugins.components.collections.common.base_service import BaseService


class CtlDropRoutingService(BaseService):
    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")

        reduce_ctl = kwargs["reduce_ctl"]

        # 获取cluster对象
        cluster = Cluster.objects.get(id=kwargs["cluster_id"])
        ctl_primary = cluster.tendbcluster_ctl_primary_address()

        rpc_params = {
            "addresses": [ctl_primary],
            "cmds": [],
            "force": False,
            "bk_cloud_id": cluster.bk_cloud_id,
        }

        # 查询reduce_ctl对应的server_name
        reduce_ip = reduce_ctl.split(":")[0]
        reduce_port = reduce_ctl.split(":")[1]

        select_sql = [
            "set tc_admin = 1",
            f"select Server_name from mysql.servers where host = '{reduce_ip}' and port = {reduce_port}",
        ]
        rpc_params["cmds"] = select_sql
        res = DRSApi.rpc(rpc_params)
        if res[0]["error_msg"]:
            raise CtlSwitchToSlaveFailedException(
                message=_("select mysql.servers failed: {}".format(res[0]["error_msg"]))
            )

        if not res[0]["cmd_results"][1]["table_data"]:
            self.log_warning(f"Node [{reduce_ctl}] no longer has routing information")
            return True

        else:
            server_name = res[0]["cmd_results"][1]["table_data"][0]["Server_name"]

            # 删除节点路由信息
            exec_sql = [
                "set tc_admin=1",
                f"TDBCTL DROP NODE IF EXISTS {server_name}",
            ]
            rpc_params["cmds"] = exec_sql
            res = DRSApi.rpc(rpc_params)
            if res[0]["error_msg"]:
                raise CtlSwitchToSlaveFailedException(
                    message=_("exec TDBCTL-DROP-NODE failed: {}".format(res[0]["error_msg"]))
                )
            return True


class CtlDropRoutingComponent(Component):
    name = __name__
    code = "ctl_drop_routing"
    bound_service = CtlDropRoutingService
