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

from backend.components import DRSApi
from backend.flow.plugins.components.collections.common.base_service import BaseService

# from backend.ticket.models import Ticket

logger = logging.getLogger("flow")


class MySQLCheckSumTicketResultCheck(BaseService):
    """
    检查每个实例的checksum结果
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        checksum_pairs = kwargs["checksum_pairs"]
        checksum_success = True
        self.log_info(_("传入参数:{}").format(kwargs))
        trans_data = data.get_one_of_inputs("trans_data")
        logger.info("set kwargs info")

        # 因checksum表是checksum_ticket_id唯一的，这里可不需要加时间范围。后续需要可放开。
        # checksum_ticket = Ticket.objects.get(id=trans_data.auto_checksum_ticket_id)
        # checksum_start_time = checksum_ticket.create_at.isoformat()
        # checksum_end_time = checksum_ticket.update_at.isoformat()
        # conditions = (
        #     f" ts >= CONVERT_TZ('{checksum_start_time}','+00:00',@@time_zone)"
        #     f" and ts <= CONVERT_TZ('{checksum_end_time}','+00:00',@@time_zone)"
        # )

        table_name = f"infodba_schema.checksum_{trans_data.auto_checksum_ticket_id}"
        bk_cloud_id = kwargs["bk_cloud_id"]
        checksum_sql = (
            f"select db,tbl,concat(db,'.',tbl) as db_table,this_crc,master_crc from {table_name}"
            f" where this_crc!=master_crc;"
        )
        #       因checksum表是checksum_ticket_id唯一的,这里不设置开始标志_dba_fake_demand_start
        #         conditions2 = (
        #             f" db in ('_dba_fake_demand_start','_dba_fake_demand_end') and"
        #             f" tbl in ('_dba_fake_demand_start','_dba_fake_demand_end') and"
        #             f" chunk=0 and {conditions}"
        #         )
        #         checksum_progress_sql = f"""select distinct * from (
        # (select * from {table_name} where {conditions2} order by ts limit 1)
        # UNION
        # (select * from {table_name} where {conditions2} order by ts desc limit 1)
        # ) as v  order by ts;
        #         """
        checksum_progress_sql = (
            f"select * from {table_name} where"
            f" db='_dba_fake_demand_end' and tbl='_dba_fake_demand_end' order by ts desc limit 1;"
        )
        self.log_info(checksum_progress_sql)
        self.log_info(checksum_sql)
        for checksum_pair in checksum_pairs:
            # 1. 先检查执行结束没有
            self.log_info(f"==== {checksum_pair['master']} -> {checksum_pair['slave']} ====")
            res = DRSApi.rpc(
                {
                    "addresses": [checksum_pair["slave"]],
                    "cmds": [checksum_progress_sql],
                    "force": False,
                    "bk_cloud_id": bk_cloud_id,
                }
            )
            if res[0]["error_msg"]:
                self.log_info("execute checksum progress sql error {}".format(res[0]["error_msg"]))
                checksum_success = False
            else:
                table_data = res[0]["cmd_results"][0]["table_data"]
                if len(table_data) == 1:
                    if (
                        table_data[0]["db"] == "_dba_fake_demand_end"
                        and table_data[0]["tbl"] == "_dba_fake_demand_end"
                    ):
                        self.log_info("Mark checksum ends. ")
                        # 2 校验数据同步完毕，开始对比校验数据。
                        res = DRSApi.rpc(
                            {
                                "addresses": [checksum_pair["slave"]],
                                "cmds": [checksum_sql],
                                "force": False,
                                "bk_cloud_id": bk_cloud_id,
                            }
                        )
                        if res[0]["error_msg"]:
                            self.log_info("execute checksum sql error {}".format(res[0]["error_msg"]))
                            checksum_success = False
                        else:
                            if len(res[0]["cmd_results"][0]["table_data"]) == 0:
                                self.log_info("Checksum consistent !!!")
                            else:
                                checksum_success = False
                                for fail_table in res[0]["cmd_results"][0]["table_data"]:
                                    self.log_info(
                                        f"table: {fail_table['db_table']}  "
                                        f"this_crc: {fail_table['this_crc']}  master_crc: {fail_table['master_crc']}"
                                    )
                    else:
                        self.log_info(_("校验checksum失败: 找不到结束标志  _dba_fake_demand_end"))
                        checksum_success = False
                else:
                    self.log_info(_("校验checksum失败: 没有结束标志 _dba_fake_demand_end "))
                    checksum_success = False
        return checksum_success


class MySQLCheckSumTicketResultComponent(Component):
    name = __name__
    code = "mysql_checksum_ticket_result_check"
    bound_service = MySQLCheckSumTicketResultCheck
    node_name = str(_("检查checksum结果是否一致"))
