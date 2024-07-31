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
from collections import defaultdict
from typing import Any, Dict, List, Optional

from django.utils.translation import ugettext as _
from iam.resource.utils import FancyDict

from backend.components.mysql_priv_manager.client import DBPrivManagerApi
from backend.core.encrypt.constants import AsymmetricCipherConfigType
from backend.core.encrypt.handlers import AsymmetricHandler
from backend.db_services.dbpermission.constants import DPRIV_PARAMETER_MAP, AccountType
from backend.db_services.dbpermission.db_account.dataclass import AccountMeta, AccountRuleMeta
from backend.db_services.dbpermission.db_account.signals import create_account_signal
from backend.db_services.mysql.open_area.models import TendbOpenAreaConfig
from backend.db_services.mysql.permission.exceptions import DBPermissionBaseException

logger = logging.getLogger("root")


class AccountHandler(object):
    """
    封装账号相关的处理操作
    """

    def __init__(self, bk_biz_id: int, account_type: AccountType, operator: str = None, context: Dict = None):
        """
        @param bk_biz_id: 业务ID
        @param account_type: 账号类型，目前区分与mysql和tendbcluster
        @param operator: 操作者
        @param context: 上下文数据
        """
        self.bk_biz_id = int(bk_biz_id)
        self.account_type = account_type
        self.operator = operator
        self.context = context

    @staticmethod
    def _decrypt_password(password: str) -> str:
        """
        - 获取saas侧私钥，将password利用私钥解密
        :param password: 待解密密码
        """
        return AsymmetricHandler.decrypt(
            name=AsymmetricCipherConfigType.PASSWORD.value, content=password, salted=False
        )

    def _format_account_rules(self, account_rules_list: Dict) -> Dict:
        """格式化账号权限列表信息"""
        for account_rules in account_rules_list["items"]:
            account_rules["account"]["account_id"] = account_rules["account"].pop("id")

            # 检查 rules 是否为 None
            if account_rules.get("rules") is None:
                account_rules["rules"] = []

            for rule in account_rules["rules"]:
                rule["rule_id"] = rule.pop("id")
                rule["access_db"] = rule.pop("dbname")
                rule["privilege"] = rule.pop("priv")

        return account_rules_list

    def create_account(self, account: AccountMeta) -> Optional[Any]:
        """
        - 新建一个账号
        @param account: 账号元信息
        """
        resp = DBPrivManagerApi.create_account(
            {
                "cluster_type": self.account_type,
                "bk_biz_id": self.bk_biz_id,
                "operator": self.operator,
                "user": account.user,
                "psw": account.password,
            }
        )
        # 获取新建账号信息 TODO: 这段逻辑在create_account返回账号信息后可以去掉
        account_data = DBPrivManagerApi.get_account(
            params={"bk_biz_id": self.bk_biz_id, "cluster_type": self.account_type, "user_like": account.user}
        )["results"]
        account = {info["user"]: info for info in account_data}.get(account.user)
        account.update(account_type=self.account_type)
        create_account_signal.send(sender=None, account=FancyDict(account))

        return resp

    def delete_account(self, account: AccountMeta) -> Optional[Any]:
        """
        - 删除账号(仅在账号不存在存量规则时)
        @param account: 账号元信息
        """
        resp = DBPrivManagerApi.delete_account(
            {
                "bk_biz_id": self.bk_biz_id,
                "operator": self.operator,
                "cluster_type": self.account_type,
                "id": account.account_id,
            }
        )
        return resp

    def update_password(self, account: AccountMeta) -> Optional[Any]:
        """
        - 修改账号密码
        @param account: 账号元信息
        """
        resp = DBPrivManagerApi.update_password(
            {
                "cluster_type": self.account_type,
                "bk_biz_id": self.bk_biz_id,
                "operator": self.operator,
                "id": account.account_id,
                "psw": account.password,
            }
        )
        return resp

    def add_account_rule(self, account_rule: AccountRuleMeta) -> Optional[Any]:
        """
        - 添加账号规则
        @param account_rule: 账号规则元信息
        """
        resp = DBPrivManagerApi.add_account_rule(
            {
                "bk_biz_id": self.bk_biz_id,
                "creator": self.operator,
                "cluster_type": self.account_type,
                "account_id": account_rule.account_id,
                "priv": account_rule.privilege,
                "dbname": account_rule.access_db,
            }
        )
        return resp

    def query_account_rules(self, account_rule: AccountRuleMeta):
        """查询某个账号下的权限"""

        account_rules_list = DBPrivManagerApi.list_account_rules(
            {
                "bk_biz_id": self.bk_biz_id,
                "cluster_type": self.account_type,
                "user": account_rule.user,
                "no_rule_user": True,
            }
        )

        if not account_rules_list["items"]:
            return {"count": 0, "results": []}

        account_rules_list = self._format_account_rules(account_rules_list)

        # 根据账号名和准许db过滤规则
        filter_account_rules_list: List[Dict[str, Any]] = []
        for account_rules in account_rules_list["items"]:
            filter_rules = []
            for rule in account_rules["rules"]:
                if not account_rule.access_dbs or (rule["access_db"] in account_rule.access_dbs):
                    filter_rules.append(rule)

            filter_account_rules_list.append({"account": account_rules["account"], "rules": filter_rules})

        return {"count": len(filter_account_rules_list), "results": filter_account_rules_list}

    def list_account_rules(self, rule_filter: AccountRuleMeta) -> Dict:
        """列举规则清单"""

        # 使用字典推导式排除值为None的键值对，并替换指定的键，同时确保新字典中的值不为None
        params = {DPRIV_PARAMETER_MAP.get(k, k): v for k, v in rule_filter.to_dict().items() if v is not None}

        # 判断无过滤条件 或者过滤条件只有user 则展示无规则用户
        no_filter = "user" not in params and "dbname" not in params and "privs" not in params
        filter_only_user = "user" in params and "dbname" not in params and "privs" not in params

        if (rule_filter.offset == 0 and no_filter) or filter_only_user:
            params["no_rule_user"] = True

        # 开区查询rule_id 不展示无规则用户
        if rule_filter.rule_ids:
            params["no_rule_user"] = False

        params["bk_biz_id"] = self.bk_biz_id
        rules_list = DBPrivManagerApi.list_account_rules(params)
        if not rules_list["items"]:
            return {"count": 0, "results": []}
        account_rules_list = self._format_account_rules(rules_list)
        return {"count": account_rules_list["count"], "results": account_rules_list["items"]}

    def modify_account_rule(self, account_rule: AccountRuleMeta) -> Optional[Any]:
        """
        - 修改账号规则
        :param account_rule: 账号规则元信息
        """

        resp = DBPrivManagerApi.modify_account_rule(
            {
                "bk_biz_id": self.bk_biz_id,
                "operator": self.operator,
                "cluster_type": self.account_type,
                "id": account_rule.rule_id,
                "account_id": account_rule.account_id,
                "dbname": account_rule.access_db,
                "priv": account_rule.privilege,
            }
        )
        return resp

    def delete_account_rule(self, account_rule: AccountRuleMeta) -> Optional[Any]:
        """
        - 删除账号规则
        :param account_rule: 账号规则元信息
        """
        # 如果账号规则与其他地方耦合，需要进行判断
        config = TendbOpenAreaConfig.objects.filter(related_authorize__contains=[account_rule.rule_id])
        if config.exists():
            raise DBPermissionBaseException(_("当前授权规则已被开区模板{}引用，不允许删除").format(config.first().name))

        resp = DBPrivManagerApi.delete_account_rule(
            {
                "bk_biz_id": self.bk_biz_id,
                "operator": self.operator,
                "cluster_type": self.account_type,
                "id": [account_rule.rule_id],
            }
        )
        return resp

    @classmethod
    def aggregate_user_db_privileges(cls, bk_biz_id: int, account_type: AccountType) -> Dict[str, Dict[str, List]]:
        account_rules = DBPrivManagerApi.list_account_rules({"bk_biz_id": bk_biz_id, "cluster_type": account_type})[
            "items"
        ]
        # 按照user，accessdb进行聚合
        user_db__rules = defaultdict(dict)
        for account_rule in account_rules:
            account, rules = account_rule["account"], account_rule["rules"]
            user_db__rules[account["user"]] = {rule["dbname"]: rule["priv"] for rule in rules}
        return user_db__rules
