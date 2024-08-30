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

from backend.db_meta.enums import ClusterType
from backend.db_services.mysql.sql_import.constants import SQLCharset
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder, MySQLBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class MysqlOpenAreaDetailSerializer(MySQLBaseOperateDetailSerializer):
    class ConfigDataSerializer(serializers.Serializer):
        class ConfigExecuteSerializer(serializers.Serializer):
            source_db = serializers.CharField(help_text=_("源DB"))
            target_db = serializers.CharField(help_text=_("目标DB"))
            schema_tblist = serializers.ListField(help_text=_("表结构列表"), child=serializers.CharField())
            data_tblist = serializers.ListField(help_text=_("表数据列表"), child=serializers.CharField())

        cluster_id = serializers.IntegerField(help_text=_("目标集群ID"))
        execute_objects = serializers.ListSerializer(help_text=_("分区执行信息"), child=ConfigExecuteSerializer())

    class PrivDataSerializer(serializers.Serializer):
        class AccountRulesSerializer(serializers.Serializer):
            dbname = serializers.CharField(help_text=_("db名"))
            bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))

        bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
        operator = serializers.CharField(help_text=_("操作人"))
        user = serializers.CharField(help_text=_("用户"))
        source_ips = serializers.ListField(help_text=_("IP列表"), child=serializers.CharField())
        target_instances = serializers.ListField(help_text=_("目标集群列表"), child=serializers.CharField())
        account_rules = serializers.ListSerializer(help_text=_("授权DB列表"), child=AccountRulesSerializer())
        cluster_type = serializers.ChoiceField(help_text=_("集群类型"), choices=ClusterType.get_choices())
        privileges = serializers.JSONField(help_text=_("授权详情"), required=False)
        access_dbs = serializers.ListField(help_text=_("准入DB列表"), child=serializers.CharField())

    cluster_id = serializers.IntegerField(help_text=_("源集群ID"))
    config_id = serializers.IntegerField(help_text=_("模板ID"), required=False)
    force = serializers.BooleanField(help_text=_("是否强制执行"), required=False, default=False)
    config_data = serializers.ListSerializer(help_text=_("分区信息"), child=ConfigDataSerializer())
    rules_set = serializers.ListSerializer(
        help_text=_("授权信息"), child=PrivDataSerializer(), required=False, allow_null=True, allow_empty=True
    )


class MysqlOpenAreaParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_open_area_scene

    def format_ticket_data(self):
        # 字符集先默认为default
        self.ticket_data["charset"] = SQLCharset.DEFAULT.value
        self.ticket_data["source_cluster"] = self.ticket_data.pop("cluster_id")
        self.ticket_data["target_clusters"] = self.ticket_data.pop("config_data")
        for info in self.ticket_data["target_clusters"]:
            info["target_cluster"] = info.pop("cluster_id")


@builders.BuilderFactory.register(TicketType.MYSQL_OPEN_AREA)
class MysqlOpenAreaFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MysqlOpenAreaDetailSerializer
    inner_flow_builder = MysqlOpenAreaParamBuilder
    inner_flow_name = _("MySQL 开区执行")
