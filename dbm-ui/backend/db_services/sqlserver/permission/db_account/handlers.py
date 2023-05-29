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

from backend.components import DBPrivManagerApi
from backend.db_services.dbpermission.db_account.dataclass import AccountMeta
from backend.db_services.dbpermission.db_account.handlers import AccountHandler
from backend.flow.utils.sqlserver.sqlserver_db_function import create_sqlserver_login_sid

logger = logging.getLogger("root")


class SQLServerDBAccountHandler(AccountHandler):
    """
    封装账号相关的处理操作
    """

    def create_account(self, account: AccountMeta) -> Optional[Any]:
        """
        - 新建一个账号, sqlserver需要sid
        @param account: 账号元信息
        """
        resp = DBPrivManagerApi.create_account(
            {
                "cluster_type": self.account_type,
                "bk_biz_id": self.bk_biz_id,
                "operator": self.operator,
                "user": account.user,
                "psw": account.password,
                "sid": create_sqlserver_login_sid(),
            }
        )
        return resp
