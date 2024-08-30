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
from backend.db_services.dbpermission.constants import DPRIV_PARAMETER_MAP, AccountType, RuleActionType
from backend.db_services.dbpermission.db_account.dataclass import (
    AccountMeta,
    AccountPrivMeta,
    AccountRuleMeta,
    AccountUserMeta,
)
from backend.db_services.dbpermission.db_account.signals import create_account_signal
from backend.db_services.dbpermission.db_authorize.models import DBRuleActionLog
from backend.db_services.mysql.open_area.models import TendbOpenAreaConfig
from backend.db_services.mysql.permission.exceptions import DBPermissionBaseException
from backend.ticket.constants import TicketStatus, TicketType
from backend.ticket.models import Ticket
from backend.utils.excel import ExcelHandler

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
        # 查询规则变更的单据，补充规则正在运行的状态
        try:
            ticket_type = getattr(TicketType, f"{self.account_type.upper()}_ACCOUNT_RULE_CHANGE")
            priv_tickets = Ticket.objects.filter(status=TicketStatus.RUNNING, ticket_type=ticket_type)
            rule__action_map = {}
            for t in priv_tickets:
                rule__action_map[t.details["rule_id"]] = {"action": t.details["action"], "ticket_id": t.id}
        except (AttributeError, Exception):
            rule__action_map = {}

        # 格式化账号规则的字段信息
        for account_rules in account_rules_list["items"]:
            account_rules["account"]["account_id"] = account_rules["account"].pop("id")

            # 检查 rules 是否为 None
            if account_rules.get("rules") is None:
                account_rules["rules"] = []

            for rule in account_rules["rules"]:
                rule["rule_id"] = rule.pop("id")
                rule["access_db"] = rule.pop("dbname")
                rule["privilege"] = rule.pop("priv")
                rule["priv_ticket"] = rule__action_map.get(rule["rule_id"], {})

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
        # DBRuleActionLog.create_log(account_rule, self.operator, action=RuleActionType.CHANGE)
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

        # 处理权限字段字符串分割为列表
        if "privs" in params:
            params["privs"] = params["privs"].split(",")

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
        DBRuleActionLog.create_log(
            account_rule.account_id, account_rule.rule_id, self.operator, action=RuleActionType.CHANGE
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
            raise DBPermissionBaseException(_("当前规则已被开区模板{}引用，不允许删除").format(config.first().config_name))

        resp = DBPrivManagerApi.delete_account_rule(
            {
                "bk_biz_id": self.bk_biz_id,
                "operator": self.operator,
                "cluster_type": self.account_type,
                "id": [account_rule.rule_id],
            }
        )
        DBRuleActionLog.create_log(
            account_rule.account_id, account_rule.rule_id, self.operator, action=RuleActionType.DELETE
        )
        return resp

    @classmethod
    def aggregate_user_db_rules(
        cls, bk_biz_id: int, account_type: AccountType, rule_key: str = "priv"
    ) -> Dict[str, Dict[str, Any]]:
        """获得user和db对应的规则对象"""
        account_rules = DBPrivManagerApi.list_account_rules({"bk_biz_id": bk_biz_id, "cluster_type": account_type})
        # 按照user，accessdb进行聚合规则
        user_db__rules = defaultdict(dict)
        for account_rule in account_rules["items"]:
            account, rules = account_rule["account"], account_rule["rules"]
            user_db__rules[account["user"]] = {rule["dbname"]: rule[rule_key] if rule_key else rule for rule in rules}
        return user_db__rules

    def paginate_match_ips(self, data, privs_format, offset, limit):
        # 收集所有的 match_ips，保留原数据的引用
        if privs_format == "privs_for_ip":
            all_match_ips = [
                (ip, dbs, domain, user, match_ip)
                for ip in data[privs_format]
                for dbs in ip["dbs"]
                for domain in dbs["domains"]
                for user in domain["users"]
                for match_ip in user["match_ips"]
            ]
        elif privs_format == "privs_for_cluster":
            all_match_ips = [
                (cluster, user, match_ip)
                for cluster in data[privs_format]
                for user in cluster["users"]
                for match_ip in user["match_ips"]
            ]

        # 获取分页的 match_ips
        paginated_match_ips = all_match_ips[offset : offset + limit]

        # 创建新的数据结构来存储分页后的结果
        paginated_data = {privs_format: []}

        if privs_format == "privs_for_ip":
            # 用于存储已经处理过的 IP, dbs, domain 和 user 的引用
            ip_dbs_domain_user_map = {}

            for ip, dbs, domain, user, match_ip in paginated_match_ips:
                # 查找或创建新的 IP 条目
                if ip["ip"] not in ip_dbs_domain_user_map:
                    new_ip = {"ip": ip["ip"], "dbs": []}
                    paginated_data[privs_format].append(new_ip)
                    ip_dbs_domain_user_map[ip["ip"]] = {"ip": new_ip, "dbs": {}}
                else:
                    new_ip = ip_dbs_domain_user_map[ip["ip"]]["ip"]

                # 查找或创建新的 dbs 条目
                dbs_map = ip_dbs_domain_user_map[ip["ip"]]["dbs"]
                if dbs["db"] not in dbs_map:
                    new_dbs = {"db": dbs["db"], "domains": []}
                    new_ip["dbs"].append(new_dbs)
                    dbs_map[dbs["db"]] = {"dbs": new_dbs, "domains": {}}
                else:
                    new_dbs = dbs_map[dbs["db"]]["dbs"]

                # 查找或创建新的 domain 条目
                domain_map = dbs_map[dbs["db"]]["domains"]
                if domain["immute_domain"] not in domain_map:
                    new_domain = {"immute_domain": domain["immute_domain"], "users": []}
                    new_dbs["domains"].append(new_domain)
                    domain_map[domain["immute_domain"]] = {"domains": new_domain, "users": {}}
                else:
                    new_domain = domain_map[domain["immute_domain"]]["domains"]

                # 查找或创建新的用户条目
                user_map = domain_map[domain["immute_domain"]]["users"]
                if user["user"] not in user_map:
                    new_user = {"user": user["user"], "match_ips": []}
                    new_domain["users"].append(new_user)
                    user_map[user["user"]] = new_user
                else:
                    new_user = user_map[user["user"]]

                # 添加匹配的 match_ip
                new_user["match_ips"].append(match_ip)

        elif privs_format == "privs_for_cluster":
            # 用于存储已经处理过的集群和用户的引用
            cluster_user_map = {}

            for cluster, user, match_ip in paginated_match_ips:
                # 查找或创建新的集群条目
                if cluster["immute_domain"] not in cluster_user_map:
                    new_cluster = {"immute_domain": cluster["immute_domain"], "users": []}
                    paginated_data[privs_format].append(new_cluster)
                    cluster_user_map[cluster["immute_domain"]] = {"cluster": new_cluster, "users": {}}
                else:
                    new_cluster = cluster_user_map[cluster["immute_domain"]]["cluster"]

                # 查找或创建新的用户条目
                user_map = cluster_user_map[cluster["immute_domain"]]["users"]
                if user["user"] not in user_map:
                    new_user = {"user": user["user"], "match_ips": []}
                    new_cluster["users"].append(new_user)
                    user_map[user["user"]] = new_user
                else:
                    new_user = user_map[user["user"]]

                # 添加匹配的 match_ip
                new_user["match_ips"].append(match_ip)

        # 更新原数据
        data[privs_format] = paginated_data[privs_format]

        # 返回分页数据以及总 match_ips 的数量
        return data, len(all_match_ips)

    def get_account_privs(self, priv_filter: AccountPrivMeta) -> Dict:
        """获取权限信息"""
        # 过滤字典为None的键值对
        priv_meta = {k: v for k, v in priv_filter.to_dict().items() if v is not None}
        priv_meta["bk_biz_id"] = self.bk_biz_id
        priv_meta["format"] = priv_meta.pop("format_type")
        offset = priv_meta.pop("offset")
        limit = priv_meta.pop("limit")
        rules_list = DBPrivManagerApi.get_priv(priv_meta)
        privs_format = "privs_for_ip" if priv_meta["format"] == "ip" else "privs_for_cluster"
        if not rules_list[privs_format]:
            return {"match_ips_count": 0, "results": rules_list}
        # 分页
        paginated_data, total_match_ips_count = self.paginate_match_ips(rules_list, privs_format, offset, limit)
        paginated_data.pop("download")
        return {"match_ips_count": total_match_ips_count, "results": paginated_data}

    def get_download_privs(self, priv_filter: AccountPrivMeta) -> Dict:
        """获取权限信息"""
        # 过滤字典为None的键值对
        priv_meta = {k: v for k, v in priv_filter.to_dict().items() if v is not None}
        priv_meta["bk_biz_id"] = self.bk_biz_id
        priv_meta["format"] = priv_meta.pop("format_type")
        rules_list = DBPrivManagerApi.get_priv(priv_meta)

        headers = [_("源客户端IP"), _("集群域名"), _("账号"), _("匹配中的访问源"), _("匹配中的DB"), _("权限")]
        excel_name = "privs.xlsx"
        privs_list = []
        for data_dict in rules_list.get("download", []):
            # 提取公共信息
            base_info = {
                "ip": data_dict.get("ip"),
                "immute_domain": data_dict.get("immute_domain"),
                "user": data_dict.get("user"),
                "match_ip": data_dict.get("match_ip"),
            }
            # 遍历每一个 priv
            for priv in data_dict.get("privs", []):
                privs_dict = {
                    **base_info,
                    "match_db": priv.get("match_db"),
                    "priv": priv.get("priv"),
                }
                privs_list.append(privs_dict)

        wb = ExcelHandler.serialize(privs_list, headers=headers, match_header=False)
        return ExcelHandler.response(wb, excel_name)

    def get_account_users(self, account_users: AccountUserMeta):
        """获取认证用户列表"""
        user_meta = {
            "ips": account_users.ips,
            "immute_domains": account_users.immute_domains,
            "cluster_type": account_users.cluster_type,
        }
        user_list = DBPrivManagerApi.get_user_list(user_meta)
        if not user_list["items"]:
            return {"count": 0, "results": []}

        return {"count": user_list["count"], "results": user_list["items"]}
