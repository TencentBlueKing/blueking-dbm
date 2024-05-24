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
from collections import defaultdict

from django.db.transaction import atomic
from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.components.mysql_partition.client import DBPartitionApi
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket

logger = logging.getLogger("flow")


class MySQLPartitionReportService(BaseService):
    def _execute(self, data, parent_data) -> bool:
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")
        kwargs = data.get_one_of_inputs("kwargs")

        log_para = []
        fail_list = []
        success_list = []
        configs = defaultdict(list)
        if trans_data.partition_report:
            if trans_data.partition_report["summaries"]:
                summaries = trans_data.partition_report["summaries"]
                for item in summaries:
                    configs[item["config_id"]].append(item)
                for config, logs in configs.items():
                    log_status = "succeeded"
                    err_msg = ""
                    for log in logs:
                        if log["status"] == "failed":
                            log_status = "failed"
                            err_msg = "{};{}".format(err_msg, log["msg"])
                    err_msg = err_msg.strip(";")
                    item = {
                        "config_id": config,
                        "check_info": err_msg,
                        "status": log_status,
                        "cron_date": global_data["cron_date"],
                        "scheduler": global_data["created_by"],
                    }
                    log_para.append(item)
                    if log_status == "succeeded":
                        success_list.append(item)
                    elif log_status == "failed":
                        fail_list.append(item)
                    else:
                        self.log_error(_("不支持的状态类型: [{}]").format(log_status))
                        return False

        if log_para:
            if (
                global_data["ticket_type"] == TicketType.MYSQL_PARTITION
                or global_data["ticket_type"] == TicketType.MYSQL_PARTITION_CRON
            ):
                cluster_type = "tendbha"
                partition_log_data = {
                    "cluster_type": cluster_type,
                    "logs": log_para,
                }
                try:
                    DBPartitionApi.create_log(partition_log_data)
                except Exception as e:  # pylint: disable=broad-except
                    self.log_error(_("callback分区create_log接口异常: {}").format(e))
                    return False
            elif (
                global_data["ticket_type"] == TicketType.TENDBCLUSTER_PARTITION
                or global_data["ticket_type"] == TicketType.TENDBCLUSTER_PARTITION_CRON
            ):
                # 原子更新：将校验结果插入ticket信息中，用后后续ticket flow上下文获取
                with atomic():
                    if global_data["ticket_type"] == TicketType.TENDBCLUSTER_PARTITION:
                        ip = kwargs["ip"]
                    else:
                        ip = global_data["ip"]
                    ticket = Ticket.objects.select_for_update().get(id=global_data["uid"])
                    flags = ticket.details.get("log_list", {})
                    flags.update({ip: log_para})
                    ticket.update_details(log_list=flags)
            else:
                self.log_error(_("不支持的单据类型: [{}]").format(global_data["ticket_type"]))
                return False

        self.print_log(fail_list, success_list)
        if fail_list and (
            global_data["ticket_type"] == TicketType.MYSQL_PARTITION
            or global_data["ticket_type"] == TicketType.MYSQL_PARTITION_CRON
        ):
            return False
        return True

    def print_log(self, fail_list, success_list):
        self.log_info(_("ERROR 执行失败的分区规则的数量: {}").format(len(fail_list)))
        self.log_info(_("SUCCESS 执行成功的分区规则的数量: {}").format((len(success_list))))
        self.log_dividing_line()
        indet_format = " " * 8

        if fail_list:
            self.log_info(_("ERROR 执行失败的分区规则:"))
            for item in fail_list:
                self.log_info(indet_format + "config id:[{}] msg:[{}]".format(item["config_id"], item["check_info"]))
            self.log_dividing_line()

        if success_list:
            self.log_info(_("SUCCESS 执行成功的分区规则:"))
            for item in success_list:
                self.log_info(indet_format + "config id:[{}]".format(item["config_id"]))
            self.log_dividing_line()


class MysqlPartitionReportComponent(Component):
    name = __name__
    code = "mysql_partition_report"
    bound_service = MySQLPartitionReportService
