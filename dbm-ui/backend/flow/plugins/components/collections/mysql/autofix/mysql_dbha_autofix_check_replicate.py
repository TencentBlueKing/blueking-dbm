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

from pipeline.component_framework.component import Component
from pipeline.core.flow import StaticIntervalGenerator

from backend.components import DRSApi
from backend.flow.plugins.components.collections.common.base_service import BaseService


class MySQLDBHAAutofixCheckReplicateService(BaseService):
    __need_schedule__ = True
    interval = StaticIntervalGenerator(10)

    def _execute(self, data, parent_data):
        """
        实际只检查 6 轮, 第一轮空跑当做 sleep 用
        因为有时候刚 change 完状态更新没那么快会误判失败
        """
        data.outputs.counter = 7
        return True

    def _schedule(self, data, parent_data, callback_data=None):
        counter = data.get_one_of_outputs("counter")
        kwargs = data.get_one_of_inputs("kwargs")

        bk_cloud_id = kwargs["bk_cloud_id"]
        address = kwargs["address"]
        master_host = kwargs["master_host"]
        master_port = kwargs["master_port"]

        self.log_info(f"show slave status on {address}")

        # 第一轮空跑
        if counter == 7:
            return True

        if counter > 0:
            counter -= 1
            data.outputs.counter = counter

            res = DRSApi.rpc(
                {"addresses": [address], "cmds": ["show slave status"], "bk_cloud_id": bk_cloud_id, "false": False}
            )
            if res[0]["error_msg"]:
                self.log_error("show slave status failed: {}".format(res[0]["error_msg"]))
                self.finish_schedule()
                return False

            if res[0]["cmd_results"][0]["error_msg"]:
                self.log_error("show slave status failed: {}".format(res[0]["cmd_results"][0]["error_msg"]))
                self.finish_schedule()
                return False

            slave_status = res[0]["cmd_results"][0]["table_data"][0]
            status_io_running = slave_status["Slave_IO_Running"]
            status_sql_running = slave_status["Slave_SQL_Running"]
            status_last_io_error = slave_status["Last_IO_Error"]
            status_last_io_errno = slave_status["Last_IO_Errno"]
            status_last_sql_error = slave_status["Last_SQL_Error"]
            status_last_sql_errno = slave_status["Last_SQL_Errno"]
            status_last_error = slave_status["Last_Error"]
            status_last_errno = slave_status["Last_Errno"]
            status_master_host = slave_status["Master_Host"]
            status_master_port = int(slave_status["Master_Port"])

            if not (status_master_host == master_host and status_master_port == master_port):
                self.log_error(f"bad master {status_master_host}:{status_master_port}!={master_port}:{master_port}")
                self.finish_schedule()
                return False

            if not (status_io_running.lower().strip() == "yes" and status_sql_running.lower().strip() == "yes"):
                self.log_error(
                    "bad status\n"
                    + f"Slave_IO_Running:{status_io_running}\n"
                    + f"Slave_SQL_Running:{status_sql_running}\n"
                    + f"Last_Errno:{status_last_errno}\n"
                    + f"Last_IO_Error:{status_last_error}\n"
                    + f"Last_SQL_Errno:{status_last_sql_errno}\n"
                    + f"Last_SQL_Error:{status_last_sql_error}\n"
                    + f"Last_IO_Errno:{status_last_io_errno}\n"
                    + f"Last_IO_Error:{status_last_io_error}"
                )
                self.finish_schedule()
                return False

            return True
        else:
            self.finish_schedule()
            return True


class MySQLDBHAAutofixCheckReplicateComponent(Component):
    name = __name__
    code = "mysql_dbha_autofix_check_replicate"
    bound_service = MySQLDBHAAutofixCheckReplicateService
