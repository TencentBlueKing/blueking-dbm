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
from typing import Dict, List, Tuple

from django.utils.translation import ugettext_lazy as _

from backend.db_meta.models import Cluster
from backend.db_services.dbpermission.constants import AccountType
from backend.db_services.dbpermission.db_account.handlers import AccountHandler
from backend.db_services.dbpermission.db_authorize.dataclass import AuthorizeMeta, ExcelAuthorizeMeta
from backend.db_services.dbpermission.db_authorize.handlers import AuthorizeHandler
from backend.db_services.sqlserver.permission.constants import AUTHORIZE_EXCEL_ERROR_TEMPLATE
from backend.db_services.sqlserver.permission.db_authorize.dataclass import (
    SQLServerDBAuthorizeMeta,
    SQLServerExcelAuthorizeMeta,
)


class SQLServerAuthorizeHandler(AuthorizeHandler):
    """
    封装授权相关的处理操作
    """

    EXCEL_ERROR_TEMPLATE: str = AUTHORIZE_EXCEL_ERROR_TEMPLATE
    authorize_meta: AuthorizeMeta = SQLServerDBAuthorizeMeta
    excel_authorize_meta: ExcelAuthorizeMeta = SQLServerExcelAuthorizeMeta
    account_type: AccountType = AccountType.SQLServer

    def _pre_check_rules(
        self, authorize: AuthorizeMeta, user_info_map: Dict = None, user_db__rules: Dict = None, **kwargs
    ) -> Tuple[bool, str, Dict]:
        """sqlserver前置检查"""

        # 组装授权信息
        account_rules = [{"bk_biz_id": self.bk_biz_id, "dbname": dbname} for dbname in authorize.access_dbs]
        authorize_data = {
            "bk_biz_id": self.bk_biz_id,
            "operator": self.operator,
            "account_id": user_info_map.get(authorize.user, {}).get("id"),
            "user": authorize.user,
            "access_dbs": authorize.access_dbs,
            "account_rules": account_rules,
            "source_ips": [],
            "target_instances": authorize.target_instances,
            "cluster_type": authorize.cluster_type,
            "cluster_ids": authorize.cluster_ids,
        }

        # 检查授权规则是否存在
        for db in authorize.access_dbs:
            if db not in user_db__rules[authorize.user]:
                return False, _("不存在{}-{}这样的规则模板").format(authorize.user, db), authorize_data

        # 校验集群是否存在，TODO: 是否校验集群是否可访问？
        exist_cluster_ids = Cluster.objects.filter(id__in=authorize.cluster_ids).values_list("id", flat=True)
        not_exist_cluster_ids = set(authorize.cluster_ids) - set(exist_cluster_ids)
        if not_exist_cluster_ids:
            return False, _("不存在集群：{}").format(not_exist_cluster_ids), authorize_data

        return True, _("前置校验成功"), authorize_data

    def pre_check_excel_rules(self, excel_authorize: ExcelAuthorizeMeta, **kwargs) -> Dict:
        """sqlserver的excel导入授权"""
        user_db__rules = AccountHandler.aggregate_user_db_rules(self.bk_biz_id, self.account_type)
        user_info_map = self._get_user_info_map(self.account_type, self.bk_biz_id)
        return super().pre_check_excel_rules(
            excel_authorize, user_info_map=user_info_map, user_db__rules=user_db__rules, **kwargs
        )

    def multi_user_pre_check_rules(self, authorize: SQLServerDBAuthorizeMeta, **kwargs):
        """多个账号的前置检查，适合sqlserver的授权"""
        user_db__rules = AccountHandler.aggregate_user_db_rules(self.bk_biz_id, self.account_type)
        user_info_map = self._get_user_info_map(self.account_type, self.bk_biz_id)
        authorize_check_result = self._multi_user_pre_check_rules(
            authorize, users_key="sqlserver_users", user_db__rules=user_db__rules, user_info_map=user_info_map
        )
        return authorize_check_result

    def get_online_rules(self) -> List:
        """获取现网授权记录"""
        raise NotImplementedError
