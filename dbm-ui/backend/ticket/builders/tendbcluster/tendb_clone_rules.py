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

from django.core.cache import cache
from django.utils.translation import ugettext_lazy as _

from backend.configuration.constants import DBType
from backend.db_services.mysql.permission.exceptions import CloneDataHasExpiredException
from backend.ticket import builders
from backend.ticket.builders.mysql.mysql_clone_rules import (
    MySQLClientCloneRulesFlowBuilder,
    MySQLCloneRulesFlowParamBuilder,
    MySQLCloneRulesSerializer,
)
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder
from backend.ticket.constants import TicketType


class TendbClusterCloneRulesSerializer(MySQLCloneRulesSerializer):
    pass


class TendbClusterCloneRulesFlowParamBuilder(MySQLCloneRulesFlowParamBuilder):
    pass


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_CLIENT_CLONE_RULES)
class TendbClusterClientCloneRulesFlowBuilder(MySQLClientCloneRulesFlowBuilder):
    group = DBType.TenDBCluster.value
    serializer = TendbClusterCloneRulesSerializer
    inner_flow_name = _("TenDB Cluster 客户端权限克隆执行")
    inner_flow_builder = TendbClusterCloneRulesFlowParamBuilder

    @property
    def need_itsm(self):
        return False

    @property
    def need_manual_confirm(self):
        return False


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_INSTANCE_CLONE_RULES)
class TendbClusterInstanceCloneRulesFlowBuilder(TendbClusterClientCloneRulesFlowBuilder):
    inner_flow_name = _("TenDB Cluster 实例权限克隆执行")
