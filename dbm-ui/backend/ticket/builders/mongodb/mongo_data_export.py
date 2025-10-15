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

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.flow.consts import MONGODB_DATA_EXPORT_PATH
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.ticket import builders
from backend.ticket.builders.mongodb.base import (
    BaseMongoDBOperateDetailSerializer,
    BaseMongoDBTicketFlowBuilder,
    BaseMongoOperateFlowParamBuilder,
    Cluster,
    DBTableSerializer,
)
from backend.ticket.constants import TicketFlowStatus, TicketType


class MongoDBDataExportDetailSerializer(BaseMongoDBOperateDetailSerializer):
    class DataExportDetailSerializer(serializers.Serializer):
        class ExportOptionsSerializer(serializers.Serializer):
            format = serializers.ChoiceField(
                help_text=_("导出格式"), choices=[("json", "JSON"), ("csv", "CSV"), ("bson", "BSON")], default="json"
            )
            query = serializers.CharField(help_text=_("查询语句"), required=False, allow_null=True, allow_blank=True)
            fields = serializers.CharField(help_text=_("导出字段"), required=False, allow_null=True, allow_blank=True)

        ns_filter = DBTableSerializer(help_text=_("库表选择器"))
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

        for info in self.ticket_data["infos"]:
            pop_if_empty(info["export_options"], "query")
            pop_if_empty(info["export_options"], "fields")

            cluster = Cluster.objects.get(id=info["cluster_id"])
            info["filename"] = f"{cluster.immute_domain}_{int(time.time())}"

    def post_callback(self):
        flow = self.ticket.current_flow()
        if not flow or flow.status != TicketFlowStatus.SUCCEEDED:
            return

        cluster_results = {}
        for info in flow.details["ticket_data"]["infos"]:
            cluster_id = info["cluster_id"]
            result_file_path = "{}/{}.tar".format(
                MONGODB_DATA_EXPORT_PATH.format(biz=self.ticket.bk_biz_id), info["filename"]
            )
            cluster_results[cluster_id] = result_file_path
        self.ticket.update_details(exported_files=cluster_results)


@builders.BuilderFactory.register(TicketType.MONGODB_DATA_EXPORT)
class MongoDBDataExportApplyFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoDBDataExportDetailSerializer
    inner_flow_builder = MongoDBDataExportFlowParamBuilder
    inner_flow_name = _("MongoDB 数据导出执行")
