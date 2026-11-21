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

import backend.flow.utils.mysql.dts.precheck.items  # noqa: F401
from backend.flow.engine.controller.mysql import MySQLController
from backend.flow.utils.mysql.dts.precheck.base import all_items
from backend.flow.utils.mysql.dts.precheck.migrate_input import expand_precheck_pairs
from backend.ticket import builders
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder
from backend.ticket.constants import TicketType


class MysqlDtsPrecheckDetailSerializer(serializers.Serializer):
    """与迁移单同一套入口。有 infos 时每行一个 one_to_one，且不能再带顶层 migrate；否则用顶层 migrate。"""

    migrate = serializers.DictField(required=False, help_text=_("迁移拓扑，与迁移单据 migrate 相同"))
    infos = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text=_("多行迁移任务，每行含 migrate"),
    )
    enabled_codes = serializers.ListField(
        child=serializers.ChoiceField(choices=()),
        required=False,
        allow_empty=False,
        help_text=_("启用的检查项；默认全部"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["enabled_codes"].child.choices = [(item.code, item.name) for item in all_items()]

    def validate(self, attrs):
        try:
            expand_precheck_pairs(attrs)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        attrs.setdefault("enabled_codes", [item.code for item in all_items()])
        return attrs


class MysqlDtsPrecheckFlowParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_dts_precheck_scene


@builders.BuilderFactory.register(TicketType.MYSQL_DTS_PRECHECK)
class MysqlDtsPrecheckFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MysqlDtsPrecheckDetailSerializer
    inner_flow_builder = MysqlDtsPrecheckFlowParamBuilder
    inner_flow_name = _("MySQL DTS 迁移预检查")
    editable = False

    @property
    def need_itsm(self):
        return False

    @property
    def need_manual_confirm(self):
        return False
