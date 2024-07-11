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
        upload_sql_path = BKREPO_SQLFILE_PATH.format(biz=self.ticket.bk_biz_id)
        execute_sql_files = []
        # 解构execute_objects，1. 上传sql文件 2. 平铺sql执行体信息
        for index, execute in enumerate(self.ticket.details["execute_objects"]):
            # 上传sql文件
            sql_content = execute.pop("sql_content", None)
            sql_files = execute.pop("sql_files", None)
            upload_sql_files = SQLHandler.upload_sql_file(upload_sql_path, sql_content, sql_files)
            real_sql_files = [os.path.split(file["sql_path"])[1] for file in upload_sql_files]
            # 更新sql执行体结构
            execute.update(sql_files=real_sql_files, line_id=index)
            execute_sql_files.extend(sql_files)

        self.ticket.update_details(execute_sql_files=execute_sql_files)
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

        if self.need_itsm:
            flows.append(
                Flow(
                    ticket=self.ticket,
                    flow_type=FlowType.BK_ITSM.value,
                    details=builders.ItsmParamBuilder(self.ticket).get_params(),
                    flow_alias=_("单据审批"),
                )
            )

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
