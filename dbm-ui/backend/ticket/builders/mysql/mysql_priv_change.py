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

from django.utils.translation import ugettext as _
from rest_framework import serializers

from backend.db_services.dbpermission.constants import RuleActionType
from backend.db_services.dbpermission.db_account.dataclass import AccountRuleMeta
from backend.db_services.dbpermission.db_account.serializers import ModifyAccountRuleSerializer
from backend.db_services.dbpermission.db_authorize.models import DBRuleActionLog
from backend.flow.engine.controller.mysql import MySQLController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder
from backend.ticket.constants import FlowRetryType, ItsmApproveMode, TicketType


class MySQLAccountRuleChangeSerializer(ModifyAccountRuleSerializer):
    last_account_rules = serializers.JSONField(help_text=_("上次账号规则"))
    action = serializers.ChoiceField(help_text=_("变更类型(修改/删除)"), choices=RuleActionType.get_choices())


class MySQLAccountRuleChangeFlowParamBuilder(builders.FlowParamBuilder):
    delete_controller = MySQLController.mysql_account_rules_delete
    change_controller = MySQLController.mysql_account_rules_change

    def format_ticket_data(self):
        self.ticket_data.update(
            cluster_type=self.ticket_data["account_type"],
            operator=self.ticket.creator,
        )
        if self.ticket_data["action"] == RuleActionType.CHANGE:
            self.ticket_data.update(
                id=self.ticket_data["rule_id"],
                dbname=self.ticket_data["access_db"],
                priv=AccountRuleMeta(privilege=self.ticket_data["privilege"]).privilege,
            )
        else:
            self.ticket_data.update(id=[self.ticket_data["rule_id"]])

    def build_controller_info(self) -> dict:
        if self.ticket_data["action"] == RuleActionType.CHANGE:
            self.controller = self.change_controller
        elif self.ticket_data["action"] == RuleActionType.DELETE:
            self.controller = self.delete_controller
        return super().build_controller_info()


class MySQLAccountRuleChangeItsmFlowParamBuilder(builders.ItsmParamBuilder):
    def get_params(self):
        params = super().get_params()
        field_map = {field["key"]: field["value"] for field in params["fields"]}
        # 获取权限审批人
        approver_list = DBRuleActionLog.get_notifiers(self.ticket.details["rule_id"])
        field_map["approver"] = ",".join(approver_list)
        # 审批模式改成会签
        field_map["approve_mode"] = ItsmApproveMode.CounterSign
        # 导出itsm字段
        params["fields"] = [{"key": key, "value": value} for key, value in field_map.items()]
        return params


@builders.BuilderFactory.register(TicketType.MYSQL_ACCOUNT_RULE_CHANGE, iam=ActionEnum.MYSQL_ADD_ACCOUNT_RULE)
class MySQLAccountRuleChangeFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MySQLAccountRuleChangeSerializer
    inner_flow_builder = MySQLAccountRuleChangeFlowParamBuilder
    itsm_flow_builder = MySQLAccountRuleChangeItsmFlowParamBuilder
    retry_type = FlowRetryType.MANUAL_RETRY

    @property
    def need_itsm(self):
        approver_list = DBRuleActionLog.get_notifiers(self.ticket.details["rule_id"])
        return bool(approver_list)
