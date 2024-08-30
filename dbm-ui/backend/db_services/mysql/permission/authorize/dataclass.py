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

from dataclasses import dataclass
from typing import Dict

from backend.db_services.dbpermission.db_authorize.dataclass import AuthorizeMeta as BaseAuthorizeMeta
from backend.db_services.dbpermission.db_authorize.dataclass import ExcelAuthorizeMeta as BaseExcelAuthorizeMeta


@dataclass
class MySQLAuthorizeMeta(BaseAuthorizeMeta):
    """授权元信息的数据模型"""

    pass


@dataclass
class MySQLExcelAuthorizeMeta(BaseExcelAuthorizeMeta):
    """excel授权信息的数据模型"""

    pass


@dataclass
class HostInAuthorizeFilterMeta:
    """查询主机在授权信息的过滤数据模型"""

    ticket_id: int = None
    keyword: str = None

    @classmethod
    def from_dict(cls, init_data: Dict) -> "HostInAuthorizeFilterMeta":
        return cls(**init_data)
