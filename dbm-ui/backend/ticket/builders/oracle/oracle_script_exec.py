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
from rest_framework import serializers

from backend.db_services.mysql.sql_import.constants import SQLImportMode
from backend.db_services.oracle.sql_import.constants import BKREPO_ORACLE_SQLFILE_PATH
from backend.flow.engine.controller.oracle import OracleController
from backend.ticket import builders
from backend.ticket.builders.common.base import SkipToRepresentationMixin
from backend.ticket.builders.oracle.base import BaseOracleTicketFlowBuilder
from backend.ticket.constants import TicketType


class OracleScriptExecDetailSerializer(SkipToRepresentationMixin, serializers.Serializer):
    class ClusterDetailSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群id"))
        execute_db = serializers.ListField(help_text=_("执行的db"), child=serializers.CharField())

    cluster_info = serializers.ListField(help_text=_("集群执行列表"), child=ClusterDetailSerializer())
    script_files = serializers.ListField(help_text=_("脚本文件列表"), child=serializers.CharField())

    import_mode = serializers.ChoiceField(help_text=_("sql导入模式"), choices=SQLImportMode.get_choices())

    def validate(self, attrs):
        attrs["path"] = BKREPO_ORACLE_SQLFILE_PATH.format(biz=self.context["bk_biz_id"])
        return attrs


class OracleScriptExecFlowParamBuilder(builders.FlowParamBuilder):
    controller = OracleController.multi_oracle_execute_script


@builders.BuilderFactory.register(TicketType.ORACLE_EXEC_SCRIPT_APPLY)
class OracleScriptExecApplyFlowBuilder(BaseOracleTicketFlowBuilder):
    serializer = OracleScriptExecDetailSerializer
    inner_flow_builder = OracleScriptExecFlowParamBuilder
    inner_flow_name = _("Oracle 变更脚本执行执行")
