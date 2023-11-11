# -*- coding: utf-8 -*-
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
from backend.core.encrypt.handlers import RSAHandler
from backend.flow.consts import AUTH_ADDRESS_DIVIDER
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptService
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload

logger = logging.getLogger("flow")


class PtTableSyncService(ExecuteDBActuatorScriptService):
    """
    定义通过pt-table-sync工具执行主从mysql实例之间的数据修复
    活动节点流程：
    1: 源和目标实例都需要加临时账号
    2: 执行pt-table-sync的db_actor命令
    3：删除临时账号(在第二步的db_actor命令执行)
    """

    def _execute(self, data, parent_data, callback=None) -> bool:

        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")

        # 例行校验而生成的修复单据，在单据信息获取节点信息
        slave_ip = global_data["slave_ip"]
        slave_port = global_data["slave_port"]
        master_ip = global_data["master_ip"]
        master_port = global_data["master_port"]

        cluster_info = {
            "slave_ip": slave_ip,
            "slave_port": slave_port,
            "master_ip": master_ip,
            "master_port": master_port,
            "sync_user": kwargs["sync_user"],
            "sync_pass": kwargs["sync_pass"],
            "check_sum_table": kwargs["check_sum_table"],
            "is_sync_non_innodb": global_data["is_sync_non_innodb"],
        }

        # 添加临时账号
        encrypt_switch_pwd = RSAHandler.encrypt_password(
            MySQLPrivManagerApi.fetch_public_key(), kwargs["sync_pass"], salt=None
        )
        params = {
            "bk_cloud_id": kwargs["bk_cloud_id"],
            "bk_biz_id": global_data["bk_biz_id"],
            "operator": global_data["created_by"],
            "user": kwargs["sync_user"],
            "psw": encrypt_switch_pwd,
            "dbname": "%",
            "dml_ddl_priv": "",
            "global_priv": "all privileges",
            "address": f"{master_ip}{AUTH_ADDRESS_DIVIDER}{master_port}",
            "hosts": [slave_ip],
        }
        MySQLPrivManagerApi.add_priv_without_account_rule(params=params)
        self.log_info(f"add sync user in master instance [{master_ip}:{master_port}]")

        params["address"] = f"{slave_ip}{AUTH_ADDRESS_DIVIDER}{slave_port}"
        MySQLPrivManagerApi.add_priv_without_account_rule(params=params)
        self.log_info(f"add sync user in slave instance [{slave_ip}:{slave_port}]")

        # 执行pt-table-sync 的 db-act命令
        data.get_one_of_inputs("kwargs")["bk_cloud_id"] = kwargs["bk_cloud_id"]
        data.get_one_of_inputs("kwargs")["get_mysql_payload_func"] = MysqlActPayload.get_pt_table_sync_payload.__name__
        data.get_one_of_inputs("kwargs")["exec_ip"] = slave_ip
        data.get_one_of_inputs("kwargs")["get_trans_data_ip_var"] = None
        data.get_one_of_inputs("kwargs")["cluster"] = cluster_info
        return super()._execute(data, parent_data)


class PtTableSyncComponent(Component):
    name = __name__
    code = "pt_table_sync"
    bound_service = PtTableSyncService
