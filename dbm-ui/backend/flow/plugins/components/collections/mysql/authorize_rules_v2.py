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
import itertools
import logging
from typing import List

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend import env
from backend.components.mysql_priv_manager.client import DBPrivManagerApi
from backend.configuration.constants import DBType, SystemSettingsEnum
from backend.configuration.models import SystemSettings
from backend.db_services.dbpermission.constants import RuleActionType
from backend.db_services.dbpermission.db_authorize.models import DBRuleActionLog
from backend.flow.engine.bamboo.engine import BambooEngine
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


class AuthorizeRulesV2(BaseService):
    """根据定义的用户规则模板进行授权"""

    @staticmethod
    def _generate_rule_desc(authorize_data):
        # 生成当前规则的描述细则
        rules_product = list(
            itertools.product(
                [authorize_data["user"]],
                authorize_data["access_dbs"],
                [", ".join(authorize_data["source_ips"])],
                authorize_data["target_instances"],
            )
        )
        rules_description = [
            _("{}. 账号规则: {}-{}, 来源ip: {}, 目标集群: {}").format(index + 1, rule[0], rule[1], rule[2], rule[3])
            for index, rule in enumerate(rules_product)
        ]
        rules_description_str = "\n".join(rules_description)
        return rules_description_str

    def _generate_rule_logs(self, bk_biz_id, account_type, operator, authorize_data, user_db_rules_map):
        # 如果该节点是重试，则无需重复记录
        root_id, node_id = self.extra_log["root_id"], self.extra_log["node_id"]
        if BambooEngine(root_id).get_node_short_histories(node_id):
            return
        # 对于虚拟用户的授权，无需记录
        virtual_users = SystemSettings.get_setting_value(key=SystemSettingsEnum.VIRTUAL_USERS, default=[])
        if not user_db_rules_map or operator in virtual_users:
            return
        # 对授权的规则进行授权记录
        auth_logs: List[DBRuleActionLog] = []
        for db in authorize_data["access_dbs"]:
            rule = user_db_rules_map[authorize_data["user"]][db]
            account_id, rule_id = rule["account_id"], rule["id"]
            log = DBRuleActionLog(
                account_id=account_id, rule_id=rule_id, operator=operator, action_type=RuleActionType.AUTH
            )
            auth_logs.append(log)
        DBRuleActionLog.objects.bulk_create(auth_logs)

    @staticmethod
    def _authorize(authorize_data):
        # 对集群进行授权
        try:
            resp = DBPrivManagerApi.authorize_rules_v2(
                params=authorize_data, raw=True, timeout=DBPrivManagerApi.TIMEOUT
            )
            authorize_results = {"code": resp["code"], "message": resp["message"]}
        except Exception as e:  # pylint: disable=broad-except
            error_message = getattr(e, "message", None) or e
            authorize_results = {"code": -1, "message": _("授权接口调用异常: {}").format(error_message)}
        return authorize_results

    def _execute(self, data, parent_data, callback=None) -> bool:
        # kwargs就是调用授权接口传入的参数
        kwargs = data.get_one_of_inputs("kwargs")
        root_id = kwargs.get("root_id")
        ticket_id = kwargs["uid"]
        bk_biz_id = kwargs["bk_biz_id"]
        # TODO: 参数兼容，后续去掉
        db_type = kwargs.get("db_type")
        user_db_rules_map = kwargs.get("user_db_rules_map")
        operator = kwargs.get("operator")
        # authorize_data, 格式为：
        # {"user": xx, "source_ip": [...], "target_instances": [...], "access_db": [...]}
        authorize_data = kwargs.get("authorize_data")

        # 授权规则记录
        self._generate_rule_logs(bk_biz_id, db_type, operator, authorize_data, user_db_rules_map)

        # 生成规则描述
        rules_description = self._generate_rule_desc(authorize_data)
        self.log_info(_("授权规则明细:\n{}\n").format(rules_description))

        # 并发请求授权，打印授权结果
        resp = self._authorize(authorize_data)
        result = resp["code"] == 0
        self.log_info(resp["message"])
        self.set_flow_output(root_id=root_id, key="authorize_results", value=resp["message"])

        # 打印授权结果详情链接下载
        # 下载excel的url中，mysql和tendbcluster同用一个路由
        route_type = DBType.MySQL.value if db_type == DBType.TenDBCluster else db_type
        self.log_info(
            _(
                "授权结果详情请下载excel: <a href='{}/apis/{}/bizs/{}/permission/authorize/"
                "get_authorize_info_excel/?ticket_id={}'>excel 下载</a>"
            ).format(env.BK_SAAS_HOST, route_type, bk_biz_id, ticket_id)
        )
        return result

    def inputs_format(self) -> List:
        return [Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True)]


class AuthorizeRulesV2Component(Component):
    name = __name__
    code = "authorize_rules_v2"
    bound_service = AuthorizeRulesV2
