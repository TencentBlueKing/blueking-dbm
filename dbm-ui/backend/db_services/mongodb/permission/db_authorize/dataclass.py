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

from backend.db_services.dbpermission.constants import EXCEL_DIVIDER, AuthorizeExcelHeader
from backend.db_services.dbpermission.db_authorize.dataclass import AuthorizeMeta as BaseAuthorizeMeta
from backend.db_services.dbpermission.db_authorize.dataclass import ExcelAuthorizeMeta as BaseExcelAuthorizeMeta
from backend.db_services.dbpermission.db_authorize.models import AuthorizeRecord


@dataclass
class MongoDBAuthorizeMeta(BaseAuthorizeMeta):
    """授权元信息的数据模型"""

    mongo_users: List[Dict] = None  # 多个账号规则

    @classmethod
    def from_excel_data(cls, excel_data: Dict, cluster_type: str) -> "MongoDBAuthorizeMeta":
        """从权限excel数据解析为AuthorizeMeta"""
        return cls(
            user=excel_data[AuthorizeExcelHeader.USER],
            access_dbs=excel_data[AuthorizeExcelHeader.ACCESS_DBS].split(EXCEL_DIVIDER),
            target_instances=excel_data[AuthorizeExcelHeader.TARGET_INSTANCES].split(EXCEL_DIVIDER),
            cluster_type=cluster_type,
        )

    @classmethod
    def serializer_record_data(cls, record_queryset: List[AuthorizeRecord]) -> List[Dict]:
        """将授权记录进行序列化"""
        record_data_list = [
            {
                AuthorizeExcelHeader.USER: record.user,
                AuthorizeExcelHeader.TARGET_INSTANCES: record.target_instances,
                AuthorizeExcelHeader.ACCESS_DBS: record.access_dbs,
                AuthorizeExcelHeader.ERROR: record.error,
            }
            for record in record_queryset
        ]
        return record_data_list


@dataclass
class MongoDBExcelAuthorizeMeta(BaseExcelAuthorizeMeta):
    """excel授权信息的数据模型"""

    @classmethod
    def serialize_excel_data(cls, data: Dict) -> Dict:
        """将数据解析为权限excel data类的数据"""
        return {
            AuthorizeExcelHeader.USER: data["user"],
            AuthorizeExcelHeader.TARGET_INSTANCES: EXCEL_DIVIDER.join(data["target_instances"]),
            AuthorizeExcelHeader.ACCESS_DBS: EXCEL_DIVIDER.join([rule["db"] for rule in data["rule_sets"]]),
            AuthorizeExcelHeader.ERROR: data["message"],
        }
