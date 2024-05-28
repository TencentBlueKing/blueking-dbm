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
from backend.ticket.builders.mysql.mysql_force_import_sqlfile import (
    MysqlForceSqlImportDetailSerializer,
    MysqlForceSqlImportFlowBuilder,
)
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder
from backend.ticket.builders.tendbcluster.tendb_import_sqlfile import TenDBClusterSqlImportBackUpFlowParamBuilder
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


class TenDBClusterForceSqlImportDetailSerializer(MysqlForceSqlImportDetailSerializer):
    pass


class TenDBClusterSqlImportFlowParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.spider_sql_import_scene

    def format_ticket_data(self):
        super().format_ticket_data()


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_FORCE_IMPORT_SQLFILE, is_sensitive=True)
class TenDBClusterForceSqlImportFlowBuilder(MysqlForceSqlImportFlowBuilder, BaseTendbTicketFlowBuilder):
    group = DBType.TenDBCluster.value
    serializer = TenDBClusterForceSqlImportDetailSerializer
    backup_builder = TenDBClusterSqlImportBackUpFlowParamBuilder
    inner_flow_builder = TenDBClusterSqlImportFlowParamBuilder
    editable = False
