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

from django.core.cache import cache
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend import env
from backend.db_services.dbpermission.db_authorize.serializers import PreCheckAuthorizeRulesSerializer
from backend.db_services.mysql.permission.exceptions import AuthorizeDataHasExpiredException
from backend.flow.engine.controller.sqlserver import SqlserverController
from backend.ticket import builders
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder
from backend.ticket.constants import TicketType


class SQLServerAuthorizeRulesSerializer(serializers.Serializer):
    authorize_uid = serializers.CharField(help_text=_("授权数据缓存uid"))
    authorize_data = serializers.ListSerializer(
        child=PreCheckAuthorizeRulesSerializer(), help_text=_("授权数据信息"), required=False
    )

    def validate(self, attrs):
        return attrs


class SQLServerExcelAuthorizeRulesSerializer(serializers.Serializer):
    authorize_uid = serializers.CharField(help_text=_("授权数据缓存uid"))
    excel_url = serializers.CharField(help_text=_("用户输入的excel下载文件地址"))
    authorize_data_list = serializers.ListSerializer(
        help_text=_("授权数据信息列表"), child=PreCheckAuthorizeRulesSerializer(), required=False
    )


class SQLServerAuthorizeRulesFlowParamBuilder(builders.FlowParamBuilder):
    controller = SqlserverController.authorize

    def post_callback(self):
        excel_url = (
            f"{env.BK_SAAS_HOST}/apis/sqlserver/bizs/{self.ticket.bk_biz_id}/"
            f"permission/authorize/get_authorize_info_excel/?ticket_id={self.ticket.id}"
        )
        flow = self.ticket.current_flow()
        flow.details.update({"authorize_result_excel_url": excel_url})
        flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.SQLSERVER_AUTHORIZE_RULES)
class SQLServerRulesFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = SQLServerAuthorizeRulesSerializer
    inner_flow_builder = SQLServerAuthorizeRulesFlowParamBuilder
    inner_flow_name = _("SQLServer 授权执行")

    default_need_itsm = False
    default_need_manual_confirm = False
    editable = False

    def patch_ticket_detail(self):
        details = self.ticket.details
        data = cache.get(details.get("authorize_uid"))
        if not data:
            raise AuthorizeDataHasExpiredException(_("授权数据不存在/已过期，请重新提交授权表单或excel文件"))
        self.ticket.update_details(rules_set=data)


@builders.BuilderFactory.register(TicketType.SQLSERVER_EXCEL_AUTHORIZE_RULES)
class SQLServerExcelAuthorizeRulesFlowBuilder(SQLServerRulesFlowBuilder):
    serializer = SQLServerExcelAuthorizeRulesSerializer
    inner_flow_name = _("SQLServer Excel授权执行")
