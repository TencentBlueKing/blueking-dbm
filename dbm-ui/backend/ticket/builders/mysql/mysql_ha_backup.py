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

from typing import List

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.db_meta.enums import InstanceInnerRole
from backend.db_meta.models import Cluster
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder, MySQLBaseOperateDetailSerializer
from backend.ticket.constants import FlowRetryType, FlowType, TicketType
from backend.ticket.models import Flow


class MySQLHaBackupDetailSerializer(MySQLBaseOperateDetailSerializer):
    class BackupDataInfoSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        db_patterns = serializers.ListField(help_text=_("匹配DB列表"), child=serializers.CharField())
        ignore_dbs = serializers.ListField(help_text=_("忽略DB列表"), child=serializers.CharField())
        table_patterns = serializers.ListField(help_text=_("匹配Table列表"), child=serializers.CharField())
        ignore_tables = serializers.ListField(help_text=_("忽略Table列表"), child=serializers.CharField())
        # 废弃backup_on参数，暂时不需要传递
        # backup_on = serializers.ChoiceField(choices=InstanceInnerRole.get_choices(), help_text=_("备份源"))

    infos = serializers.ListSerializer(help_text=_("备份信息列表"), child=BackupDataInfoSerializer())

    def validate(self, attrs):
        """验证库表数据库的数据"""
        super().validate(attrs)

        # 库表选择器校验
        super().validate_database_table_selector(attrs)

        return attrs


class MySQLHaBackupFlowParamBuilder(builders.FlowParamBuilder):
    """MySQL HA 备份执行单据参数"""

    controller = MySQLController.mysql_ha_db_table_backup_scene


@builders.BuilderFactory.register(TicketType.MYSQL_HA_DB_TABLE_BACKUP)
class MySQLHaBackupFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MySQLHaBackupDetailSerializer
    inner_flow_builder = MySQLHaBackupFlowParamBuilder
    inner_flow_name = _("库表备份执行")
    retry_type = FlowRetryType.MANUAL_RETRY
