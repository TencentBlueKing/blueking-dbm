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
import time

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.components import DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.flow.plugins.components.collections.common.base_service import BaseService


class MySQLCheckProcesslistService(BaseService):
    """
    检查slave当前30秒内是否检测到有链接
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
        self.log_info(
            _(
                """
    检查slave当前30秒内是否检测到有链接,步骤:
    1. 检查 show processlist 进程。
    2. 先 stop slave ,避免复制进程打开表
    3. flush tables
    4. 检查 show open tables
    5. 程序退出前 start slave。
        """
            )
        )
        check_flag = False
        try:
            res = DRSApi.rpc(rpc_info)
            if res[0]["error_msg"]:
                self.log_info("execute sql error {}".format(res[0]["error_msg"]))
                return False
            else:
                if res[0]["cmd_results"][0]["table_data"] is None or len(res[0]["cmd_results"][0]["table_data"]) == 0:
                    #  flush tables 前先 stop slave
                    rpc_info["cmds"] = ["stop slave"]
                    res = DRSApi.rpc(rpc_info)
                    if res[0]["error_msg"]:
                        self.log_info("execute sql error {}".format(res[0]["error_msg"]))
                        return False
                    time.sleep(10)
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
                    if (
                        res[0]["cmd_results"][0]["table_data"] is None
                        or len(res[0]["cmd_results"][0]["table_data"]) == 0
                    ):
                        check_flag = True
                        return True
                    else:
                        self.log_error(
                            _("实例: {},存在open table {}".format(instance, res[0]["cmd_results"][0]["table_data"]))
                        )
                        return False

                else:
                    self.log_error(_("实例: {},存在链接 {}".format(instance, res[0]["cmd_results"][0]["table_data"])))
                    return False
        finally:
            if not check_flag:
                rpc_info["cmds"] = ["start slave"]
                res = DRSApi.rpc(rpc_info)
                if res[0]["error_msg"]:
                    self.log_info("execute sql error {}".format(res[0]["error_msg"]))
                    self.log_info(_("检查不通过,且重新 start slave 失败,请手动介入处理"))
                    return False
            self.log_info("check finish")


class MySQLCheckProcesslistComponent(Component):
    name = __name__
    code = "mysql_check_processlist"
    bound_service = MySQLCheckProcesslistService
