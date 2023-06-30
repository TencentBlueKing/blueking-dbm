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

import json
from collections import defaultdict
from typing import Dict, List

from django.utils.translation import ugettext as _
from rest_framework import serializers

from backend.flow.consts import SYSTEM_DBS
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.common.base import CommonValidate
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder, MySQLBaseOperateDetailSerializer
from backend.ticket.constants import FlowRetryType, FlowType, TicketType
from backend.ticket.models import Flow


class MySQLHaRenameSerializer(MySQLBaseOperateDetailSerializer):
    class RenameDatabaseInfoSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        from_database = serializers.CharField(help_text=_("源数据库名"))
        to_database = serializers.CharField(help_text=_("目标数据库名"))
        force = serializers.BooleanField(help_text=_("是否强制执行"), default=False)

    infos = serializers.ListField(help_text=_("重命名数据库列表"), child=RenameDatabaseInfoSerializer())

    def validate(self, attrs):
        super().validate(attrs)

        cluster__db_name_map: Dict[int, Dict[str, List]] = defaultdict(
            lambda: {"from_database": [], "to_database": []}
        )

        for db_info in attrs["infos"]:
            cluster__db_name_map[db_info["cluster_id"]]["from_database"].append(db_info["from_database"])
            cluster__db_name_map[db_info["cluster_id"]]["to_database"].append(db_info["to_database"])

            # 校验新db name是否合法
            is_valid, message = CommonValidate.validate_db_name(db_info["to_database"])
            if not is_valid:
                raise serializers.ValidationError(message)

        # 校验在同一个集群内，源DB名必须唯一，新DB名必须唯一，且源DB名不能出现在新DB名中
        for cluster_id, name_info in cluster__db_name_map.items():
            from_database_list = name_info["from_database"]
            for db_name in from_database_list:
                if db_name in SYSTEM_DBS:
                    raise serializers.ValidationError(_("系统内置数据库[{}]，不允许重命名").format(db_name))
            to_database_list = name_info["to_database"]
            if len(set(from_database_list)) != len(from_database_list):
                raise serializers.ValidationError(_("请保证集群{}中源数据库名{}的名字唯一").format(cluster_id, from_database_list))

            if len(set(to_database_list)) != len(to_database_list):
                raise serializers.ValidationError(_("请保证集群{}中新数据库名{}的名字唯一").format(cluster_id, to_database_list))

            intersected_db_names = set(from_database_list).intersection(set(to_database_list))
            if intersected_db_names:
                raise serializers.ValidationError(_("请保证源数据库名{}不要出现在新数据库名列表中").format(intersected_db_names))

        return attrs


class MySQLHaRenameFlowParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_ha_rename_database_scene

    def format_ticket_data(self):
        pass


@builders.BuilderFactory.register(TicketType.MYSQL_HA_RENAME_DATABASE)
class MySQLHaRenameFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MySQLHaRenameSerializer
    inner_flow_builder = MySQLHaRenameFlowParamBuilder
    inner_flow_name = _("DB重命名执行")
    retry_type = FlowRetryType.MANUAL_RETRY
