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

from django.db import transaction
from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.db_monitor.constants import MySQLAutofixStep
from backend.db_monitor.models import MySQLAutofixTicketStatus, MySQLAutofixTodo
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("celery")


class MySQLAutofixTodoRegisterService(BaseService):
    @transaction.atomic
    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")

        for row in kwargs["infos"]:
            self.log_info("[{}] mysql autofix info row: {}".format(kwargs["node_name"], row))
            new_record = {
                "bk_cloud_id": row["bk_cloud_id"],
                "bk_biz_id": row["bk_biz_id"],
                "check_id": row["check_id"],
                "cluster_id": row["cluster_id"],
                "immute_domain": row["immute_domain"],
                "cluster_type": row["cluster_type"],
                "machine_type": row["machine_type"],
                "instance_role": row["instance_role"],
                "ip": row["ip"],
                "port": row["port"],
                "event_create_time": row["event_create_time"],
                "dbha_gm_ip": row["dbha_gm_ip"],
                "context_master_host": row["context_master_host"],
                "context_master_port": row["context_master_port"],
                "context_master_log_file": row["context_master_log_file"],
                "context_master_log_pos": row["context_master_log_pos"],
                "inplace_ticket_id": 0,
                "inplace_ticket_status": MySQLAutofixTicketStatus.UNSUBMITTED.value,
                "replace_ticket_id": 0,
                "replace_ticket_status": MySQLAutofixTicketStatus.UNSUBMITTED.value,
                "current_step": MySQLAutofixStep.IN_PLACE_AUTOFIX.value,
            }

            # 按表唯一键做 replace 操作, 防止实例重复上报
            MySQLAutofixTodo.objects.update_or_create(
                defaults=new_record,
                check_id=new_record["check_id"],
                ip=new_record["ip"],
                port=new_record["port"],
            )

        self.log_info(_("[{}] 自愈信息写入完成".format(kwargs["node_name"])))
        return True


class MySQLAutofixTodoRegisterComponent(Component):
    name = __name__
    code = "mysql_autofix_todo_register"
    bound_service = MySQLAutofixTodoRegisterService
