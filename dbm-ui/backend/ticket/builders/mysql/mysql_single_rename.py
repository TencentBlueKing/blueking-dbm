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

from backend.db_meta.enums import ClusterType
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.mysql.base import BaseMySQLSingleTicketFlowBuilder
from backend.ticket.builders.mysql.mysql_ha_rename import MySQLHaRenameFlowParamBuilder, MySQLHaRenameSerializer
from backend.ticket.constants import TicketType


class MySQLSingleRenameDetailSerializer(MySQLHaRenameSerializer):
    def validate(self, attrs):
        super().validate_cluster_can_access(attrs)
        # 集群类型校验
        super().validated_cluster_type(attrs, cluster_type=ClusterType.TenDBSingle)
        # DB重命名校验
        super().validate_rename_db(attrs)
        return attrs


class MySQLSingleRenameFlowParamBuilder(MySQLHaRenameFlowParamBuilder):
    controller = MySQLController.mysql_single_rename_database_scene


@builders.BuilderFactory.register(TicketType.MYSQL_SINGLE_RENAME_DATABASE)
class MySQLSingleClearFlowBuilder(BaseMySQLSingleTicketFlowBuilder):
    serializer = MySQLSingleRenameDetailSerializer
    inner_flow_builder = MySQLSingleRenameFlowParamBuilder
    inner_flow_name = _("MySQL 单节点DB重命名执行")
