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
import itertools
import logging
import os

from django.utils.translation import ugettext as _

from backend.db_services.mysql.sql_import.constants import BKREPO_SQLFILE_PATH, SQLExecuteTicketMode
from backend.db_services.mysql.sql_import.handlers import SQLHandler
from backend.db_services.mysql.sql_import.serializers import ImportSQLForceSerializer
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder, MySQLBaseOperateDetailSerializer
from backend.ticket.builders.mysql.mysql_import_sqlfile import MysqlSqlImportBackUpFlowParamBuilder
from backend.ticket.constants import FlowRetryType, FlowType, TicketType
from backend.ticket.models import Flow

logger = logging.getLogger("root")


class MysqlForceSqlImportDetailSerializer(ImportSQLForceSerializer, MySQLBaseOperateDetailSerializer):
    def validate(self, attrs):
        return attrs


class MysqlForceSqlImportFlowParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_import_sqlfile_scene

    def format_ticket_data(self):
        pass


@builders.BuilderFactory.register(TicketType.MYSQL_FORCE_IMPORT_SQLFILE, is_sensitive=True)
class MysqlForceSqlImportFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MysqlForceSqlImportDetailSerializer
    backup_builder = MysqlSqlImportBackUpFlowParamBuilder
    inner_flow_builder = MysqlForceSqlImportFlowParamBuilder
    editable = False

    def patch_ticket_detail(self):
        # 上传sql文件
        sql_content = self.ticket.details.pop("execute_sql_content")
        sql_files = self.ticket.details.pop("execute_sql_files")
        execute_sql_files = SQLHandler.upload_sql_file(BKREPO_SQLFILE_PATH, sql_content, sql_files)

        # 获取sql执行体结构
        execute_sql_filenames = [os.path.split(file["sql_path"])[1] for file in execute_sql_files]
        execute_objects = [
            [{"sql_file": sql_file, **db_info} for db_info in self.ticket.details["execute_db_infos"]]
            for sql_file in execute_sql_filenames
        ]
        execute_objects = list(itertools.chain(*execute_objects))

        self.ticket.update_details(execute_sql_files=execute_sql_files, execute_objects=execute_objects)
        super().patch_ticket_detail()

    def init_ticket_flows(self):
        """
        sql导入根据执行模式可分为三种执行流程：
        手动：手动确认-->(备份)--->sql导入
        自动：(备份)--->sql导入
        定时：定时触发-->(备份)--->sql导入
        """
        flows = []
        mode = self.ticket.details["ticket_mode"]["mode"]

        if mode == SQLExecuteTicketMode.MANUAL.value:
            flows.append(Flow(ticket=self.ticket, flow_type=FlowType.PAUSE.value, flow_alias=_("人工确认执行")))

        if mode == SQLExecuteTicketMode.TIMER.value:
            flows.append(Flow(ticket=self.ticket, flow_type=FlowType.TIMER.value, flow_alias=_("定时执行")))

        if self.ticket.details.get("backup"):
            flows.append(
                Flow(
                    ticket=self.ticket,
                    flow_type=FlowType.INNER_FLOW.value,
                    details=self.backup_builder(self.ticket).get_params(),
                    retry_type=FlowRetryType.MANUAL_RETRY.value,
                    flow_alias=_("库表备份"),
                )
            )

        flows.append(
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.INNER_FLOW.value,
                details=self.inner_flow_builder(self.ticket).get_params(),
                retry_type=FlowRetryType.MANUAL_RETRY.value,
                flow_alias=_("强制变更SQL执行"),
            )
        )

        Flow.objects.bulk_create(flows)
        return list(Flow.objects.filter(ticket=self.ticket))

    @classmethod
    def describe_ticket_flows(cls, flow_config_map):
        flow_desc = [_("库表备份(可选)"), _("变更SQL执行")]
        return flow_desc
