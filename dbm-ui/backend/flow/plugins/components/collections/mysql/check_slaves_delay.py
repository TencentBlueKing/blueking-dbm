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
from backend.flow.consts import INFODBA_SCHEMA
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


class CheckSlavesDelayService(BaseService):
    """
    执行 show slave status 语句
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        self.log_info(_("传入参数:{}").format(kwargs))
        slave_instance_tuples = kwargs["slave_addr_tuples"]
        allow_delay_sec = kwargs["allow_delay_sec"]
        for slave_addr in slave_instance_tuples:
            self.log_info(_("检查从库延迟"))
            res = DRSApi.rpc(
                {
                    "addresses": [slave_addr],
                    "cmds": ["show slave status"],
                    "force": False,
                    "bk_cloud_id": kwargs["bk_cloud_id"],
                }
            )
            res2 = DRSApi.rpc(
                {
                    "addresses": [slave_addr],
                    "cmds": [
                        (
                            "SELECT delay_sec,min(timestampdiff(SECOND, master_time, now())) beat_sec "
                            " FROM {}.master_slave_heartbeat "
                            " WHERE slave_server_id = @@server_id and slave_server_id != master_server_id "
                        ).format(INFODBA_SCHEMA)
                    ],
                    "force": False,
                    "bk_cloud_id": kwargs["bk_cloud_id"],
                }
            )
            if res[0]["error_msg"]:
                self.log_error("execute sql error {}".format(res[0]["error_msg"]))
                return False
            if res2[0]["error_msg"]:
                self.log_error("execute sql error {}".format(res2[0]["error_msg"]))
                return False
            if len(res[0]["cmd_results"][0]["table_data"]) == 0:
                self.log_error("show slave status is empty")
                return False
            if len(res2[0]["cmd_results"][0]["table_data"]) == 0:
                self.log_error("quwey master_slave_heartbeat result is empty")
                return False
            slave_info = res[0]["cmd_results"][0]["table_data"][0]
            slave_delay = 0
            if slave_info["Seconds_Behind_Master"] is not None:
                slave_delay = int(slave_info["Seconds_Behind_Master"])
            real_delay_sec = int(res2[0]["cmd_results"][0]["table_data"][0]["delay_sec"])
            beat_sec = int(res2[0]["cmd_results"][0]["table_data"][0]["beat_sec"])
            if beat_sec > 600:
                self.log_error(_("心跳表最近10分钟都没更新,请检查下 ~"))
                return False
            if real_delay_sec > allow_delay_sec:
                self.log_error(_("心跳表记录的主从库延迟超过{}s,请确认从库复制链路正常且延迟不能超过{}s").format(allow_delay_sec, allow_delay_sec))
                return False
            if (
                slave_info["Slave_IO_Running"] == "Yes"
                and slave_info["Slave_SQL_Running"] == "Yes"
                and slave_delay <= allow_delay_sec
            ):
                return True
            else:
                self.log_error(
                    _(
                        "Slave_IO_Running!=Yes or Slave_SQL_Running=!Yes or Seconds_Behind_Master>300,"
                        "请确定slave复制链路正常且延迟不能超过300s。"
                    )
                )
                return False


class CheckSlavesDelayComponent(Component):
    name = __name__
    code = "check_slaves_delay"
    bound_service = CheckSlavesDelayService
