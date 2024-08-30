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
from typing import Dict, List

from backend.db_services.dbpermission.constants import AuthorizeExcelHeader
from backend.db_services.dbpermission.db_authorize.dataclass import AuthorizeMeta as BaseAuthorizeMeta
from backend.db_services.dbpermission.db_authorize.dataclass import ExcelAuthorizeMeta as BaseExcelAuthorizeMeta


@dataclass
class MongoDBAuthorizeMeta(BaseAuthorizeMeta):
    """授权元信息的数据模型"""

    mongo_users: List[Dict] = None  # 多个账号规则


@dataclass
class MongoDBExcelAuthorizeMeta(BaseExcelAuthorizeMeta):
    """excel授权信息的数据模型"""

    @classmethod
    def serialize_excel_data(cls, data: Dict) -> Dict:
        excel_data = BaseExcelAuthorizeMeta.serialize_excel_data(data)
        excel_data.pop(AuthorizeExcelHeader.SOURCE_IPS)
        return excel_data
