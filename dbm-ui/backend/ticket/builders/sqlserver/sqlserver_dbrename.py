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
from collections import defaultdict
from typing import Dict, List

from django.utils.translation import ugettext as _
from rest_framework import serializers

from backend.flow.engine.controller.sqlserver import SqlserverController
from backend.flow.utils.sqlserver import sqlserver_db_function
from backend.ticket import builders
from backend.ticket.builders.common.base import CommonValidate
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder, DBTableField
from backend.ticket.builders.sqlserver.base import SQLServerBaseOperateDetailSerializer
from backend.ticket.constants import FlowRetryType, TicketType


class SQLServerRenameSerializer(SQLServerBaseOperateDetailSerializer):
    class RenameDatabaseInfoSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        from_database = serializers.CharField(help_text=_("源数据库名"))
        to_database = DBTableField(help_text=_("目标数据库名"), db_field=True)

    infos = serializers.ListField(help_text=_("重命名数据库列表"), child=RenameDatabaseInfoSerializer())

    def validate(self, attrs):
        super().validate(attrs)

        # DB重命名校验，逻辑同mysql
        cluster_ids = [info["cluster_id"] for info in attrs["infos"]]
        cluster__databases = sqlserver_db_function.get_cluster_database(cluster_ids)
        CommonValidate.validate_mysql_db_rename(attrs["infos"], cluster__databases)

        return attrs


class SQLServerRenameFlowParamBuilder(builders.FlowParamBuilder):
    controller = SqlserverController.rename_dbs_scene

    def format_ticket_data(self):
        # 将重命名信息根据cluster id进行聚合
        cluster__dbrename_infos: Dict[int, List[Dict]] = defaultdict(list)
        for info in self.ticket_data["infos"]:
            cluster__dbrename_infos[info["cluster_id"]].append(
                {"db_name": info["from_database"], "target_db_name": info["to_database"]}
            )

        dbrename_infos = [
            {"cluster_id": cluster_id, "rename_infos": infos} for cluster_id, infos in cluster__dbrename_infos.items()
        ]
        self.ticket_data["infos"] = dbrename_infos


@builders.BuilderFactory.register(TicketType.SQLSERVER_DBRENAME)
class SQLServerRenameFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = SQLServerRenameSerializer
    inner_flow_builder = SQLServerRenameFlowParamBuilder
    inner_flow_name = _("SQLServer DB重命名执行")
    retry_type = FlowRetryType.MANUAL_RETRY
