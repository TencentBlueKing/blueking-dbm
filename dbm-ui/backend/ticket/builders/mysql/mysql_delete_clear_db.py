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

from django.utils.translation import ugettext as _

from backend.db_services.mysql.sql_import.constants import SQLExecuteTicketMode
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.mysql.mysql_force_import_sqlfile import (
    MysqlForceSqlImportDetailSerializer,
    MysqlForceSqlImportFlowBuilder,
    MysqlForceSqlImportFlowParamBuilder,
)
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


class MysqlDeleteClearDBDetailSerializer(MysqlForceSqlImportDetailSerializer):
    def validate(self, attrs):
        return attrs


class MysqlDeleteClearDBFlowParamBuilder(MysqlForceSqlImportFlowParamBuilder):
    controller = MySQLController.mysql_import_sqlfile_scene

    def format_ticket_data(self):
        pass


@builders.BuilderFactory.register(TicketType.MYSQL_DELETE_CLEAR_DB, is_sensitive=True)
class MysqlDeleteClearDBFlowBuilder(MysqlForceSqlImportFlowBuilder):
    serializer = MysqlDeleteClearDBDetailSerializer
    inner_flow_builder = MysqlDeleteClearDBFlowParamBuilder

    @property
    def need_manual_confirm(self):
        if self.ticket.details["ticket_mode"]["mode"] != SQLExecuteTicketMode.MANUAL.value:
            return False
        return super().need_manual_confirm

    @property
    def need_timer(self):
        return self.ticket.details["ticket_mode"]["mode"] == SQLExecuteTicketMode.TIMER

    @classmethod
    def describe_ticket_flows(cls, flow_config_map):
        flow_desc = [_("定时执行/人工执行"), _("删除清档备份库")]
        return flow_desc
