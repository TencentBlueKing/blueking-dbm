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

import time

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.dbm_init.medium.handlers import MediumHandler
from backend.flow.consts import MONGODB_DATA_EXPORT_PATH
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.flow.utils.mongodb.db_table_filter import MongoDbTableFilter
from backend.ticket import builders
from backend.ticket.builders.mongodb.base import (
    BaseMongoDBOperateDetailSerializer,
    BaseMongoDBTicketFlowBuilder,
    BaseMongoOperateFlowParamBuilder,
    Cluster,
    DBTableSerializer,
)
from backend.ticket.builders.mysql.mysql_dump_data import (
    MySQLDumpDataItsmMaintainerFlowParamsBuilder,
    MySQLDumpDataItsmProductorFlowParamsBuilder,
)
from backend.ticket.constants import FlowType, TicketFlowStatus, TicketType
from backend.ticket.models import Flow


class MongoDBDataExportDetailSerializer(BaseMongoDBOperateDetailSerializer):
    class DataExportDetailSerializer(serializers.Serializer):
        class ExportOptionsSerializer(serializers.Serializer):
            format = serializers.ChoiceField(
                help_text=_("导出格式"), choices=[("json", "JSON"), ("csv", "CSV"), ("bson", "BSON")], default="json"
            )
            query = serializers.CharField(help_text=_("查询语句"), required=False, allow_null=True, allow_blank=True)
            fields = serializers.CharField(help_text=_("导出字段"), required=False, allow_null=True, allow_blank=True)

        class DBTableExportSerializer(DBTableSerializer):
            def validate(self, attrs):
                MongoDbTableFilter(
                    attrs["db_patterns"], attrs["table_patterns"], attrs["ignore_dbs"], attrs["ignore_tables"], True
                )
                return attrs

        ns_filter = DBTableExportSerializer(help_text=_("库表选择器"))
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        export_options = ExportOptionsSerializer(help_text=_("导出选项配置"))

    infos = serializers.ListSerializer(help_text=_("数据导出信息"), child=DataExportDetailSerializer())


class MongoDBDataExportFlowParamBuilder(BaseMongoOperateFlowParamBuilder):
    controller = MongoDBController.mongo_data_export

    def format_ticket_data(self):
        def pop_if_empty(export_options: dict, key: str):
            """
            Pops empty items.
            e.g. {"query": ""} -> {}
            """
            if key in export_options and len(export_options[key]) == 0:
                export_options.pop(key)

        cluster_ids = [info["cluster_id"] for info in self.ticket_data["infos"]]
        cluster_id_map = {cluster.id: cluster for cluster in Cluster.objects.filter(id__in=cluster_ids)}
        for info in self.ticket_data["infos"]:
            pop_if_empty(info["export_options"], "query")
            pop_if_empty(info["export_options"], "fields")

            cluster = cluster_id_map[info["cluster_id"]]
            info["filename"] = f"{cluster.immute_domain}_{time.strftime('%Y%m%d%H%M%S')}"

    def post_callback(self):
        flow = self.ticket.current_flow()
        if not flow or flow.status != TicketFlowStatus.SUCCEEDED:
            return

        _, files = MediumHandler().storage.listdir(MONGODB_DATA_EXPORT_PATH.format(biz=self.ticket.bk_biz_id))
        file_name_size_map = {file["name"]: file["size"] for file in files}
        cluster_results = {}
        for info in flow.details["ticket_data"]["infos"]:
            cluster_id = info["cluster_id"]
            result_file_path = "{}/{}.tar".format(
                MONGODB_DATA_EXPORT_PATH.format(biz=self.ticket.bk_biz_id), info["filename"]
            )
            cluster_results[cluster_id] = {
                "file_path": result_file_path,
                "file_name": info["filename"],
                "size": file_name_size_map.get(f"{info['filename']}.tar"),
            }
        self.ticket.update_details(exported_files=cluster_results)


@builders.BuilderFactory.register(TicketType.MONGODB_DATA_EXPORT)
class MongoDBDataExportApplyFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoDBDataExportDetailSerializer
    inner_flow_builder = MongoDBDataExportFlowParamBuilder
    itsm_flow_maintainer_builder = MySQLDumpDataItsmMaintainerFlowParamsBuilder
    itsm_flow_productor_builder = MySQLDumpDataItsmProductorFlowParamsBuilder
    inner_flow_name = _("MongoDB 数据导出执行")

    def init_ticket_flows(self):
        flows = []
        # 二级审批
        flows.append(
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.BK_ITSM.value,
                details=self.itsm_flow_maintainer_builder(self.ticket).get_params(),
                flow_alias=_("运维人员审批"),
            )
        )
        flows.append(
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.BK_ITSM.value,
                details=self.itsm_flow_productor_builder(self.ticket).get_params(),
                flow_alias=_("产品人员审批"),
            )
        )
        # 人工确认
        flows.append(
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.PAUSE.value,
                details=self.pause_node_builder(self.ticket).get_params(),
                flow_alias=_("人工确认"),
            ),
        )
        # 数据导出
        flows.append(
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.INNER_FLOW.value,
                details=self.inner_flow_builder(self.ticket).get_params(),
                flow_alias=self.inner_flow_name,
                retry_type=self.retry_type,
            )
        )

        Flow.objects.bulk_create(flows)
        return list(Flow.objects.filter(ticket=self.ticket))
