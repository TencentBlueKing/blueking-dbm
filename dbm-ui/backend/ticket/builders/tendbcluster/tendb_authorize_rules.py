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

from backend.db_services.mysql.permission.constants import AccountType
from backend.db_services.mysql.permission.db_account.handlers import AccountHandler
from backend.ticket import builders
from backend.ticket.builders.mysql.mysql_authorize_rules import (
    MySQLAuthorizeRulesFlowBuilder,
    MySQLAuthorizeRulesFlowParamBuilder,
    MySQLAuthorizeRulesSerializer,
    MySQLExcelAuthorizeRulesSerializer,
)
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder
from backend.ticket.constants import TicketType


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_AUTHORIZE_RULES)
class TendbClusterAuthorizeRulesFlowBuilder(BaseTendbTicketFlowBuilder, MySQLAuthorizeRulesFlowBuilder):
    serializer = MySQLAuthorizeRulesSerializer
    inner_flow_builder = MySQLAuthorizeRulesFlowParamBuilder
    inner_flow_name = _("TenDB Cluster 授权执行")

    @property
    def need_itsm(self):
        handler = AccountHandler(bk_biz_id=self.ticket.bk_biz_id, account_type=AccountType.TENDB)
        high_risk = handler.has_high_risk_privileges(self.ticket.details["rules_set"])
        return high_risk

    @property
    def need_manual_confirm(self):
        return False


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_EXCEL_AUTHORIZE_RULES)
class TendbClusterAuthorizeRulesFlowBuilder(TendbClusterAuthorizeRulesFlowBuilder):
    serializer = MySQLExcelAuthorizeRulesSerializer
    inner_flow_name = _("TenDB Cluster 授权执行")
