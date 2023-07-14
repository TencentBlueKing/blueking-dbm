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
from backend.flow.consts import INFODBA_SCHEMA
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.ticket.builders.common.constants import MYSQL_CHECKSUM_TABLE


class VerifyChecksumService(BaseService):
    """
    定义检测实例checksum结果的活动节点
    """

    def _execute(self, data, parent_data):

        # 每次检测checksum结果目前是保留一个轮次的检测结果，故优先检测checksum表
        # 如果checksum记录没有判断，且checksum没有test记录，说明一轮数据刚刚检验完且清空checksum表，
        # 则减少checksum_history最近14天的不一致记录
        allow_diff_cnt = 0
        kwargs = data.get_one_of_inputs("kwargs")

        checksum_instance_tuples = kwargs["checksum_instance_tuples"]
        error_message_list = []

        for t in checksum_instance_tuples:
            master_ip = t["master"].split(":")[0]
            master_port = t["master"].split(":")[1]
            slave_address = t["slave"]

            check_cmds = [
                (
                    f"select count(0) as cnt from {INFODBA_SCHEMA}.checksum"
                    " where ts > date_sub(now(), interval 14 day)"
                ),
                (
                    f"select count(0) as cnt from {INFODBA_SCHEMA}.{MYSQL_CHECKSUM_TABLE}"
                    " where ts > date_sub(now(), interval 14 day)"
                ),
                (
                    f"select count(distinct db, tbl,chunk) as cnt from {INFODBA_SCHEMA}.checksum"
                    " where (this_crc <> master_crc or this_cnt <> master_cnt)"
                    f" and master_ip = '{master_ip}' and master_port = {master_port}"
                ),
                (
                    f"select count(distinct db, tbl,chunk) as cnt from {INFODBA_SCHEMA}.{MYSQL_CHECKSUM_TABLE}"
                    " where (this_crc <> master_crc or this_cnt <> master_cnt)"
                    " and ts > date_sub(now(), interval 14 day)"
                    f" and master_ip = '{master_ip}' and master_port = {master_port}"
                ),
            ]

            res = DRSApi.rpc(
                {
                    "addresses": [slave_address],
                    "cmds": check_cmds,
                    "force": False,
                    "bk_cloud_id": kwargs["bk_cloud_id"],
                }
            )

            if res[0]["error_msg"]:
                error_message_list.append(f"This node [{slave_address}] verify checksum failed: {res[0]['error_msg']}")

            checksum_cnt = int(res[0]["cmd_results"][0]["table_data"][0]["cnt"])
            checksum_history_cnt = int(res[0]["cmd_results"][1]["table_data"][0]["cnt"])
            checksum_diff_cnt = int(res[0]["cmd_results"][2]["table_data"][0]["cnt"])
            checksum_history_diff_cnt = int(res[0]["cmd_results"][3]["table_data"][0]["cnt"])

            if not checksum_cnt and not checksum_history_cnt:
                error_message_list.append(
                    f"This node [{slave_address}] has not queried the verification records of the last 14 days"
                )

            elif checksum_diff_cnt > allow_diff_cnt or (
                checksum_cnt == 0 and checksum_history_diff_cnt > allow_diff_cnt
            ):
                error_message_list.append(f"This node [{slave_address}] has diff chuck in the last 14 days")
            else:
                self.log_info(f"The node [{slave_address}] passed the checkpoint [verify-checksum] !")

        if error_message_list:
            for error in error_message_list:
                self.log_error(error)
            return False

        return True


class VerifyChecksumComponent(Component):
    name = __name__
    code = "verify_checksum"
    bound_service = VerifyChecksumService
