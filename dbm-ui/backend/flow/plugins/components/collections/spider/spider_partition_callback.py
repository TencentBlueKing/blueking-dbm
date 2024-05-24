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

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.components.mysql_partition.client import DBPartitionApi
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.plugins.components.collections.mysql.mysql_partition_report import MySQLPartitionReportService
from backend.ticket.models import Ticket

logger = logging.getLogger("flow")


class SpiderPartitionCallbackService(BaseService):
    def _execute(self, data, parent_data) -> bool:
        global_data = data.get_one_of_inputs("global_data")
        configs = defaultdict(list)
        log_para = []
        fail_list = []
        success_list = []
        ticket = Ticket.objects.get(id=global_data["uid"])
        flags = ticket.details.get("log_list", {})
        for log_list in flags.values():
            for log in log_list:
                configs[log["config_id"]].append(log)
        for config, logs in configs.items():
            log_status = "succeeded"
            err_msg = ""
            for log in logs:
                if log["status"] == "failed":
                    log_status = "failed"
                    err_msg = "{};{}".format(err_msg, log["check_info"])
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
            try:
                partition_log_data = {
                    "cluster_type": "tendbcluster",
                    "logs": log_para,
                }
                DBPartitionApi.create_log(partition_log_data)
            except Exception as e:  # pylint: disable=broad-except
                self.log_error(_("callback分区create_log接口异常: {}").format(e))
                return False
        MySQLPartitionReportService.print_log(self, fail_list, success_list)
        if fail_list:
            return False
        return True


class SpiderPartitionCallbackComponent(Component):
    name = __name__
    code = "spider_partition_callback"
    bound_service = SpiderPartitionCallbackService
