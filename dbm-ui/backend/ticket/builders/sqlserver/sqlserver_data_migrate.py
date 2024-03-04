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
import datetime
from collections import defaultdict
from typing import Any, Dict, List

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.db_meta.models.sqlserver_dts import DtsStatus, SqlserverDtsInfo
from backend.flow.consts import SqlserverDtsMode
from backend.flow.engine.controller.sqlserver import SqlserverController
from backend.ticket import builders
from backend.ticket.builders.sqlserver.base import BaseSQLServerTicketFlowBuilder, SQLServerBaseOperateDetailSerializer
from backend.ticket.constants import FlowRetryType, FlowType, TicketFlowStatus, TicketType
from backend.ticket.models import Flow, Ticket


class SQLServerDataMigrateDetailSerializer(SQLServerBaseOperateDetailSerializer):
    class DataMigrateInfoSerializer(serializers.Serializer):
        class RenameInfoSerializer(serializers.Serializer):
            db_name = serializers.CharField(help_text=_("源集群库名"))
            target_db_name = serializers.CharField(help_text=_("目标集群库名"))
            rename_db_name = serializers.CharField(help_text=_("集群重命名库名"), default="", required=False)

            def validate(self, attrs):
                # 补充源集群DB重命名的格式
                date = str(datetime.date.today()).replace("-", "")
                attrs["old_db_name"] = f"{attrs['db_name']}_old_{date}"
                return attrs

        src_cluster = serializers.IntegerField(help_text=_("源集群ID"))
        dst_cluster = serializers.IntegerField(help_text=_("目标集群ID"))
        db_list = serializers.ListField(help_text=_("库正则"), child=serializers.CharField(), required=False)
        ignore_db_list = serializers.ListField(help_text=_("忽略库正则"), child=serializers.CharField(), required=False)
        rename_infos = serializers.ListSerializer(help_text=_("迁移DB信息"), child=RenameInfoSerializer())
        dts_id = serializers.IntegerField(help_text=_("迁移记录ID"), required=False)

    dts_mode = serializers.ChoiceField(help_text=_("迁移方式"), choices=SqlserverDtsMode.get_choices())
    need_auto_rename = serializers.BooleanField(help_text=_("迁移后，系统是否对源DB进行重命名"))
    manual_terminate = serializers.BooleanField(help_text=_("手动终止迁移"), required=False, default=False)
    infos = serializers.ListSerializer(help_text=_("迁移信息列表"), child=DataMigrateInfoSerializer())

    def validate(self, attrs):
        """验证库表数据库的数据"""
        # TODO: 验证target_db_name如果在目标集群存在，则rename_db_name不为空
        # TODO: 验证所有的rename_db_name一定不在目标集群存在
        super().validate(attrs)
        return attrs


class SQLServerDataMigrateFlowParamBuilder(builders.FlowParamBuilder):
    incr_controller = SqlserverController.incr_dts_scene
    full_controller = SqlserverController.full_dts_scene

    def build_controller_info(self) -> dict:
        if self.ticket_data["dts_mode"] == SqlserverDtsMode.INCR:
            self.controller = self.incr_controller
        else:
            self.controller = self.full_controller
        return super().build_controller_info()

    def post_callback(self):
        flow = self.ticket.current_flow()
        if flow.status not in [TicketFlowStatus.REVOKED, TicketFlowStatus.FAILED, TicketFlowStatus.TERMINATED]:
            return
        # 流程失败/终止情况下，更新传输记录状态
        dts_ids = [info["dts_id"] for info in self.ticket_data["infos"]]
        # 全量传输中 ----> 全量传输失败
        SqlserverDtsInfo.objects.filter(id__in=dts_ids, status=DtsStatus.FullOnline).update(
            status=DtsStatus.FullFailed
        )
        # 增量传输中 ----> 增量传输失败
        SqlserverDtsInfo.objects.filter(id__in=dts_ids, status=DtsStatus.IncrOnline).update(
            status=DtsStatus.IncrFailed
        )

    def format_ticket_data(self):
        is_last = self.ticket_data["dts_mode"] == SqlserverDtsMode.FULL
        self.ticket_data["is_last"] = is_last


class SQLServerRenameFlowParamBuilder(builders.FlowParamBuilder):
    controller = SqlserverController.rename_dbs_scene
    rename_type = None

    def __init__(self, rename_type, ticket: Ticket):
        super().__init__(ticket)
        self.rename_type = rename_type

    def format_db_rename_infos(self, cluster_key, from_key, to_key):
        """填充db重命名信息"""
        dbrename_infos: List[Dict[str, str]] = []
        for info in self.ticket_data["infos"]:
            dbrename_infos.extend(
                [
                    {"cluster_id": info[cluster_key], "from_database": db[from_key], "to_database": db[to_key]}
                    for db in info["rename_infos"]
                    if db.get(from_key) and db.get(to_key)
                ]
            )
        return dbrename_infos

    def format_target_cluster_rename_infos(self):
        """对目标集群进行DB重命名"""
        dbrename_infos = self.format_db_rename_infos("dst_cluster", "target_db_name", "rename_db_name")
        self.ticket_data["infos"] = dbrename_infos

    def format_source_cluster_rename_infos(self):
        """对源集群进行DB重命名"""
        dbrename_infos = self.format_db_rename_infos("src_cluster", "db_name", "old_db_name")
        self.ticket_data["infos"] = dbrename_infos

    def format_ticket_data(self):
        getattr(self, f"format_{self.rename_type}_cluster_rename_infos")()
        self.ticket_data["ticket_type"] = TicketType.SQLSERVER_DBRENAME


@builders.BuilderFactory.register(TicketType.SQLSERVER_DATA_MIGRATE)
class SQLServerDataMigrateFlowBuilder(BaseSQLServerTicketFlowBuilder):
    serializer = SQLServerDataMigrateDetailSerializer
    inner_flow_builder = SQLServerDataMigrateFlowParamBuilder
    inner_flow_name = _("SQLServer 数据迁移执行")
    retry_type = FlowRetryType.MANUAL_RETRY
    # 流程不允许修改
    editable = False

    def need_itsm(self):
        super().need_itsm()

    def need_manual_confirm(self):
        super().need_manual_confirm()

    def create_dts_infos(self):
        # 创建迁移记录
        dts_infos: List[SqlserverDtsInfo] = []
        for index, info in enumerate(self.ticket.details["infos"]):
            dts_config = [
                {"db_name": db["db_name"], "target_db_name": db["target_db_name"]} for db in info["rename_infos"]
            ]
            dts_info = SqlserverDtsInfo(
                bk_biz_id=self.ticket.bk_biz_id,
                source_cluster_id=info["src_cluster"],
                target_cluster_id=info["dst_cluster"],
                dts_mode=self.ticket.details["dts_mode"],
                ticket_id=self.ticket.id,
                status=DtsStatus.ToDo,
                dts_config=dts_config,
            )
            dts_infos.append(dts_info)

        SqlserverDtsInfo.objects.bulk_create(dts_infos)
        dts_infos = SqlserverDtsInfo.objects.filter(ticket_id=self.ticket.id)
        # 构造源集群--目标集群--单据ID的记录映射
        dts_info_map: Dict[Any, Dict[Any, Dict[Any, Any]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(dict))
        )
        for dts_info in dts_infos:
            dts_info_map[dts_info.source_cluster_id][dts_info.target_cluster_id][dts_info.ticket_id] = dts_info.id
        # 填充每条迁移信息的迁移记录id
        for info in self.ticket.details["infos"]:
            dts_info_id = dts_info_map[info["src_cluster"]][info["dst_cluster"]][self.ticket.id]
            info["dts_id"] = dts_info_id

    def update_dts_infos(self):
        # 更新迁移记录，更新关联的ticket_id和断开中的状态
        dts_ids = [info["dts_id"] for info in self.ticket.details["infos"]]
        SqlserverDtsInfo.objects.filter(id__in=dts_ids).update(
            ticket_id=self.ticket.id, status=DtsStatus.Disconnecting
        )

    def patch_ticket_detail(self):
        # 如果是手动终止，则需要更新dts记录，否则创建
        if self.ticket.details["manual_terminate"]:
            self.update_dts_infos()
        else:
            self.create_dts_infos()
        super().patch_ticket_detail()

    def custom_ticket_flows(self):
        is_manual_terminate = self.ticket.details["manual_terminate"]
        dts_mode = self.ticket.details["dts_mode"]

        if is_manual_terminate:
            self.inner_flow_name = _("SQLServer 数据迁移执行(断开同步)")

        dts_flow = Flow(
            ticket=self.ticket,
            flow_type=FlowType.INNER_FLOW.value,
            details=SQLServerDataMigrateFlowParamBuilder(self.ticket).get_params(),
            flow_alias=self.inner_flow_name,
        )
        target_dbrename_flow = Flow(
            ticket=self.ticket,
            flow_type=FlowType.INNER_FLOW.value,
            details=SQLServerRenameFlowParamBuilder(rename_type="target", ticket=self.ticket).get_params(),
            flow_alias=_("SQLServer 目标数据库重命名"),
        )
        source_dbrename_flow = Flow(
            ticket=self.ticket,
            flow_type=FlowType.INNER_FLOW.value,
            details=SQLServerRenameFlowParamBuilder(rename_type="source", ticket=self.ticket).get_params(),
            flow_alias=_("SQLServer 源数据库重命名"),
        )

        # 如果非手动终止发起的单据，且存在目标数据库重命名的情况，则串目标集群重命名流程
        if not is_manual_terminate and target_dbrename_flow.details["ticket_data"].get("infos"):
            flows = [target_dbrename_flow, dts_flow]
        else:
            flows = [dts_flow]

        # 如果是完整备份迁移且源DB不在使用，则串源集群重命名流程
        if dts_mode == SqlserverDtsMode.FULL and self.ticket.details["need_auto_rename"]:
            flows.append(source_dbrename_flow)
        # 如果是增量备份迁移，且是手动触发，且源DB不在使用，则
        elif is_manual_terminate and dts_mode == SqlserverDtsMode.INCR and self.ticket.details["need_auto_rename"]:
            flows.append(source_dbrename_flow)

        return flows
