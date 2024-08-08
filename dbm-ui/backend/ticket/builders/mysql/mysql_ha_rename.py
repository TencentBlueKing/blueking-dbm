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

from django.utils.translation import ugettext as _
from rest_framework import serializers

from backend.db_meta.enums import ClusterType
from backend.db_services.mysql.remote_service.handlers import RemoteServiceHandler
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.common.base import CommonValidate
from backend.ticket.builders.mysql.base import (
    BaseMySQLTicketFlowBuilder,
    DBTableField,
    MySQLBaseOperateDetailSerializer,
)
from backend.ticket.constants import FlowRetryType, TicketType


class MySQLHaRenameSerializer(MySQLBaseOperateDetailSerializer):
    class RenameDatabaseInfoSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        # 源database无需校验，考虑将存量不合法的DB名重命名为合法DB名
        from_database = serializers.CharField(help_text=_("源数据库名"))
        to_database = DBTableField(help_text=_("目标数据库名"), db_field=True)

    infos = serializers.ListField(help_text=_("重命名数据库列表"), child=RenameDatabaseInfoSerializer())
    force = serializers.BooleanField(help_text=_("是否强制执行"), default=False)

    def validate_rename_db(self, attrs):
        # 集群与业务库的映射
        cluster_ids = [info["cluster_id"] for info in attrs["infos"]]
        database_info = RemoteServiceHandler(self.context["bk_biz_id"]).show_databases(cluster_ids)
        cluster__databases = {info["cluster_id"]: info["databases"] for info in database_info}
        # DB重命名校验
        CommonValidate.validate_mysql_db_rename(attrs["infos"], cluster__databases)

    def validate(self, attrs):
        super().validate_cluster_can_access(attrs)
        # 集群类型校验
        super().validated_cluster_type(attrs, cluster_type=ClusterType.TenDBHA)
        # DB重命名校验
        self.validate_rename_db(attrs)
        return attrs


class MySQLHaRenameFlowParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_ha_rename_database_scene

    def format_ticket_data(self):
        for info in self.ticket_data["infos"]:
            info["force"] = self.ticket_data["force"]


@builders.BuilderFactory.register(TicketType.MYSQL_HA_RENAME_DATABASE)
class MySQLHaRenameFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MySQLHaRenameSerializer
    inner_flow_builder = MySQLHaRenameFlowParamBuilder
    inner_flow_name = _("DB重命名执行")
    retry_type = FlowRetryType.MANUAL_RETRY
