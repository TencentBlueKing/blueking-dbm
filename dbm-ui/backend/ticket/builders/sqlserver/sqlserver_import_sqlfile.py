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
from typing import Any, Dict, List, Union

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_services.mysql.sql_import.constants import SQLExecuteTicketMode
from backend.db_services.sqlserver.sql_import.constants import BKREPO_SQLFILE_PATH
from backend.flow.consts import SqlserverBackupFileTagEnum, SqlserverBackupMode, SqlserverCharSet
from backend.flow.engine.controller.sqlserver import SqlserverController
from backend.flow.utils.sqlserver import sqlserver_db_function
from backend.ticket import builders
from backend.ticket.builders.common.field import DBTimezoneField
from backend.ticket.builders.sqlserver.base import BaseSQLServerTicketFlowBuilder, SQLServerBaseOperateDetailSerializer
from backend.ticket.constants import FlowRetryType, FlowType, TicketType
from backend.ticket.exceptions import TicketParamsVerifyException
from backend.ticket.models import Flow


class SQLServerImportDetailSerializer(SQLServerBaseOperateDetailSerializer):
    class ExecuteDBInfoSerializer(serializers.Serializer):
        dbnames = serializers.ListField(help_text=_("执行DB"), child=serializers.CharField())
        ignore_dbnames = serializers.ListField(help_text=_("忽略DB"), child=serializers.CharField(), required=False)

    class SQLImportModeSerializer(serializers.Serializer):
        mode = serializers.ChoiceField(help_text=_("单据执行模式"), choices=SQLExecuteTicketMode.get_choices())
        trigger_time = DBTimezoneField(help_text=_("定时任务触发时间"), required=False, allow_blank=True)

    class SQLImportBackUpSerializer(serializers.Serializer):
        backup_dbs = serializers.ListField(help_text=_("备份db列表"), child=serializers.CharField())
        ignore_backup_dbs = serializers.ListField(help_text=_("忽略备份db列表"), child=serializers.CharField())

    charset = serializers.ChoiceField(help_text=_("字符集"), required=False, choices=SqlserverCharSet.get_choices())
    force = serializers.BooleanField(help_text=_("是否强制执行"), required=False, default=False)
    path = serializers.CharField(help_text=_("SQL文件路径"), required=False, default=BKREPO_SQLFILE_PATH)
    cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField())
    execute_sql_files = serializers.ListField(help_text=_("sql执行文件"), child=serializers.CharField())
    execute_db_infos = serializers.ListSerializer(help_text=_("sql执行的DB信息"), child=ExecuteDBInfoSerializer())
    ticket_mode = SQLImportModeSerializer(help_text=_("执行模式"))

    backup = serializers.ListSerializer(help_text=_("备份信息"), required=False, child=SQLImportBackUpSerializer())
    backup_place = serializers.CharField(help_text=_("备份位置(先固定为master)"), required=False, default="master")
    file_tag = serializers.ChoiceField(
        help_text=_("备份保存时间"),
        choices=SqlserverBackupFileTagEnum.get_choices(),
        required=False,
        default=SqlserverBackupFileTagEnum.MSSQL_FULL_BACKUP,
    )
    backup_type = serializers.ChoiceField(
        help_text=_("备份方式"), choices=SqlserverBackupMode.get_choices(), required=False
    )

    def validate(self, attrs):
        return attrs


class SQLServerBackupFlowParamBuilder(builders.FlowParamBuilder):
    controller = SqlserverController.backup_dbs_scene

    def format_ticket_data(self):
        # 根据库正则批量查询实际DB，获取集群备份DB信息
        backup_infos: List[Dict] = []
        for backup in self.ticket_data["backup"]:
            cluster_id__real_dbs = sqlserver_db_function.multi_get_dbs_for_drs(
                self.ticket_data["cluster_ids"], backup["backup_dbs"], backup["ignore_backup_dbs"]
            )
            backup_infos.extend(
                [
                    {"cluster_id": cluster_id, "backup_dbs": cluster_id__real_dbs[cluster_id]}
                    for cluster_id in self.ticket_data["cluster_ids"]
                    if cluster_id__real_dbs.get(cluster_id)
                ]
            )
        if not backup_infos:
            raise TicketParamsVerifyException(_("所选备份DB信息为空，请检查库表正则"))
        # 填充其他备份选项
        backup_data: Dict[str, Any] = {
            "backup_place": self.ticket_data["backup_place"],
            "backup_type": self.ticket_data["backup_type"],
            "file_tag": self.ticket_data["file_tag"],
            "infos": backup_infos,
        }
        self.ticket_data = backup_data
        # 注意回填一下单据基本信息
        self.add_common_params()


class SQLServerImportFlowParamBuilder(builders.FlowParamBuilder):
    controller = SqlserverController.sql_file_execute_scene

    def format_ticket_data(self):
        ticket_data = self.ticket_data
        execute_objects: List[Dict[str, Union[str, List]]] = []
        for sql_file in ticket_data["execute_sql_files"]:
            execute_objects.extend([{"sql_file": sql_file, **db_info} for db_info in ticket_data["execute_db_infos"]])
        ticket_data["execute_objects"] = execute_objects


@builders.BuilderFactory.register(TicketType.SQLSERVER_IMPORT_SQLFILE)
class SQLServerSingleApplyFlowBuilder(BaseSQLServerTicketFlowBuilder):
    serializer = SQLServerImportDetailSerializer
    editable = False

    def init_ticket_flows(self):
        """
        sql导入根据执行模式可分为三种执行流程：
        手动：单据审批-->手动确认-->(备份)--->sql导入
        自动：单据审批-->(备份)--->sql导入
        定时：单据审批-->定时触发-->(备份)--->sql导入
        """
        flows = [
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.BK_ITSM.value,
                details=builders.ItsmParamBuilder(self.ticket).get_params(),
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
                    details=SQLServerBackupFlowParamBuilder(self.ticket).get_params(),
                    retry_type=FlowRetryType.MANUAL_RETRY.value,
                    flow_alias=_("库表备份"),
                )
            )

        flows.append(
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.INNER_FLOW.value,
                details=SQLServerImportFlowParamBuilder(self.ticket).get_params(),
                retry_type=FlowRetryType.MANUAL_RETRY.value,
                flow_alias=_("变更SQL执行"),
            )
        )

        Flow.objects.bulk_create(flows)
        return list(Flow.objects.filter(ticket=self.ticket))

    @classmethod
    def describe_ticket_flows(cls, flow_config_map):
        flow_desc = [_("单据审批"), _("定时执行(人工确认)"), _("库表备份(可选)"), _("变更SQL执行")]
        return flow_desc
