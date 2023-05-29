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
from dataclasses import asdict, dataclass
from typing import Dict, Union

from backend.db_services.mysql.permission.constants import AccountType


@dataclass
class AccountMeta:
    """账号元信息的数据模型"""

    account_id: int = None
    user: str = None
    password: str = None
    account_type: str = AccountType.MYSQL.value

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, init_data: Dict) -> "AccountMeta":
        return cls(**init_data)


@dataclass
class AccountRuleMeta(AccountMeta):
    """账号规则元信息的数据模型"""

    rule_id: int = None
    privilege: Dict[str, Union[list, str]] = None
    access_db: Union[list, str] = None

    # 用于过滤筛选的准入db列表
    access_dbs: list = None

    def __post_init__(self):
        if not isinstance(self.privilege, dict):
            return

        # 更新账号权限参数
        for rule_type in self.privilege:
            if isinstance(self.privilege[rule_type], list):
                self.privilege[rule_type] = ",".join(self.privilege[rule_type])

        self.privilege["global"] = self.privilege.pop("glob")
