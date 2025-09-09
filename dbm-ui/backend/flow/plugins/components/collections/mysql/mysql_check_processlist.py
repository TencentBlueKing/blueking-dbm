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
import time

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.components import DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


class MySQLCheckProcesslistService(BaseService):
    """
    检查 show processlist 进程
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        self.log_info(_("传入参数:{}").format(kwargs))
        self.log_info(_("如果检查不通过,根据您实际需求来选择跳过此节点。"))
        instance = "{}{}{}".format(kwargs["instance_ip"], IP_PORT_DIVIDER, kwargs["instance_port"])
        rpc_info = {
            "addresses": [instance],
            "cmds": [
                """select * from information_schema.processlist  where
User not in ('event_scheduler', 'system user','yw', 'MONITOR', 'ADMIN') and
DB not in ('mysql', 'sys', 'information_schema','performance_schema','test', 'infodba_schema', 'db_infobase')"""
            ],
            "force": False,
            "bk_cloud_id": kwargs["bk_cloud_id"],
        }

        res = DRSApi.rpc(rpc_info)
        if res[0]["error_msg"]:
            self.log_info("execute sql error {}".format(res[0]["error_msg"]))
            return False
        else:
            if res[0]["cmd_results"][0]["table_data"] is None or len(res[0]["cmd_results"][0]["table_data"]) == 0:
                rpc_info["cmds"] = ["flush tables"]
                res = DRSApi.rpc(rpc_info)
                if res[0]["error_msg"]:
                    self.log_info("execute sql error {}".format(res[0]["error_msg"]))
                    return False
                time.sleep(31)
                rpc_info["cmds"] = [
                    """show open tables where `Database`  not in ('mysql', 'sys', 'information_schema',
'performance_schema', 'test', 'infodba_schema', 'db_infobase')"""
                ]
                res = DRSApi.rpc(rpc_info)
                if res[0]["error_msg"]:
                    self.log_info("execute sql error {}".format(res[0]["error_msg"]))
                    return False
                if res[0]["cmd_results"][0]["table_data"] is None or len(res[0]["cmd_results"][0]["table_data"]) == 0:
                    return True
                else:
                    self.log_error(
                        _("实例: {},存在open table {}".format(instance, res[0]["cmd_results"][0]["table_data"]))
                    )
                    return False

            else:
                self.log_error(_("实例: {},存在链接 {}".format(instance, res[0]["cmd_results"][0]["table_data"])))
                return False


class MySQLCheckProcesslistComponent(Component):
    name = __name__
    code = "mysql_check_processlist"
    bound_service = MySQLCheckProcesslistService
