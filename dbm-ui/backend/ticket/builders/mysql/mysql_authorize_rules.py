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
from backend.db_meta.enums import ClusterType
from backend.db_services.dbpermission.db_authorize.serializers import PreCheckAuthorizeRulesSerializer
from backend.db_services.mysql.permission.exceptions import AuthorizeDataHasExpiredException
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder
from backend.ticket.constants import TicketType


class MySQLPluginInfoSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    user = serializers.CharField(help_text=_("授权账号"))
    access_dbs = serializers.ListSerializer(child=serializers.CharField(), help_text=_("准入DB"))
    source_ips = serializers.ListField(help_text=_("源IP列表"), child=serializers.CharField())
    target_instances = serializers.ListField(help_text=_("目标集群域名"), child=serializers.CharField())
    cluster_type = serializers.ChoiceField(help_text=_("集群类型"), choices=ClusterType.get_choices())


class MySQLAuthorizeDataSerializer(PreCheckAuthorizeRulesSerializer):
    privileges = serializers.JSONField(help_text=_("授权详情"), required=False)


class MySQLAuthorizeRulesSerializer(serializers.Serializer):
    authorize_uid = serializers.CharField(help_text=_("授权数据缓存uid"), required=False)
    authorize_data = MySQLAuthorizeDataSerializer(help_text=_("授权数据信息"), required=False)
    authorize_plugin_infos = serializers.ListSerializer(
        help_text=_("第三方接口/插件授权信息"), child=MySQLPluginInfoSerializer(), required=False
    )
    need_itsm = serializers.BooleanField(help_text=_("是否需要审批"), required=False, default=True)

    def validate(self, attrs):
        if not (attrs.get("authorize_plugin_infos") or attrs.get("authorize_uid")):
            raise serializers.ValidationError(_("请保证授权数据存在"))

        if attrs.get("authorize_plugin_infos"):
            infos = attrs["authorize_plugin_infos"]
            for info in infos:
                info["account_rules"] = [{"bk_biz_id": info["bk_biz_id"], "dbname": db} for db in info["access_dbs"]]
                info["operator"] = self.context["request"].user.username

        return attrs


class MySQLExcelAuthorizeDataSerializer(PreCheckAuthorizeRulesSerializer):
    source_ips = serializers.ListField(help_text=_("ip列表"), child=serializers.CharField())
    privileges = serializers.JSONField(help_text=_("授权详情"), required=False)


class MySQLExcelAuthorizeRulesSerializer(serializers.Serializer):
    authorize_uid = serializers.CharField(help_text=_("授权数据缓存uid"))
    excel_url = serializers.CharField(help_text=_("用户输入的excel下载文件地址"))
    authorize_data_list = serializers.ListSerializer(
        help_text=_("授权数据信息列表"), child=MySQLExcelAuthorizeDataSerializer()
    )


class MySQLAuthorizeRulesFlowParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_authorize_rules

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
    inner_flow_name = _("MySQL 授权执行")
    editable = False

    @property
    def need_itsm(self):
        # 授权无需审批
        return False

    @property
    def need_manual_confirm(self):
        # 授权无需人工确认
        return False

    def patch_ticket_detail(self):
        details = self.ticket.details
        data = cache.get(details.get("authorize_uid")) or details.get("authorize_plugin_infos")
        if not data:
            raise AuthorizeDataHasExpiredException(_("授权数据不存在/已过期，请重新提交授权表单或excel文件"))
        self.ticket.update_details(rules_set=data)


@builders.BuilderFactory.register(TicketType.MYSQL_EXCEL_AUTHORIZE_RULES)
class MySQLExcelAuthorizeRulesFlowBuilder(MySQLAuthorizeRulesFlowBuilder):
    serializer = MySQLExcelAuthorizeRulesSerializer
    inner_flow_name = _("MySQL Excel授权执行")
