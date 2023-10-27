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
    检测checksum结果的规则:
    1: 这里的规则只检验例行checksum结果，对手动checksum结果不做校验
    2: 如果最近14天内在checksum/checksum_history表没有记录，则认为这对主从长时间没有checksum，报出异常
    3: 优先检测checksum结果，checksum结果目前是保留一个轮次的检测结果，下一个轮次会清空
    4: checksum表有可能为空的情况，如果为则再判断checksum_history表的不一致的情况
    5: checksum_history表一开始是不存在的，故先判断实例是否存在，以免影响结果输出
    """

    def _execute(self, data, parent_data):

        allow_diff_cnt = 0
        is_exist_checksum_history = True

        kwargs = data.get_one_of_inputs("kwargs")

        checksum_instance_tuples = kwargs["checksum_instance_tuples"]
        error_message_list = []

        for t in checksum_instance_tuples:
            master_ip = t["master"].split(":")[0]
            master_port = t["master"].split(":")[1]
            slave_address = t["slave"]
            checksum_history_cnt = checksum_history_diff_cnt = 0

            # 判断checksum_history表是否存在
            is_table_cmd = (
                f"select count(0) as t from information_schema.tables "
                f"where TABLE_SCHEMA = '{INFODBA_SCHEMA}' "
                f"and TABLE_NAME = '{MYSQL_CHECKSUM_TABLE}' ;"
            )

            res = DRSApi.rpc(
                {
                    "addresses": [slave_address],
                    "cmds": [is_table_cmd],
                    "force": False,
                    "bk_cloud_id": kwargs["bk_cloud_id"],
                }
            )
            if res[0]["error_msg"]:
                error_message_list.append(f"This node [{slave_address}] verify checksum failed: {res[0]['error_msg']}")
                continue

            if int(res[0]["cmd_results"][0]["table_data"][0]["t"]) == 0:
                # 标记 checksum_history 不存在
                is_exist_checksum_history = False

            # 拼接查询校验结果命令集，并分析结果
            check_cmds = [
                (
                    f"select count(0) as cnt from {INFODBA_SCHEMA}.checksum"
                    f" where ts > date_sub(now(), interval 14 day)"
                    f" and ((master_ip = '{master_ip}' and master_port = {master_port}) or"
                    f" master_ip = '0.0.0.0')"
                ),
                (
                    f"select count(distinct db, tbl,chunk) as cnt from {INFODBA_SCHEMA}.checksum"
                    " where (this_crc <> master_crc or this_cnt <> master_cnt)"
                    "and ts > date_sub(now(), interval 14 day)"
                    f" and master_ip = '{master_ip}' and master_port = {master_port}"
                ),
            ]
            if is_exist_checksum_history:
                check_cmds.append(
                    (
                        f"select count(0) as cnt from {INFODBA_SCHEMA}.{MYSQL_CHECKSUM_TABLE}"
                        f" where ts > date_sub(now(), interval 14 day)"
                        f" and ((master_ip = '{master_ip}' and master_port = {master_port}) or"
                        f" master_ip = '0.0.0.0')"
                    )
                )
                check_cmds.append(
                    (
                        f"select count(distinct db, tbl,chunk) as cnt from {INFODBA_SCHEMA}.{MYSQL_CHECKSUM_TABLE}"
                        " where (this_crc <> master_crc or this_cnt <> master_cnt)"
                        " and ts > date_sub(now(), interval 14 day)"
                        f" and master_ip = '{master_ip}' and master_port = {master_port}"
                    )
                )

            res = DRSApi.rpc(
                {
                    "addresses": [slave_address],
                    "cmds": check_cmds,
                    "force": False,
                    "bk_cloud_id": kwargs["bk_cloud_id"],
                }
            )

            # 执行如果出现异常报错
            if res[0]["error_msg"]:
                error_message_list.append(f"This node [{slave_address}] verify checksum failed: {res[0]['error_msg']}")
                continue

            # 捕捉返回结果
            checksum_cnt = int(res[0]["cmd_results"][0]["table_data"][0]["cnt"])
            checksum_diff_cnt = int(res[0]["cmd_results"][1]["table_data"][0]["cnt"])
            if is_exist_checksum_history:
                checksum_history_cnt = int(res[0]["cmd_results"][2]["table_data"][0]["cnt"])
                checksum_history_diff_cnt = int(res[0]["cmd_results"][3]["table_data"][0]["cnt"])

            # 分析结果
            # 场景1: 如果最近14天内在checksum/checksum_history表没有记录，异常
            if checksum_cnt == 0 and checksum_history_cnt == 0:
                error_message_list.append(
                    f"This node [{slave_address}] has not queried the verification records of the last 14 days"
                )
            # 场景2: checksum不一致结果大于允许范围； 或者checksum表为空且history表不一致结果大于允许范围，异常
            elif checksum_diff_cnt > allow_diff_cnt or (
                checksum_cnt == 0 and checksum_history_diff_cnt > allow_diff_cnt
            ):
                error_message_list.append(f"This node [{slave_address}] has diff chuck in the last 14 days")
            # 其余场景：从结果看表示数据一致，正常
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
