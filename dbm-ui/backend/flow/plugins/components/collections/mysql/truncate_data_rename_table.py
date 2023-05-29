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
from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

import backend.flow.utils.mysql.mysql_context_dataclass as flow_context
from backend.components.db_remote_service.client import DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.flow.plugins.components.collections.common.base_service import BaseService


class TruncateDataRenameTableService(BaseService):
    def _execute(self, data, parent_data) -> bool:
        """
        bk_cloud_id 统一由私有变量kwargs传入
        """
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        global_data = data.get_one_of_inputs("global_data")

        ip = global_data["ip"]
        port = global_data["port"]

        old_new_map = trans_data.old_new_map

        self.log_info("[{}] targets: {}".format(kwargs["node_name"], trans_data.targets))
        self.log_info("[{}] old_new_map: {}".format(kwargs["node_name"], old_new_map))

        for db in trans_data.targets:
            new_db_name = old_new_map[db]
            # 每次一张表, 结合 processed 状态
            # 可以让这个步骤反复执行
            for table_name in trans_data.targets[db]:
                processed = trans_data.targets[db][table_name]
                if processed:
                    self.log_info("{} {} had been processed".format(db, table_name))
                    continue

                rename_db_res = DRSApi.rpc(
                    {
                        "addresses": ["{}{}{}".format(ip, IP_PORT_DIVIDER, port)],
                        "cmds": [
                            "rename table `{}`.`{}` to `{}`.`{}`".format(db, table_name, new_db_name, table_name)
                        ],
                        "force": False,
                        "bk_cloud_id": kwargs["bk_cloud_id"],
                    }
                )
                self.log_info(
                    "[{}] rename table {}.{} to {}.{} on {}{}{} response: {}".format(
                        kwargs["node_name"],
                        db,
                        table_name,
                        new_db_name,
                        table_name,
                        ip,
                        IP_PORT_DIVIDER,
                        port,
                        rename_db_res,
                    )
                )
                if rename_db_res[0]["error_msg"]:
                    self.log_error(
                        "[{}] rename table {}.{} to {}.{} on {}{}{} failed: {}".format(
                            kwargs["node_name"],
                            db,
                            table_name,
                            new_db_name,
                            table_name,
                            ip,
                            IP_PORT_DIVIDER,
                            port,
                            rename_db_res[0]["error_msg"],
                        )
                    )
                    return False

                trans_data.targets[db][table_name] = True

        self.log_info(_("[{}] 备份清档表完成").format(kwargs["node_name"]))
        data.outputs["trans_data"] = trans_data
        return True


class TruncateDataRenameTableComponent(Component):
    name = __name__
    code = "truncate_data_rename_table"
    bound_service = TruncateDataRenameTableService
