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

import json
import logging

from django.utils.translation import ugettext as _
from rest_framework import serializers

from backend import env
from backend.configuration.constants import DBType
from backend.db_meta.models import Cluster
from backend.db_services.mysql.sql_import.constants import SQLExecuteTicketMode
from backend.db_services.mysql.sql_import.dataclass import SemanticOperateMeta
from backend.db_services.mysql.sql_import.handlers import SQLHandler
from backend.flow.engine.bamboo.engine import BambooEngine
from backend.flow.engine.controller.mysql import MySQLController
from backend.flow.engine.controller.spider import SpiderController
from backend.flow.models import FlowNode, FlowTree
from backend.flow.plugins.components.collections.mysql.semantic_check import SemanticCheckComponent
from backend.ticket import builders
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder, MySQLBaseOperateDetailSerializer
from backend.ticket.builders.mysql.mysql_import_sqlfile import (
    MysqlSqlImportBackUpFlowParamBuilder,
    MysqlSqlImportDetailSerializer,
    MysqlSqlImportFlowBuilder,
    MysqlSqlImportFlowParamBuilder,
    MysqlSqlImportItsmParamBuilder,
)
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder
from backend.ticket.builders.tendbcluster.tendb_full_backup import TendbFullBackUpDetailSerializer
from backend.ticket.constants import FlowRetryType, FlowType, TicketType
from backend.ticket.exceptions import TicketBaseException
from backend.ticket.models import Flow

logger = logging.getLogger("root")


class TenDBClusterSqlImportDetailSerializer(MysqlSqlImportDetailSerializer):
    pass


class TenDBClusterSqlImportItsmParamBuilder(MysqlSqlImportItsmParamBuilder):
    pass


class TenDBClusterSqlImportBackUpFlowParamBuilder(MysqlSqlImportBackUpFlowParamBuilder):
    controller = SpiderController.database_table_backup

    def format_ticket_data(self):
        super().format_ticket_data()
        for info in self.ticket_data["infos"]:
            info["backup_local"] = info["backup_on"]
            TendbFullBackUpDetailSerializer.get_backup_local_params(info)


class TenDBClusterSqlImportFlowParamBuilder(MysqlSqlImportFlowParamBuilder):
    controller = SpiderController.spider_sql_import_scene

    def format_ticket_data(self):
        super().format_ticket_data()


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_IMPORT_SQLFILE)
class TenDBClusterSqlImportFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TenDBClusterSqlImportDetailSerializer

    def patch_ticket_detail(self):
        MysqlSqlImportFlowBuilder.patch_sqlimport_ticket_detail(ticket=self.ticket, cluster_type=DBType.MySQL)

    def init_ticket_flows(self):
        """
        sql导入根据执行模式可分为三种执行流程：
        手动：语义检查-->单据审批-->手动确认-->(备份)--->sql导入
        自动：语义检查-->单据审批-->(备份)--->sql导入
        定时：语义检查-->单据审批-->定时触发-->(备份)--->sql导入
        """

        flows = [
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.DESCRIBE_TASK.value,
                details=TenDBClusterSqlImportFlowParamBuilder(self.ticket).get_params(),
                flow_alias=_("SQL模拟执行状态查询"),
            ),
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.BK_ITSM.value,
                details=TenDBClusterSqlImportItsmParamBuilder(self.ticket).get_params(),
                flow_alias=_("单据审批"),
            ),
        ]

        mode = self.ticket.details["ticket_mode"]["mode"]
        if mode == SQLExecuteTicketMode.MANUAL.value:
            flows.append(Flow(ticket=self.ticket, flow_type=FlowType.PAUSE.value, flow_alias=_("人工确认执行")))
        elif mode == SQLExecuteTicketMode.TIMER.value:
            flows.append(Flow(ticket=self.ticket, flow_type=FlowType.TIMER.value, flow_alias=_("定时执行")))

        if self.ticket.details.get("backup"):
            flows.append(
                Flow(
                    ticket=self.ticket,
                    flow_type=FlowType.INNER_FLOW.value,
                    details=TenDBClusterSqlImportBackUpFlowParamBuilder(self.ticket).get_params(),
                    retry_type=FlowRetryType.MANUAL_RETRY.value,
                    flow_alias=_("库表备份"),
                )
            )

        flows.append(
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.INNER_FLOW.value,
                details=TenDBClusterSqlImportFlowParamBuilder(self.ticket).get_params(),
                retry_type=FlowRetryType.MANUAL_RETRY.value,
                flow_alias=_("变更SQL执行"),
            )
        )

        Flow.objects.bulk_create(flows)
        return list(Flow.objects.filter(ticket=self.ticket))
