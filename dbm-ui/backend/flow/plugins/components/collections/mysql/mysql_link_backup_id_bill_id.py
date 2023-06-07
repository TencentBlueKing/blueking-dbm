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
from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

import backend.flow.utils.mysql.mysql_context_dataclass as flow_context
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.ticket.models import TicketResultRelation


class MySQLLinkBackupIdBillIdService(BaseService):
    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        global_data = data.get_one_of_inputs("global_data")

        # self.log_info("[{}] backup response: {}".format(kwargs["node_name"], trans_data.backup_report_response))

        backup_id = global_data["backup_id"]  # trans_data.backup_report_response["report_status"]["backup_id"]
        self.log_info(_("[{}] 备份 id: {}").format(kwargs["node_name"], backup_id))

        TicketResultRelation.objects.create(
            ticket_id=global_data["uid"],
            ticket_type=global_data["ticket_type"],
            task_id=backup_id,
            creator=global_data["created_by"],
            updater=global_data["created_by"],
        )
        return True


class MySQLLinkBackupIdBillIdComponent(Component):
    name = __name__
    code = "mysql_link_backup_id_bill_id"
    bound_service = MySQLLinkBackupIdBillIdService
