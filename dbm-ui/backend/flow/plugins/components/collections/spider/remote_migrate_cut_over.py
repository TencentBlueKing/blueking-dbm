"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import logging

from pipeline.component_framework.component import Component

from backend.components import MySQLPrivManagerApi
from backend.core.encrypt.handlers import AsymmetricHandler
from backend.db_meta.models import Cluster
from backend.flow.consts import TDBCTL_USER
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptService
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload

logger = logging.getLogger("flow")


class RemoteMigrateCutOverService(ExecuteDBActuatorScriptService):
    """
    定义执行tendbcluster的remote成对切换的活动
    活动节点流程：
    1: 给新机器都需要加内置账号
    2: 执行成对切换的db_actor命令
    """

    def _execute(self, data, parent_data, callback=None) -> bool:

        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")

        cluster = Cluster.objects.get(id=global_data["cluster_id"])
        ctl_primary = cluster.tendbcluster_ctl_primary_address()

        # 添加临时账号
        encrypt_switch_pwd = AsymmetricHandler.encrypt_with_pubkey(
            pubkey=MySQLPrivManagerApi.fetch_public_key(), content=global_data["tdbctl_pass"]
        )

        params = {
            "bk_cloud_id": cluster.bk_cloud_id,
            "bk_biz_id": global_data["bk_biz_id"],
            "operator": global_data.get("created_by", ""),
            "user": TDBCTL_USER,
            "psw": encrypt_switch_pwd,
            "dbname": "%",
            "dml_ddl_priv": "",
            "global_priv": "all privileges",
            "address": "",
            "hosts": [ctl_primary.split(":")[0]],
        }

        for info in global_data["migrate_tuples"]:
            params["address"] = info["new_master"]
            MySQLPrivManagerApi.add_priv_without_account_rule(params=params)
            self.log_info(f"add tdbctl user in master instance [{info['new_master']}]")

            params["address"] = info["new_slave"]
            MySQLPrivManagerApi.add_priv_without_account_rule(params=params)
            self.log_info(f"add tdbctl user in slave instance [{info['new_slave']}]")

        # 执行pt-table-sync 的 db-act命令
        data.get_one_of_inputs("kwargs")["bk_cloud_id"] = cluster.bk_cloud_id
        data.get_one_of_inputs("kwargs")[
            "get_mysql_payload_func"
        ] = MysqlActPayload.tendb_cluster_remote_migrate.__name__
        data.get_one_of_inputs("kwargs")["exec_ip"] = ctl_primary.split(":")[0]
        return super()._execute(data, parent_data)


class RemoteMigrateCutOverComponent(Component):
    name = __name__
    code = "remote_migrate_cut_over"
    bound_service = RemoteMigrateCutOverService
