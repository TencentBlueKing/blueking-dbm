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

import re
from dataclasses import asdict, dataclass
from typing import Dict, List

from django.core.files.uploadedfile import InMemoryUploadedFile

from backend.constants import IP_RE_PATTERN
from backend.db_meta.models.cluster import Cluster
from backend.db_services.mysql.permission.constants import EXCEL_DIVIDER, AuthorizeExcelHeader


@dataclass
class AuthorizeMeta:
    """授权元信息的数据模型"""

    user: str
    access_dbs: list = None
    source_ips: list = None
    target_instances: list = None
    cluster_ids: list = None
    cluster_type: str = None

    def to_dict(self):
        return asdict(self)

    def __post_init__(self):
        # 获取操作的集群id，方便后续在ticket中记录
        if self.target_instances:
            self.cluster_ids = [
                cluster.id for cluster in Cluster.objects.filter(immute_domain__in=self.target_instances)
            ]

    @classmethod
    def from_dict(cls, init_data: Dict) -> "AuthorizeMeta":
        return cls(**init_data)

    @classmethod
    def from_excel_data(cls, excel_data: Dict, cluster_type: str) -> "AuthorizeMeta":
        """从权限excel数据解析为AuthorizeMeta"""
        return cls(
            user=excel_data[AuthorizeExcelHeader.USER],
            access_dbs=excel_data[AuthorizeExcelHeader.ACCESS_DBS].split(EXCEL_DIVIDER),
            source_ips=ExcelAuthorizeMeta.format_ip(excel_data[AuthorizeExcelHeader.SOURCE_IPS]),
            target_instances=excel_data[AuthorizeExcelHeader.TARGET_INSTANCES].split(EXCEL_DIVIDER),
            cluster_type=cluster_type,
        )


@dataclass
class ExcelAuthorizeMeta:
    """excel授权信息的数据模型"""

    authorize_file: InMemoryUploadedFile = None
    authorize_excel_data: List[Dict] = None
    cluster_type: str = None

    authorize_uid: str = None
    ticket_id: int = None

    @classmethod
    def from_dict(cls, init_data: Dict) -> "ExcelAuthorizeMeta":
        return cls(**init_data)

    @classmethod
    def format_ip(cls, ips: str):
        # 编译捕获ip:port的正则表达式(注意用?:取消分组)
        ip_pattern = re.compile(IP_RE_PATTERN)
        return ip_pattern.findall(ips)

    @classmethod
    def serialize_excel_data(cls, data: Dict) -> Dict:
        """将数据解析为权限excel data类的数据"""
        return {
            AuthorizeExcelHeader.USER: data["user"],
            AuthorizeExcelHeader.SOURCE_IPS: EXCEL_DIVIDER.join(data["source_ips"]),
            AuthorizeExcelHeader.TARGET_INSTANCES: EXCEL_DIVIDER.join(data["target_instances"]),
            AuthorizeExcelHeader.ACCESS_DBS: EXCEL_DIVIDER.join([rule["dbname"] for rule in data["account_rules"]]),
            AuthorizeExcelHeader.ERROR: data["message"],
        }


@dataclass
class HostInAuthorizeFilterMeta:
    """查询主机在授权信息的过滤数据模型"""

    ticket_id: int = None
    keyword: str = None

    @classmethod
    def from_dict(cls, init_data: Dict) -> "HostInAuthorizeFilterMeta":
        return cls(**init_data)
