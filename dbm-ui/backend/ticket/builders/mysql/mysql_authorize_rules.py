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
from backend.db_services.mysql.permission.authorize.serializers import PreCheckAuthorizeRulesSerializer
from backend.db_services.mysql.permission.exceptions import AuthorizeDataHasExpiredException
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder
from backend.ticket.constants import FlowRetryType, FlowType, TicketType
from backend.ticket.models import Flow


class MySQLAuthorizeDataSerializer(PreCheckAuthorizeRulesSerializer):
    pass


class MySQLAuthorizeRulesSerializer(serializers.Serializer):
    authorize_uid = serializers.CharField(help_text=_("授权数据缓存uid"))
    authorize_data = MySQLAuthorizeDataSerializer(help_text=_("授权数据信息"))


class MySQLExcelAuthorizeDataSerializer(PreCheckAuthorizeRulesSerializer):
    source_ips = serializers.ListField(help_text=_("ip列表"), child=serializers.CharField())


class MySQLExcelAuthorizeRulesSerializer(serializers.Serializer):
    authorize_uid = serializers.CharField(help_text=_("授权数据缓存uid"))
    excel_url = serializers.CharField(help_text=_("用户输入的excel下载文件地址"))
    authorize_data_list = serializers.ListSerializer(
        help_text=_("授权数据信息列表"), child=MySQLExcelAuthorizeDataSerializer()
    )


class MySQLAuthorizeRulesFlowParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_authorize_rules

    def format_ticket_data(self):
        authorize_uid = self.ticket_data["authorize_uid"]
        data = cache.get(authorize_uid)

        if not data:
            raise AuthorizeDataHasExpiredException(_("授权数据已过期，请重新提交授权表单或excel文件"))

        self.ticket_data.update({"rules_set": data})

    def post_callback(self):
        excel_url = (
            f"{env.BK_SAAS_HOST}/apis/mysql/bizs/{self.ticket.bk_biz_id}/"
            f"permission/authorize/get_authorize_info_excel/?ticket_id={self.ticket.id}"
        )
        flow = self.ticket.current_flow()
        flow.details.update({"authorize_result_excel_url": excel_url})
        flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.MYSQL_AUTHORIZE_RULES)
class MySQLAuthorizeRulesFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MySQLAuthorizeRulesSerializer
    inner_flow_builder = MySQLAuthorizeRulesFlowParamBuilder
    inner_flow_name = _("授权执行")

    @property
    def need_itsm(self):
        return False


@builders.BuilderFactory.register(TicketType.MYSQL_EXCEL_AUTHORIZE_RULES)
class MySQLExcelAuthorizeRulesFlowBuilder(MySQLAuthorizeRulesFlowBuilder):
    serializer = MySQLExcelAuthorizeRulesSerializer
    inner_flow_name = _("Excel 授权执行")
