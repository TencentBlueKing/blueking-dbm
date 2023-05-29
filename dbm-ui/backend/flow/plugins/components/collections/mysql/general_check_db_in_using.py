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

from backend.components.db_remote_service.client import DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.flow.consts import TruncateDataTypeEnum
from backend.flow.plugins.components.collections.common.base_service import BaseService


class GeneralCheckDBInUsingService(BaseService):
    """
    输入:
    1. global_data 中
    {
    "ip": str,
    "port": int
    }
    2. trans_data.targets
    {
    "db_name": {
                "table_name": false,
                ....
               }
    ....
    }
    """

    __need_schedule__ = True
    interval = StaticIntervalGenerator(10)

    def _execute(self, data, parent_data) -> bool:
        """
        bk_cloud_id 统一由私有变量kwargs传入
        """
        data.outputs.counter = 6
        return True

    def _schedule(self, data, parent_data, callback_data=None):
        counter = data.get_one_of_outputs("counter")
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        global_data = data.get_one_of_inputs("global_data")

        ip = global_data["ip"]
        port = global_data["port"]
        targets = trans_data.targets
        truncate_data_type = global_data["truncate_data_type"]

        if counter > 0:
            counter -= 1
            self.log_info("[{}] {} round flush tables left".format(kwargs["node_name"], counter))

            flush_table_res = DRSApi.rpc(
                {
                    "addresses": ["{}{}{}".format(ip, IP_PORT_DIVIDER, port)],
                    "cmds": ["flush tables"],
                    "force": False,
                    "bk_cloud_id": kwargs["bk_cloud_id"],
                }
            )
            self.log_info("[{}] flush tables response: {}".format(kwargs["node_name"], flush_table_res))
            if flush_table_res[0]["error_msg"]:
                self.log_error(
                    "[{}] flush tables on {}{}{} failed: {}".format(
                        kwargs["node_name"], ip, IP_PORT_DIVIDER, port, flush_table_res[0]["error_msg"]
                    )
                )
                self.finish_schedule()
                return False

            data.outputs.counter = counter
            return True
        else:
            show_open_table_res = DRSApi.rpc(
                {
                    "addresses": ["{}{}{}".format(ip, IP_PORT_DIVIDER, port)],
                    "cmds": ["show open tables"],
                    "force": False,
                    "bk_cloud_id": kwargs["bk_cloud_id"],
                }
            )
            self.log_info("[{}] show open tables response: {}".format(kwargs["node_name"], show_open_table_res))
            if show_open_table_res[0]["error_msg"]:
                self.log_error(
                    "[{}] show open tables on {}{}{} failed: {}".format(
                        kwargs["node_name"], ip, IP_PORT_DIVIDER, port, show_open_table_res[0]["error_msg"]
                    )
                )
                data.outputs.ext_result = False
                self.finish_schedule()
                return False

            reopened_targets = []
            for row in show_open_table_res[0]["cmd_results"][0]["table_data"]:
                db = row["Database"]
                tbl = row["Table"]

                if truncate_data_type == TruncateDataTypeEnum.DROP_DATABASE.value:
                    if db in targets:
                        reopened_targets.append(db)
                else:
                    if db in targets and tbl in targets[db]:
                        reopened_targets.append("{}.{}".format(db, tbl))

            if reopened_targets:
                self.log_info("[{}] check db/table using failed: {}".format(kwargs["node_name"], reopened_targets))
                self.finish_schedule()
                return False
            else:
                self.log_info("[{}] check db/table using pass".format(kwargs["node_name"]))
                self.finish_schedule()
                return True


class GeneralCheckDBInUsingComponent(Component):
    name = __name__
    code = "check_db_in_using"
    bound_service = GeneralCheckDBInUsingService
