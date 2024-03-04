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
from rest_framework import serializers

from backend.flow.engine.controller.sqlserver import SqlserverController
from backend.ticket import builders
from backend.ticket.builders.common.field import DBTimezoneField
from backend.ticket.builders.sqlserver.base import BaseSQLServerTicketFlowBuilder, SQLServerBaseOperateDetailSerializer
from backend.ticket.builders.sqlserver.sqlserver_data_migrate import SQLServerRenameFlowParamBuilder
from backend.ticket.constants import FlowRetryType, FlowType, TicketType
from backend.ticket.models import Flow, Ticket


class SQLServerRollbackDetailSerializer(SQLServerBaseOperateDetailSerializer):
    class RollbackInfoSerializer(serializers.Serializer):
        class RenameInfoSerializer(serializers.Serializer):
            db_name = serializers.CharField(help_text=_("源集群库名"))
            target_db_name = serializers.CharField(help_text=_("目标集群库名"))
            rename_db_name = serializers.CharField(help_text=_("集群重命名库名"), default="", required=False)

            def validate(self, attrs):
                # 补充源集群DB重命名的格式
                attrs["old_db_name"] = attrs["rename_db_name"]
                return attrs

        class BackupFileSerializer(serializers.Serializer):
            backup_id = serializers.CharField(help_text=_("备份ID"))
            logs = serializers.ListSerializer(help_text=_("备份日志"), child=serializers.JSONField())

        src_cluster = serializers.IntegerField(help_text=_("源集群ID"))
        dst_cluster = serializers.IntegerField(help_text=_("目标集群ID"))
        db_list = serializers.ListField(help_text=_("库正则"), child=serializers.CharField(), required=False)
        ignore_db_list = serializers.ListField(help_text=_("忽略库正则"), child=serializers.CharField(), required=False)
        rename_infos = serializers.ListSerializer(help_text=_("迁移DB信息"), child=RenameInfoSerializer())
        restore_backup_file = BackupFileSerializer(help_text=_("备份记录"))
        restore_time = DBTimezoneField(help_text=_("回档时间"), required=False)

    infos = serializers.ListSerializer(help_text=_("迁移信息列表"), child=RollbackInfoSerializer())
    is_local = serializers.BooleanField(help_text=_("是否原地构造"))

    def validate(self, attrs):
        """验证库表数据库的数据"""
        # TODO: 验证target_db_name如果在目标集群存在，则rename_db_name不为空
        # TODO: 验证所有的rename_db_name一定不在目标集群存在
        super().validate(attrs)
        return attrs


class SQLServerDataMigrateFlowParamBuilder(builders.FlowParamBuilder):
    controller = SqlserverController.fake_scene

    def format_ticket_data(self):
        super().format_ticket_data()


class SQLServerRollbackRenameFlowParamBuilder(SQLServerRenameFlowParamBuilder):
    controller = SqlserverController.rename_dbs_scene

    def __init__(self, ticket: Ticket):
        # 如果原地定点构造，则对源集群进行重命名；否则对目标集群进行重命名
        rename_type = "source" if ticket.details["is_local"] else "target"
        super().__init__(rename_type, ticket)


@builders.BuilderFactory.register(TicketType.SQLSERVER_ROLLBACK)
class SQLServerDataMigrateFlowBuilder(BaseSQLServerTicketFlowBuilder):
    serializer = SQLServerRollbackDetailSerializer
    inner_flow_builder = SQLServerDataMigrateFlowParamBuilder
    retry_type = FlowRetryType.MANUAL_RETRY
    # 流程不允许修改
    editable = False

    def custom_ticket_flows(self):
        rollback_flow = Flow(
            ticket=self.ticket,
            flow_type=FlowType.INNER_FLOW.value,
            details=SQLServerDataMigrateFlowParamBuilder(self.ticket).get_params(),
            flow_alias=_("SQLServer 定点构造执行"),
        )
        dbrename_flow = Flow(
            ticket=self.ticket,
            flow_type=FlowType.INNER_FLOW.value,
            details=SQLServerRollbackRenameFlowParamBuilder(ticket=self.ticket).get_params(),
            flow_alias=_("SQLServer 数据库重命名"),
        )

        # 如果重命名单据参数不为空，需要串重命名流程
        if dbrename_flow.details["ticket_data"].get("infos"):
            flows = [dbrename_flow, rollback_flow]
        else:
            flows = [rollback_flow]
        return flows
