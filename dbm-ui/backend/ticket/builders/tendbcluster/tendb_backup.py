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

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.flow.engine.controller.spider import SpiderController
from backend.ticket import builders
from backend.ticket.builders.mysql.base import DBTableField
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder, TendbBaseOperateDetailSerializer
from backend.ticket.builders.tendbcluster.tendb_full_backup import TendbFullBackUpDetailSerializer
from backend.ticket.constants import TicketType


class TendbBackUpDetailSerializer(TendbBaseOperateDetailSerializer):
    class TendbBackUpItemSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        backup_local = serializers.CharField(help_text=_("备份位置"))
        db_patterns = serializers.ListField(help_text=_("匹配DB列表"), child=DBTableField(db_field=True))
        ignore_dbs = serializers.ListField(help_text=_("忽略DB列表"), child=DBTableField(db_field=True))
        table_patterns = serializers.ListField(help_text=_("匹配Table列表"), child=DBTableField())
        ignore_tables = serializers.ListField(help_text=_("忽略Table列表"), child=DBTableField())

    infos = serializers.ListSerializer(help_text=_("库表备份信息"), child=TendbBackUpItemSerializer())

    def validate(self, attrs):
        for info in attrs["infos"]:
            TendbFullBackUpDetailSerializer.get_backup_local_params(info)

        # 库表选择器校验
        super().validate_database_table_selector(attrs, role_key="backup_local")
        return attrs


class TendbBackUpFlowParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.database_table_backup


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_DB_TABLE_BACKUP)
class TendbBackUpFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TendbBackUpDetailSerializer
    inner_flow_builder = TendbBackUpFlowParamBuilder
    inner_flow_name = _("TenDB Cluster 库表备份")
