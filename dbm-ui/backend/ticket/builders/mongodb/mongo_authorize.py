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

from backend.db_services.dbpermission.db_authorize.serializers import PreCheckAuthorizeRulesSerializer
from backend.db_services.mysql.permission.exceptions import AuthorizeDataHasExpiredException
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.ticket import builders
from backend.ticket.builders.mongodb.base import BaseMongoDBTicketFlowBuilder
from backend.ticket.constants import TicketType


class MongoDBAuthorizeRulesSerializer(serializers.Serializer):
    authorize_uid = serializers.CharField(help_text=_("授权数据缓存uid"))
    authorize_data = serializers.ListSerializer(help_text=_("授权数据列表"), child=serializers.JSONField(), required=False)

    def validate(self, attrs):
        return attrs


class MongoDBExcelAuthorizeDataSerializer(PreCheckAuthorizeRulesSerializer):
    pass


class MongodbExcelAuthorizeRulesSerializer(serializers.Serializer):
    authorize_uid = serializers.CharField(help_text=_("授权数据缓存uid"))
    excel_url = serializers.CharField(help_text=_("用户输入的excel下载文件地址"))
    authorize_data_list = serializers.ListSerializer(
        help_text=_("授权数据信息列表"), child=serializers.JSONField(), required=False
    )


class MongoDBAuthorizeRulesFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.create_user


@builders.BuilderFactory.register(TicketType.MONGODB_AUTHORIZE)
class MongoDBAuthorizeRulesFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoDBAuthorizeRulesSerializer
    inner_flow_builder = MongoDBAuthorizeRulesFlowParamBuilder
    inner_flow_name = _("MongoDB 授权执行")

    def patch_ticket_detail(self):
        details = self.ticket.details
        data = cache.get(details.get("authorize_uid"))
        if not data:
            raise AuthorizeDataHasExpiredException(_("授权数据不存在/已过期，请重新提交授权表单或excel文件"))

        self.ticket.update_details(infos=data)


@builders.BuilderFactory.register(TicketType.MONGODB_EXCEL_AUTHORIZE)
class MySQLExcelAuthorizeRulesFlowBuilder(MongoDBAuthorizeRulesFlowBuilder):
    serializer = MongodbExcelAuthorizeRulesSerializer
    inner_flow_name = _("MongoDB Excel授权执行")
