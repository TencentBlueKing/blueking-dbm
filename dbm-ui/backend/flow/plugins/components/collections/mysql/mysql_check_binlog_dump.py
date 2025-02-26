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

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.components import DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


class MySQLCheckBinlogDumpService(BaseService):
    """
    检查 binlog dump 进程
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        self.log_info(_("传入参数:{}").format(kwargs))
        self.log_info(_("检查从库是否延迟,如果检查不通过,根据您实际需求来选择跳过此节点。"))
        res = DRSApi.rpc(
            {
                "addresses": ["{}{}{}".format(kwargs["instance_ip"], IP_PORT_DIVIDER, kwargs["instance_port"])],
                "cmds": ["select ID,USER,HOST from information_schema.PROCESSLIST where COMMAND like 'Binlog Dump%'"],
                "force": False,
                "bk_cloud_id": kwargs["bk_cloud_id"],
            }
        )
        if res[0]["error_msg"]:
            self.log_info("execute sql error {}".format(res[0]["error_msg"]))
            return False
        else:
            if len(res[0]["cmd_results"][0]["table_data"]) == 0:
                return True
            else:
                self.log_error(
                    _(
                        "实例存在Binlog Dump进程: {},原地slave重建会对其从库有影响,请谨慎确认".format(
                            res[0]["cmd_results"][0]["table_data"]["HOST"]
                        )
                    )
                )
                return False


class MySQLCheckBinlogDumpComponent(Component):
    name = __name__
    code = "mysql_check_binlog_dump"
    bound_service = MySQLCheckBinlogDumpService
