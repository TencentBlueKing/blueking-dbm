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
from django.utils.translation import ugettext_lazy as _

from backend.flow.engine.controller.mysql_clb_operation import MySQLClbController
from backend.ticket import builders
from backend.ticket.builders.mysql.base import BaseMySQLHATicketFlowBuilder, MysqlSingleOpsBaseDetailSerializer
from backend.ticket.constants import TicketType


class MysqlCLBBindDomainDetailSerializer(MysqlSingleOpsBaseDetailSerializer):
    pass


class MysqlCLBBindDomainFlowParamBuilder(builders.FlowParamBuilder):
    controller = MySQLClbController.immute_domain_bind_clb_ip

    def format_ticket_data(self):
        """
        {
            "uid": "22346",
            "created_by": "makeyuan",
            "bk_biz_id": "20",
            "bk_cloud_id": 0,
            "ticket_type": "MYSQL_CLB_BIND_DOMAIN",
            "cluster_id": 91
        }
        """
        super().format_ticket_data()


@builders.BuilderFactory.register(TicketType.MYSQL_CLB_BIND_DOMAIN)
class MysqlCLBBindDomainFlowBuilder(BaseMySQLHATicketFlowBuilder):
    serializer = MysqlCLBBindDomainDetailSerializer
    inner_flow_builder = MysqlCLBBindDomainFlowParamBuilder
    inner_flow_name = _("主域名绑定CLB")
    default_need_itsm = False
