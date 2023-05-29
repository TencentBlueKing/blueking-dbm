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
from django.db.transaction import atomic
from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.components import DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.flow.consts import CHECKSUM_DB, CHECKSUM_TABlE_PREFIX
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.ticket.models import Ticket


class MySQLChecksumReportService(BaseService):
    def _execute(self, data, parent_data) -> bool:
        """
        bk_cloud_id 统一由私有变量kwargs传入
        """
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")
        kwargs = data.get_one_of_inputs("kwargs")

        skip_tables = []
        if trans_data.checksum_report:
            if trans_data.checksum_report["summaries"]:
                for table_checksum in trans_data.checksum_report["summaries"]:
                    if table_checksum["skipped"] != 0:
                        skip_tables.append(table_checksum["table"])

        diff_sql, consistent_sql = self._generate_sql(
            global_data["master_ip"],
            global_data["master_port"],
            "{}.{}{}".format(CHECKSUM_DB, CHECKSUM_TABlE_PREFIX, global_data["ran_str"]),
        )

        address = "{}{}{}".format(global_data["slave_ip"], IP_PORT_DIVIDER, global_data["slave_port"])

        try:
            resp = DRSApi.rpc(
                {
                    "addresses": [address],
                    "cmds": [diff_sql, consistent_sql],
                    "force": False,
                    "bk_cloud_id": kwargs["bk_cloud_id"],
                }
            )

            if resp[0]["error_msg"]:
                self.log_error(_("在{}执行sql失败，相关信息: {}").format(address, resp[0]["error_msg"]))
                return False
            else:
                if resp[0]["cmd_results"][0]["error_msg"]:
                    self.log_error(
                        _("在{}执行sql{}失败，相关信息: {}").format(
                            address, resp[0]["cmd_results"][0]["cmd"], resp[0]["cmd_results"][0]["error_msg"]
                        )
                    )
                    return False
                if resp[0]["cmd_results"][1]["error_msg"]:
                    self.log_error(
                        _("在{}执行sql{}失败，相关信息: {}").format(
                            address, resp[0]["cmd_results"][1]["cmd"], resp[0]["cmd_results"][1]["error_msg"]
                        )
                    )
                    return False

            err_tables = []
            succ_tables = []
            for result in resp[0]["cmd_results"][0]["table_data"]:
                err_tables.append(result["res"])
            for result in resp[0]["cmd_results"][1]["table_data"]:
                succ_tables.append(result["res"])

            if len(err_tables) > 0:
                trans_data.is_consistent = False

            self._print_log(err_tables, skip_tables, succ_tables)

        except Exception as e:  # pylint: disable=broad-except
            self.log_error(_("查询数据库接口异常，相关信息: {}").format(e))
            return False

        self.log_info(_("uid:{}".format(global_data["uid"])))

        # 原子更新：将校验结果插入ticket信息中，用后后续ticket flow上下文获取
        with atomic():
            ticket = Ticket.objects.select_for_update().get(id=global_data["uid"])
            flags = ticket.details.get("is_consistent_list", {})
            flags.update({address: trans_data.is_consistent})
            ticket.update_details(
                is_consistent_list=flags, checksum_table="{}{}".format(CHECKSUM_TABlE_PREFIX, global_data["ran_str"])
            )

        return True

    @staticmethod
    def _generate_sql(master_ip, master_port, replicate_table):
        where_master = "master_ip = '{}' and master_port = {}".format(master_ip, master_port)

        where_not_consistent = "(this_crc <> master_crc or this_cnt <> master_cnt)"
        where_consistent = "(this_crc = master_crc and this_cnt = master_cnt)"

        diff_tables = "concat(db,'.',tbl,' checksum failed! Number of different chunks: ',count(*)) as res "
        diff_sql = "select {} from {} where {} and {} group by db,tbl;".format(
            diff_tables, replicate_table, where_master, where_not_consistent
        )

        consistent_tables = "concat(db,'.',tbl,' checksum succeeded! Total chunks: ',count(*)) as res"
        consistent_sql = "select {} from {} where {} and {} group by db,tbl;".format(
            consistent_tables, replicate_table, where_master, where_consistent
        )
        return diff_sql, consistent_sql

    def _print_log(self, err_tables, skip_tables, succ_tables):
        self.log_info(_("ERROR 数据不一致的表的数量: {}").format(len(err_tables)))
        self.log_info(_("WARNING 被跳过校验的表的数量: {}").format(len(skip_tables)))
        self.log_info(_("SUCCESS 数据一致的表的数量: {}").format((len(succ_tables))))
        self.log_dividing_line()
        indet_format = " " * 8

        if len(err_tables) > 0:
            self.log_info(_("ERROR 校验失败，数据不一致的表:"))
            for tb in err_tables:
                self.log_info(indet_format + tb)
            self.log_dividing_line()

        if len(skip_tables) > 0:
            self.log_info(_("WARNING 校验程序没有校验的表:"))
            for tb in skip_tables:
                self.log_info(indet_format + tb)
            self.log_dividing_line()

        if len(succ_tables) > 0:
            self.log_info(_("SUCCESS 校验成功，数据一致的表:"))
            for tb in succ_tables:
                self.log_info(indet_format + tb)
            self.log_dividing_line()


class MysqlChecksumReportComponent(Component):
    name = __name__
    code = "mysql_checksum_report"
    bound_service = MySQLChecksumReportService
