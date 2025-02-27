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

from backend.db_meta.models import Cluster
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.ticket.constants import TicketType
from backend.ticket.models import ClusterOperateRecord, Ticket

logger = logging.getLogger("root")


class AddUnlockTicketTypeConfigService(BaseService):
    """
    添加解除单据互斥锁的配置动作
    """

    @transaction.atomic()
    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")

        # 获取单据和flow信息
        ticket_id = global_data["uid"]
        ticket = Ticket.objects.get(id=ticket_id)
        flow = ticket.current_flow()

        # 判断是否修改互斥记录
        for cluster_id in kwargs.get("cluster_ids", []):
            cluster = Cluster.objects.get(id=cluster_id)
            record = ClusterOperateRecord.objects.get(
                cluster_id=cluster_id,
                ticket=ticket,
                flow=flow,
            )

            # 判断是否提前释放单据互斥锁
            record.unlock_ticket_type_operations(kwargs["unlock_ticket_type_list"])
            if "*" in kwargs["unlock_ticket_type_list"]:
                self.log_info(_("集群[{}] 解除单据互斥锁，所有单据都能进入\n".format(cluster.immute_domain)))
                continue
            for ticket_type in kwargs["unlock_ticket_type_list"]:
                self.log_info(
                    _(
                        "集群[{}] 解除单据互斥锁，以下单据类型可以进入 :[{}]\n".format(
                            cluster.immute_domain, TicketType.get_choice_label(ticket_type)
                        )
                    )
                )

        return True


class AddUnlockTicketTypeConfigComponent(Component):
    """
    定义添加解除单据互斥锁关系配置的component

    """

    name = _("添加解除单据互斥锁关系配置")
    code = "add_unlock_ticket_type_config"
    bound_service = AddUnlockTicketTypeConfigService
