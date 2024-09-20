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
from datetime import datetime, timezone
from typing import Dict, List

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.db_services.sqlserver.cluster.handlers import ClusterServiceHandler
from backend.db_services.sqlserver.rollback.handlers import SQLServerRollbackHandler
from backend.flow.consts import SqlserverBackupFileTagEnum, SqlserverBackupMode
from backend.flow.engine.controller.sqlserver import SqlserverController
from backend.ticket import builders
from backend.ticket.builders.common.field import DBTimezoneField
from backend.ticket.builders.sqlserver.base import BaseSQLServerTicketFlowBuilder, SQLServerBaseOperateDetailSerializer
from backend.ticket.builders.sqlserver.sqlserver_data_migrate import SQLServerRenameFlowParamBuilder
from backend.ticket.constants import FlowRetryType, FlowType, TicketType
from backend.ticket.models import Flow, Ticket
from backend.utils.time import str2datetime


class SQLServerRollbackDetailSerializer(SQLServerBaseOperateDetailSerializer):
    class RollbackInfoSerializer(serializers.Serializer):
        class RenameInfoSerializer(serializers.Serializer):
            db_name = serializers.CharField(help_text=_("源集群库名"))
            target_db_name = serializers.CharField(help_text=_("目标集群库名"))
            rename_db_name = serializers.CharField(
                help_text=_("集群重命名库名"), allow_blank=True, default="", required=False
            )

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
        restore_backup_file = BackupFileSerializer(help_text=_("备份记录"), required=False)
        restore_time = DBTimezoneField(help_text=_("回档时间"), allow_blank=True, required=False)

    infos = serializers.ListSerializer(help_text=_("迁移信息列表"), child=RollbackInfoSerializer())
    is_local = serializers.BooleanField(help_text=_("是否原地构造"))

    def validate(self, attrs):
        """验证库表数据库的数据"""
        # TODO: 验证target_db_name如果在目标集群存在，则rename_db_name不为空
        # TODO: 验证所有的rename_db_name一定不在目标集群存在

        # 校验集群是否可用
        super().validate_cluster_can_access(attrs)

        # 如果是指定回档时间，则查出最近的备份记录
        for info in attrs["infos"]:
            if not info.get("restore_time"):
                info.pop("restore_time", None)
                continue
            rollback_time = str2datetime(info["restore_time"])
            restore_backup_file = SQLServerRollbackHandler(info["src_cluster"]).query_latest_backup_log(rollback_time)
            info["restore_backup_file"] = restore_backup_file

        super().validate(attrs)
        return attrs


class SQLServerDataMigrateFlowParamBuilder(builders.FlowParamBuilder):
    controller = SqlserverController.db_construct_scene

    def format_ticket_data(self):
        super().format_ticket_data()


class SQLServerRollbackRenameFlowParamBuilder(SQLServerRenameFlowParamBuilder):
    controller = SqlserverController.rename_dbs_scene

    def __init__(self, ticket: Ticket):
        # 如果原地定点构造，则对源集群进行重命名；否则对目标集群进行重命名
        rename_type = "source" if ticket.details["is_local"] else "target"
        super().__init__(rename_type, ticket)


class SQLServerRollbackBackupFlowParamBuilder(builders.FlowParamBuilder):
    controller = SqlserverController.backup_dbs_scene

    def format_ticket_data(self):
        # 通过库表匹配查询db
        backup_infos: List[Dict[str, str]] = []
        for info in self.ticket_data["infos"]:
            if "restore_time" not in info:
                continue
            cluster_id = info["src_cluster"]
            db_list = info["db_list"]
            ignore_db_list = info["ignore_db_list"]
            restore_time = str2datetime(info["restore_time"])
            current_time = datetime.now(timezone.utc)
            # 获取最近的一次日志备份记录的时间点
            last_time = str2datetime(SQLServerRollbackHandler(cluster_id).query_last_log_time(current_time))
            # 如果最近一次日志备份记录的时间大于等于回滚时间 则不需要备份
            if last_time > restore_time:
                continue

            backup_dbs = ClusterServiceHandler(self.ticket.bk_biz_id).get_dbs_for_drs(
                cluster_id, db_list, ignore_db_list
            )
            backup_infos.extend([{"cluster_id": cluster_id, "backup_dbs": backup_dbs, "backup_type": "log_backup"}])
        self.ticket_data["infos"] = backup_infos
        self.ticket_data["ticket_type"] = TicketType.SQLSERVER_BACKUP_DBS
        self.ticket_data["backup_place"] = "master"
        self.ticket_data["file_tag"] = SqlserverBackupFileTagEnum.INCREMENT_BACKUP.value
        self.ticket_data["backup_type"] = SqlserverBackupMode.LOG_BACKUP.value


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

        backup_flow = Flow(
            ticket=self.ticket,
            flow_type=FlowType.INNER_FLOW.value,
            details=SQLServerRollbackBackupFlowParamBuilder(ticket=self.ticket).get_params(),
            flow_alias=_("SQLServer 库表备份执行"),
        )
        flows = []

        # 如果重命名单据参数不为空，需要串重命名流程
        if dbrename_flow.details["ticket_data"].get("infos"):
            flows.append(dbrename_flow)
        elif backup_flow.details["ticket_data"].get("infos"):
            flows.append(backup_flow)
        flows.append(rollback_flow)
        return flows
