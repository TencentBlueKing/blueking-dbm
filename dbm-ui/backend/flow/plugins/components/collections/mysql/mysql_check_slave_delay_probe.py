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

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import StaticIntervalGenerator

from backend.components import DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.flow.plugins.components.collections.common.base_service import BkJobService

logger = logging.getLogger("flow")


class MySQLCheckSlaveDelayProbeService(BkJobService):
    """
    执行 show slave status 定时探测,自动通过
    """

    interval = StaticIntervalGenerator(30)

    def _execute(self, data, parent_data) -> bool:
        return True

    def _schedule(self, data, parent_data, callback_data=None):
        kwargs = data.get_one_of_inputs("kwargs")
        self.log_info(_("传入参数:{}").format(kwargs))
        res = DRSApi.rpc(
            {
                "addresses": ["{}{}{}".format(kwargs["instance_ip"], IP_PORT_DIVIDER, kwargs["instance_port"])],
                "cmds": ["show slave status"],
                "force": False,
                "bk_cloud_id": kwargs["bk_cloud_id"],
            }
        )
        if res[0]["error_msg"]:
            self.log_info("execute slave sql error {}".format(res[0]["error_msg"]))
            self.finish_schedule()
            return False
        else:
            if len(res[0]["cmd_results"][0]["table_data"]) == 0:
                self.log_info("show slave status is empty")
                self.finish_schedule()
                return False
            else:
                slave_info = res[0]["cmd_results"][0]["table_data"][0]
                self.log_debug(slave_info)
                # 查看主节点位点
                if kwargs["master_ip"] != "" or int(kwargs["master_port"]) != 0:
                    if slave_info["Master_Host"] != kwargs["master_ip"] or int(slave_info["Master_Port"]) != int(
                        kwargs["master_port"]
                    ):
                        self.log_info(_("请确定实例对应的主节点是否正确"))
                        self.finish_schedule()
                        return False
                if not (slave_info["Slave_IO_Running"] == "Yes" and slave_info["Slave_SQL_Running"] == "Yes"):
                    self.log_info(
                        _(
                            "复制链路错误: Slave_IO_Running: {} Slave_SQL_Running: {}".format(
                                slave_info["Slave_IO_Running"], slave_info["Slave_SQL_Running"]
                            )
                        )
                    )
                    self.finish_schedule()
                    return False
                res = DRSApi.rpc(
                    {
                        "addresses": [
                            "{}{}{}".format(slave_info["Master_Host"], IP_PORT_DIVIDER, slave_info["Master_Port"])
                        ],
                        "cmds": ["show master status"],
                        "force": False,
                        "bk_cloud_id": kwargs["bk_cloud_id"],
                    }
                )
                if res[0]["error_msg"]:
                    self.log_info("execute master sql error {}".format(res[0]["error_msg"]))
                    self.finish_schedule()
                    return False
                if len(res[0]["cmd_results"][0]["table_data"]) == 0:
                    self.log_info("show master status is empty")
                    self.finish_schedule()
                    return False
                master_info = res[0]["cmd_results"][0]["table_data"][0]
                self.log_debug(master_info)
                slave_delay = int(master_info["Position"]) - int(slave_info["Exec_Master_Log_Pos"])
                master_file_num = master_info["File"].strip().split(".")[-1]
                slave_file_num = slave_info["Relay_Master_Log_File"].strip().split(".")[-1]
                file_delay = int(master_file_num) - int(slave_file_num)

                if slave_delay > kwargs["slave_delay_threshold"] or (file_delay > kwargs["check_file_delay"] >= 0):
                    self.log_info(_("从库延迟过大: 延迟文件个数: {} 延迟位点: {}".format(file_delay, slave_delay)))
                else:
                    self.log_info(_("当前从库延迟: 延迟文件个数: {} 延迟位点: {}".format(file_delay, slave_delay)))
                    self.finish_schedule()
                    return True


class MySQLCheckSlaveDelayProbeComponent(Component):
    name = __name__
    code = "mysql_check_slave_delay_probe"
    bound_service = MySQLCheckSlaveDelayProbeService
