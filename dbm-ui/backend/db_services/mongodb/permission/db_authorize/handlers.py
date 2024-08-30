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
import base64
from typing import Dict, List, Tuple

from django.utils.translation import ugettext_lazy as _

from backend.components.mysql_priv_manager.client import DBPrivManagerApi
from backend.db_services.dbpermission.constants import AccountType, AuthorizeExcelHeader
from backend.db_services.dbpermission.db_account.handlers import AccountHandler
from backend.db_services.dbpermission.db_authorize.dataclass import AuthorizeMeta, ExcelAuthorizeMeta
from backend.db_services.dbpermission.db_authorize.handlers import AuthorizeHandler
from backend.db_services.mongodb.permission.constants import AUTHORIZE_EXCEL_ERROR_TEMPLATE
from backend.db_services.mongodb.permission.db_authorize.dataclass import (
    MongoDBAuthorizeMeta,
    MongoDBExcelAuthorizeMeta,
)


class MongoDBAuthorizeHandler(AuthorizeHandler):
    """
    封装授权相关的处理操作
    """

    EXCEL_ERROR_TEMPLATE: str = AUTHORIZE_EXCEL_ERROR_TEMPLATE
    authorize_meta: AuthorizeMeta = MongoDBAuthorizeMeta
    excel_authorize_meta: ExcelAuthorizeMeta = MongoDBExcelAuthorizeMeta
    account_type: AccountType = AccountType.MONGODB

    def _pre_check_rules(
        self,
        authorize: MongoDBAuthorizeMeta,
        user_info_map: Dict = None,
        user_db__rules: Dict = None,
        user__password: Dict = None,
        **kwargs
    ) -> Tuple[bool, str, Dict]:
        """前置校验"""

        # 组装授权信息
        auth_db, username = authorize.user.split(".")
        authorize_data = {
            "cluster_ids": authorize.cluster_ids,
            "target_instances": authorize.target_instances,
            "access_dbs": authorize.access_dbs,
            "account_id": user_info_map.get(authorize.user, {}).get("id"),
            "username": username,
            "password": "",
            "auth_db": auth_db,
            "rule_sets": [],
        }

        # 校验密码是否存在
        user_password_map = kwargs.get("user_password_map", {})
        if authorize.user not in user_password_map:
            return False, _("无法查询用户{}对应的密码").format(authorize.user), authorize_data
        authorize_data["password"] = user_password_map[authorize.user]

        # 检查授权规则是否存在
        for db in authorize.access_dbs:
            if db not in user_db__rules[authorize.user]:
                return False, _("不存在{}-{}这样的规则模板").format(authorize.user, db), authorize_data
        authorize_data["rule_sets"] = [
            {"db": db, "privileges": user_db__rules[authorize.user][db].split(",")} for db in authorize.access_dbs
        ]

        # 校验集群是否存在，TODO:是否可访问
        if len(authorize.target_instances) != len(authorize.cluster_ids):
            return False, _("存在不合法的集群域名"), authorize_data

        return True, _("前置校验成功"), authorize_data

    def _get_user_rules_and_password_map(self, users: List[str]):
        """提前查询权限规则表和密码表"""
        user_db__rules = AccountHandler.aggregate_user_db_rules(self.bk_biz_id, AccountType.MONGODB)

        params = {"bk_biz_id": self.bk_biz_id, "users": users, "cluster_type": AccountType.MONGODB.value}
        user_password_data = DBPrivManagerApi.get_account_include_password(params)["items"]
        user_password_map = {d["user"]: base64.b64decode(d["psw"]).decode("utf8") for d in user_password_data}

        return user_db__rules, user_password_map

    def pre_check_excel_rules(self, excel_authorize: ExcelAuthorizeMeta, **kwargs) -> Dict:
        users = [d[AuthorizeExcelHeader.USER] for d in excel_authorize.authorize_excel_data]
        # 获取授权用户相关数据，缓存成字典减少重复请求
        user_db__rules, user_password_map = self._get_user_rules_and_password_map(users)
        user_info_map = self._get_user_info_map(self.account_type, self.bk_biz_id)
        # 获取授权检查数据
        return super().pre_check_excel_rules(
            excel_authorize,
            user_db__rules=user_db__rules,
            user_info_map=user_info_map,
            user__password=user_password_map,
            **kwargs
        )

    def multi_user_pre_check_rules(self, authorize: MongoDBAuthorizeMeta, **kwargs):
        """多个账号的前置校验，适合mongodb的授权"""
        users = [user["user"] for user in authorize.mongo_users]
        # 获取授权用户相关数据，缓存成字典减少重复请求
        user_db__rules, user_password_map = self._get_user_rules_and_password_map(users)
        user_info_map = self._get_user_info_map(self.account_type, self.bk_biz_id)
        # 获取授权检查数据
        authorize_check_result = self._multi_user_pre_check_rules(
            authorize,
            users_key="mongo_users",
            user_db__rules=user_db__rules,
            user_password_map=user_password_map,
            user_info_map=user_info_map,
            **kwargs
        )
        return authorize_check_result

    def get_online_rules(self) -> List:
        """获取现网授权记录"""
        raise NotImplementedError
