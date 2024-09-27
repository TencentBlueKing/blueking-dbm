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

from backend.configuration.constants import DBType
from backend.flow.engine.controller.spider import SpiderController
from backend.ticket import builders
from backend.ticket.builders.mysql.mysql_import_sqlfile import (
    MysqlSqlImportBackUpFlowParamBuilder,
    MysqlSqlImportDetailSerializer,
    MysqlSqlImportFlowBuilder,
    MysqlSqlImportFlowParamBuilder,
    MysqlSqlImportItsmParamBuilder,
)
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder
from backend.ticket.builders.tendbcluster.tendb_full_backup import TendbFullBackUpDetailSerializer
from backend.ticket.constants import TicketType

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
class TenDBClusterSqlImportFlowBuilder(MysqlSqlImportFlowBuilder, BaseTendbTicketFlowBuilder):
    serializer = TenDBClusterSqlImportDetailSerializer
    # 定义流程所用到的cls，方便继承复用
    itsm_flow_builder = TenDBClusterSqlImportItsmParamBuilder
    backup_flow_builder = TenDBClusterSqlImportBackUpFlowParamBuilder
    import_flow_builder = TenDBClusterSqlImportFlowParamBuilder

    def patch_ticket_detail(self):
        super().patch_sqlimport_ticket_detail(ticket=self.ticket, cluster_type=DBType.TenDBCluster)
        super().patch_sqlfile_grammar_check_info(ticket=self.ticket, cluster_type=DBType.TenDBCluster)
        super().patch_ticket_detail()

    def init_ticket_flows(self):
        super().init_ticket_flows()
