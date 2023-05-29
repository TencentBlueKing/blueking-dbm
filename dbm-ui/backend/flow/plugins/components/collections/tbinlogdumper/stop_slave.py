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

from backend.components import DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.flow.plugins.components.collections.common.base_service import BaseService


class TBinlogDumperStopSlaveService(BaseService):
    """
    对TBinlogDumper关闭数据同步
    """

    def _execute(self, data, parent_data):

        kwargs = data.get_one_of_inputs("kwargs")
        address = f"{kwargs['tbinlogdumper_ip']}{IP_PORT_DIVIDER}{kwargs['tbinlogdumper_port']}"

        res = DRSApi.rpc(
            {
                "addresses": [address],
                "cmds": ["stop slave"],
                "force": False,
                "bk_cloud_id": kwargs["bk_cloud_id"],
            }
        )

        if res[0]["error_msg"]:
            if kwargs["is_safe"]:
                self.log_error(f"stop slave [{address}] failed:[{res[0]['error_msg']}]")
                return False
            else:
                self.log_warning(f"stop slave [{address}] failed:[{res[0]['error_msg']}], but is_safe is false,skip")
                return True

        self.log_info(f"stop slave [{address}] success")
        return True


class TBinlogDumperStopSlaveComponent(Component):
    name = __name__
    code = "tbinlogdumper_stop_slave"
    bound_service = TBinlogDumperStopSlaveService
