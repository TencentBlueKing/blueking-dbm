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

from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.mysql.mysql_priv_change import (
    MySQLAccountRuleChangeFlowParamBuilder,
    MySQLAccountRuleChangeItsmFlowParamBuilder,
    MySQLAccountRuleChangeSerializer,
)
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder
from backend.ticket.constants import FlowRetryType, TicketType


class TendbAccountRuleChangeSerializer(MySQLAccountRuleChangeSerializer):
    pass


class TendbAccountRuleChangeFlowParamBuilder(MySQLAccountRuleChangeFlowParamBuilder):
    pass


class TendbAccountRuleChangeItsmFlowParamBuilder(MySQLAccountRuleChangeItsmFlowParamBuilder):
    pass


@builders.BuilderFactory.register(
    TicketType.TENDBCLUSTER_ACCOUNT_RULE_CHANGE, iam=ActionEnum.TENDBCLUSTER_ADD_ACCOUNT_RULE
)
class TendbAccountRuleChangeFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TendbAccountRuleChangeSerializer
    inner_flow_builder = TendbAccountRuleChangeFlowParamBuilder
    itsm_flow_builder = TendbAccountRuleChangeItsmFlowParamBuilder
    retry_type = FlowRetryType.MANUAL_RETRY
