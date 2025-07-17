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

from backend.db_meta.enums import ClusterType
from backend.ticket.builders import BuilderFactory
from backend.ticket.builders.mysql.base import BaseMySQLHATicketFlowBuilder
from backend.ticket.builders.mysql.mysql_ha_apply import (
    MysqlHAApplyDetailSerializer,
    MysqlHAApplyFlowParamBuilder,
    MysqlHaApplyResourceParamBuilder,
)
from backend.ticket.builders.mysql.mysql_single_apply import MysqlSingleApplyFlowBuilder
from backend.ticket.constants import TicketType


class MysqlHAApplyQuickMinorPassDetailSerializer(MysqlHAApplyDetailSerializer):
    pass


class MysqlHAApplyQuickMinorPassFlowParamBuilder(MysqlHAApplyFlowParamBuilder):
    pass


class MysqlHAApplyQuickMinorPassParamBuilder(MysqlHaApplyResourceParamBuilder):
    pass


@BuilderFactory.register(TicketType.MYSQL_HA_APPLY_QUICK_MINOR_PASS, is_apply=True, cluster_type=ClusterType.TenDBHA)
class MysqlHAApplyQuickMinorPassFlowBuilder(BaseMySQLHATicketFlowBuilder):
    serializer = MysqlHAApplyQuickMinorPassDetailSerializer
    inner_flow_builder = MysqlHAApplyQuickMinorPassFlowParamBuilder
    inner_flow_name = _("MySQL高可用小额绿通部署执行")
    resource_apply_builder = MysqlHAApplyQuickMinorPassParamBuilder
    default_need_itsm = False
    default_need_manual_confirm = False

    def patch_ticket_detail(self):
        MysqlSingleApplyFlowBuilder.patch_dbconfig(ticket=self.ticket, cluster_type=ClusterType.TenDBHA)
        super().patch_ticket_detail()
