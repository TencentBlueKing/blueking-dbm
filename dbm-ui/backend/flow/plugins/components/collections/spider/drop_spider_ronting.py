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

from backend.components import DBConfigApi, DRSApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.models import Cluster, ProxyInstance
from backend.flow.consts import MYSQL_SYS_USER, ConfigTypeEnum, NameSpaceEnum
from backend.flow.engine.bamboo.scene.mysql.common.get_mysql_sys_user import get_mysql_sys_users
from backend.flow.engine.bamboo.scene.spider.common.exceptions import DropSpiderNodeFailedException
from backend.flow.plugins.components.collections.common.base_service import BaseService


class DropSpiderRoutingService(BaseService):
    def _pre_check(self, cluster: Cluster, reduce_spider: ProxyInstance):
        """
        检测待下架的spider节点是否有存在访问
        """

        # 获取内置账号名称
        data = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": "0",
                "level_name": LevelName.PLAT,
                "level_value": "0",
                "conf_file": "mysql#user",
                "conf_type": ConfigTypeEnum.InitUser,
                "namespace": NameSpaceEnum.TenDB.value,
                "format": FormatType.MAP,
            }
        )["content"]
        mysql_user_name_list = [data["admin_user"], data["backup_user"], data["monitor_user"], data["repl_user"]]
        users = ",".join(
            [
                "'" + str(x) + "'"
                for x in MYSQL_SYS_USER + mysql_user_name_list + get_mysql_sys_users(cluster.bk_cloud_id)
            ]
        )

        cmds = [f"select * from information_schema.processlist where command != 'Sleep' and User not in ({users})"]
        res = DRSApi.rpc(
            {
                "addresses": [f"{reduce_spider.machine.ip}{IP_PORT_DIVIDER}{reduce_spider.port}"],
                "cmds": cmds,
                "force": False,
                "bk_cloud_id": cluster.bk_cloud_id,
            }
        )

        if res[0]["error_msg"]:
            raise DropSpiderNodeFailedException(message=_("select processlist failed: {}".format(res[0]["error_msg"])))

        if res[0]["cmd_results"][0]["table_data"]:
            self.log_error(f"There are also {res[0]['cmd_results'][1]['rows_affected']} non-sleep state threads")
            return False

        return True

    def _exec_drop_routing(self, cluster: Cluster, spider: ProxyInstance):
        """
        执行删除节点路由逻辑
        """
        ctl_primary = cluster.tendbcluster_ctl_primary_address()

        rpc_params = {
            "addresses": [ctl_primary],
            "cmds": [],
            "force": False,
            "bk_cloud_id": cluster.bk_cloud_id,
        }

        select_sqls = [
            "set tc_admin=1",
            f"select Server_name from mysql.servers where host = '{spider.machine.ip}' and port = {spider.port}",
        ]

        rpc_params["cmds"] = select_sqls
        res = DRSApi.rpc(rpc_params)

        if res[0]["error_msg"]:
            raise DropSpiderNodeFailedException(
                message=_("select mysql.servers failed: {}".format(res[0]["error_msg"]))
            )

        if not res[0]["cmd_results"][1]["table_data"]:
            self.log_warning(f"Node [{spider.ip_port}] no longer has routing information")
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
                raise DropSpiderNodeFailedException(
                    message=_("exec TDBCTL-DROP-NODE failed: {}".format(res[0]["error_msg"]))
                )
            return True

    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")

        reduce_spiders = kwargs["reduce_spiders"]
        is_safe = kwargs["is_safe"]
        cluster = Cluster.objects.get(id=kwargs["cluster_id"])

        for spider in reduce_spiders:
            # spider机器是专属于一套集群，单机单实例
            s = cluster.proxyinstance_set.get(machine__ip=spider["ip"])

            if is_safe:
                if not self._pre_check(cluster, s):
                    # 检测不通过退出
                    return False

            # 执行删除路由
            self.log_info(f"exec drop node [{s.ip_port}]")
            self._exec_drop_routing(cluster, s)
            return True


class DropSpiderRoutingComponent(Component):
    name = __name__
    code = "drop_spider_routing"
    bound_service = DropSpiderRoutingService
