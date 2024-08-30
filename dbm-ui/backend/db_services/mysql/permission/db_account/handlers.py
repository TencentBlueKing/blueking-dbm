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
from typing import Any, Optional

from django.utils.translation import ugettext as _

from backend.components import DBPrivManagerApi
from backend.db_services.dbpermission.constants import PrivilegeType
from backend.db_services.dbpermission.db_account.dataclass import AccountRuleMeta
from backend.db_services.dbpermission.db_account.handlers import AccountHandler
from backend.db_services.mysql.permission.exceptions import DBPermissionBaseException

logger = logging.getLogger("root")


class MySQLAccountHandler(AccountHandler):
    """
    封装账号相关的处理操作
    """

    def pre_check_add_account_rule(self, account_rule: AccountRuleMeta) -> Optional[Any]:
        """
        - 添加账号规则前置检查
        @param account_rule: 账号规则元信息
        """
        account_rule_params = {
            "bk_biz_id": self.bk_biz_id,
            "operator": self.operator,
            "cluster_type": self.account_type,
            "account_id": account_rule.account_id,
            "priv": account_rule.privilege,
            "dbname": account_rule.access_db,
        }
        resp = DBPrivManagerApi.pre_check_add_account_rule(params=account_rule_params, raw=True)
        # 如果不允许执行，说明前置检查失败，抛出message
        if not resp["data"]["force_run"]:
            raise DBPermissionBaseException(_("创建授权规则前置检查失败，错误信息: {}").format(resp["message"]))
        return {"force_run": resp["data"]["force_run"], "warning": resp["message"]}

    def has_high_risk_privileges(self, rule_sets):
        """
        - 判断是否有高危权限
        @param rule_sets: 授权列表，数据结构与MySQLPrivManagerApi.authorize_rules接口相同
        """
        risk_priv_set = set(PrivilegeType.MySQL.GLOBAL.get_values())
        user_db__rules = self.aggregate_user_db_rules(self.bk_biz_id, self.account_type)
        # 判断是否有高危权限
        for rule_set in rule_sets:
            for rule in rule_set["account_rules"]:
                try:
                    privileges = user_db__rules[rule_set["user"]][rule["dbname"]].split(",")
                    if risk_priv_set.intersection(set(privileges)):
                        return True
                except KeyError:
                    raise DBPermissionBaseException(
                        _("授权规则{}-{}不存在，bk_biz_id[{}] cluster_type[{}], 请检查检查后重新提单").format(
                            rule_set["user"], rule["dbname"], self.bk_biz_id, self.account_type
                        )
                    )
        return False
