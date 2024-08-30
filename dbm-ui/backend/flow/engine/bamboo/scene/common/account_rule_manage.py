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
import logging
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.components import DBPrivManagerApi
from backend.db_services.dbpermission.constants import RuleActionType
from backend.db_services.dbpermission.db_authorize.models import DBRuleActionLog
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.plugins.components.collections.common.external_service import ExternalServiceComponent

logger = logging.getLogger("flow")


def insert_change_record(params, data, kwargs, global_data):
    DBRuleActionLog.objects.create(
        operator=params["operator"],
        account_id=params["account_id"],
        rule_id=params["rule_id"],
        action_type=params["action"],
    )


class AccountRulesFlows(object):
    """
    账号权限模板管理流程(修改，删除)
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """

        self.root_id = root_id
        self.data = data

    def modify_account_rule(self):
        """定义mysql账号修改流程"""
        account_modify_rules = Builder(root_id=self.root_id, data=self.data)
        account_modify_rules.add_act(
            act_name=_("账号规则模板修改"),
            act_component_code=ExternalServiceComponent.code,
            kwargs={
                "params": {**self.data, "action": RuleActionType.CHANGE},
                "api_import_path": DBPrivManagerApi.__module__,
                "api_import_module": "DBPrivManagerApi",
                "api_call_func": "modify_account_rule",
                "success_callback_path": f"{insert_change_record.__module__}.{insert_change_record.__name__}",
            },
        )
        account_modify_rules.run_pipeline()

    def delete_account_rule(self):
        """定义mysql账号删除流程"""
        account_delete_rules = Builder(root_id=self.root_id, data=self.data)
        account_delete_rules.add_act(
            act_name=_("账号规则模板删除"),
            act_component_code=ExternalServiceComponent.code,
            kwargs={
                "params": {**self.data, "action": RuleActionType.DELETE},
                "api_import_path": DBPrivManagerApi.__module__,
                "api_import_module": "DBPrivManagerApi",
                "api_call_func": "delete_account_rule",
                "success_callback_path": f"{insert_change_record.__module__}.{insert_change_record.__name__}",
            },
        )
        account_delete_rules.run_pipeline()
