# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is
distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from datetime import datetime, timezone
from typing import Dict, List

from django.utils.translation import gettext_lazy as _
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


class SQLServerRollbackBaseDetailSerializer(SQLServerBaseOperateDetailSerializer):
    """SQLServer 定点构造(回档)与本地构造(原地构造)公共的明细序列化器"""

    class RollbackInfoSerializer(serializers.Serializer):
        class RenameInfoSerializer(serializers.Serializer):
            db_name = serializers.CharField(help_text=_("源库名"))
            target_db_name = serializers.CharField(help_text=_("恢复后库名"))
            rename_db_name = serializers.CharField(help_text=_("已有库新名"), allow_blank=True, default="", required=False)

            def validate(self, attrs):
                # 补充源集群DB重命名的格式
                attrs["old_db_name"] = attrs["rename_db_name"]
                return attrs

        class BackupFileSerializer(serializers.Serializer):
            backup_id = serializers.CharField(help_text=_("备份 ID"))
            logs = serializers.ListSerializer(help_text=_("备份日志"), child=serializers.JSONField())
            start_time = serializers.CharField(help_text=_("备份开始时间"), required=False)
            end_time = serializers.CharField(help_text=_("备份结束时间"), required=False)
            complete = serializers.BooleanField(help_text=_("备份是否完成"), required=False)
            expected_cnt = serializers.IntegerField(help_text=_("期望文件数量"), required=False)
            real_cnt = serializers.IntegerField(help_text=_("实际文件数量"), required=False)
            role = serializers.CharField(help_text=_("备份角色"), required=False)
            backup_db_list = serializers.ListSerializer(
                help_text=_("备份库列表"), child=serializers.CharField(), required=False
            )
            backup_db_size_kb = serializers.IntegerField(help_text=_("备份库大小 KB"), required=False)
            backup_file_size_kb = serializers.IntegerField(help_text=_("备份文件大小 KB"), required=False)
            excluded_db_list = serializers.ListSerializer(
                help_text=_("排除库列表"), child=serializers.CharField(), required=False
            )
            bill_id = serializers.CharField(help_text=_("关联单据 ID"), allow_blank=True, required=False)

        src_cluster = serializers.IntegerField(help_text=_("源集群ID"))
        dst_cluster = serializers.IntegerField(help_text=_("目标集群ID"))
        db_list = serializers.ListField(help_text=_("库正则"), child=serializers.CharField(), required=False)
        ignore_db_list = serializers.ListField(help_text=_("忽略库正则"), child=serializers.CharField(), required=False)
        rename_infos = serializers.ListSerializer(help_text=_("迁移DB信息"), child=RenameInfoSerializer())
        restore_backup_file = BackupFileSerializer(help_text=_("备份记录"), required=False)
        restore_time = DBTimezoneField(help_text=_("回档时间"), allow_blank=True, required=False)

    infos = serializers.ListSerializer(help_text=_("迁移信息列表"), child=RollbackInfoSerializer())


class SQLServerDataMigrateFlowParamBuilder(builders.FlowParamBuilder):
    controller = SqlserverController.db_construct_scene

    def format_ticket_data(self):
        super().format_ticket_data()


class SQLServerRollbackRenameFlowParamBuilder(SQLServerRenameFlowParamBuilder):
    controller = SqlserverController.rename_dbs_scene

    def __init__(self, ticket: Ticket):
        # 去掉 is_local 字段后，通过源集群与目标集群是否一致来判断：
        # 原地回档（源集群与目标集群相同）需要对源集群重命名；定点构造（目标集群不同）对目标集群重命名
        rollback_infos = ticket.details["infos"]
        is_inplace = bool(rollback_infos) and rollback_infos[0]["dst_cluster"] == rollback_infos[0]["src_cluster"]
        rename_type = "source" if is_inplace else "target"
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
            last_time = str2datetime(SQLServerRollbackHandler(cluster_id).query_last_log_time_from_model(current_time))
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


class SQLServerRollbackCommonFlowBuilder(BaseSQLServerTicketFlowBuilder):
    """定点构造与本地构造共用的流程编排逻辑"""

    inner_flow_builder = SQLServerDataMigrateFlowParamBuilder
    retry_type = FlowRetryType.MANUAL_RETRY

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

        # dbrename_flow 和 backup_flow 是互斥关系：
        # 因此使用 elif 而非两个独立的 if，避免同时触发两个流程
        if dbrename_flow.details["ticket_data"].get("infos"):
            flows.append(dbrename_flow)
        elif backup_flow.details["ticket_data"].get("infos"):
            flows.append(backup_flow)
        flows.append(rollback_flow)
        return flows
