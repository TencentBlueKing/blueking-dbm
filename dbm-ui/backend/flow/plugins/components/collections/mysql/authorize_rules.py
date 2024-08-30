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
from typing import Any, Dict, List, Tuple

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend import env
from backend.components.mysql_priv_manager.client import DBPrivManagerApi
from backend.configuration.constants import DBType
from backend.db_services.dbpermission.constants import RuleActionType
from backend.db_services.dbpermission.db_account.handlers import AccountHandler
from backend.db_services.dbpermission.db_authorize.models import DBRuleActionLog
from backend.flow.engine.bamboo.engine import BambooEngine
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class AuthorizeRules(BaseService):
    """根据定义的用户规则模板进行授权"""

    @staticmethod
    def _generate_rule_desc(authorize_data):
        # 生成当前规则的描述细则
        rules_product: List[Tuple[Any, ...]] = list(
            itertools.product(
                [authorize_data["user"]],
                authorize_data["access_dbs"],
                [", ".join(authorize_data["source_ips"])],
                authorize_data["target_instances"],
            )
        )
        rules_description: str = "\n".join(
            [
                _("{}. 账号规则: {}-{}, 来源ip: {}, 目标集群: {}").format(index + 1, rule[0], rule[1], rule[2], rule[3])
                for index, rule in enumerate(rules_product)
            ]
        )
        return rules_description

    def _generate_rule_logs(self, bk_biz_id, account_type, operator, authorize_data_list):
        # 如果该节点是重试，则无需重复记录
        root_id, node_id = self.extra_log["root_id"], self.extra_log["node_id"]
        if BambooEngine(root_id).get_node_short_histories(node_id):
            return

        # 对授权的规则进行授权记录
        user__db_rules: Dict[str, Dict] = AccountHandler.aggregate_user_db_rules(bk_biz_id, account_type, rule_key="")
        auth_logs: List[DBRuleActionLog] = []
        for data in authorize_data_list:
            for db in data["access_dbs"]:
                rule = user__db_rules[data["user"]][db]
                log = DBRuleActionLog(
                    account_id=rule["account_id"],
                    rule_id=rule["id"],
                    operator=operator,
                    action_type=RuleActionType.AUTH,
                )
                auth_logs.append(log)
        DBRuleActionLog.objects.bulk_create(auth_logs)

    def _execute(self, data, parent_data, callback=None) -> bool:

        # kwargs就是调用授权接口传入的参数
        kwargs = data.get_one_of_inputs("kwargs")
        ticket_id = kwargs["uid"]
        ticket_type = kwargs["ticket_type"]
        db_type = TicketType.get_db_type_by_ticket(ticket_type)
        bk_biz_id = kwargs["bk_biz_id"]

        # authorize_data_list的单个元素是authorize_data, 格式为：
        # {"user": xx, "source_ip": [...], "target_instances": [...], "access_db": [...]}
        authorize_data_list: List[Dict] = kwargs["rules_set"]
        authorize_success_count: int = 0

        # 授权规则记录
        self._generate_rule_logs(bk_biz_id, db_type, kwargs["created_by"], authorize_data_list)

        for authorize_data in authorize_data_list:
            # 生成规则描述
            rules_description = self._generate_rule_desc(authorize_data)
            self.log_info(_("授权规则明细:\n{}\n").format(rules_description))

            # 进行授权，无论授权是否成功，都需要将message存入record中
            try:
                resp = DBPrivManagerApi.authorize_rules(authorize_data, raw=True, timeout=DBPrivManagerApi.TIMEOUT)
                if int(resp["code"]) == 0:
                    authorize_success_count += 1
                authorize_results = resp["message"]
                self.log_info(authorize_results)
            except Exception as e:  # pylint: disable=broad-except
                error_message = getattr(e, "message", None) or e
                authorize_results = _("「授权接口调用异常」{}").format(error_message)
                self.log_error(_("授权异常，相关信息: {}\n").format(authorize_results))

            # 作为结果输出到flow
            self.set_flow_output(root_id=kwargs.get("root_id"), key="authorize_results", value=authorize_results)

        # 授权结果汇总
        overall_result = authorize_success_count == len(authorize_data_list)
        overall_result_alias = _("成功") if overall_result else _("失败")
        self.log_info(_("授权整体结果{}").format(overall_result_alias))
        # 如果是excel导入授权，则增加增加excel导入授权总览
        if "EXCEL" in ticket_type:
            self.log_info(
                _("Excel导入授权行数:{}，成功授权数目:{}，失败授权数目:{}").format(
                    len(authorize_data_list),
                    authorize_success_count,
                    len(authorize_data_list) - authorize_success_count,
                )
            )

        # 打印授权结果详情链接下载
        # 下载excel的url中，mysql和tendbcluster同用一个路由
        route_type = DBType.MySQL.value if db_type == DBType.TenDBCluster else db_type
        self.log_info(
            _(
                "授权结果详情请下载excel: <a href='{}/apis/{}/bizs/{}/permission/authorize/"
                "get_authorize_info_excel/?ticket_id={}'>excel 下载</a>"
            ).format(env.BK_SAAS_HOST, route_type, bk_biz_id, ticket_id)
        )
        return overall_result

    def inputs_format(self) -> List:
        return [Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True)]


class AuthorizeRulesComponent(Component):
    name = __name__
    code = "authorize_rules"
    bound_service = AuthorizeRules
