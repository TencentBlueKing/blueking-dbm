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
from backend.db_meta.enums import ClusterEntryType
from backend.db_meta.models import ClusterEntry
from backend.db_services.dbpermission.constants import (
    AUTHORIZE_KEY__EXCEL_FIELD_MAP,
    EXCEL_DIVIDER,
    AuthorizeExcelHeader,
)
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.ticket.constants import FlowType
from backend.ticket.models import Flow


@dataclass
class AuthorizeMeta:
    """授权元信息的数据模型"""

    user: str = None
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
            ens = ClusterEntry.objects.filter(cluster_entry_type=ClusterEntryType.DNS, entry__in=self.target_instances)
            self.cluster_ids = list(ens.values_list("cluster_id", flat=True))

    @classmethod
    def from_dict(cls, init_data: Dict) -> "AuthorizeMeta":
        return cls(**init_data)

    @classmethod
    def from_excel_data(cls, excel_data: Dict, cluster_type: str) -> "AuthorizeMeta":
        """从权限excel数据解析为AuthorizeMeta, 每个集群类型自己实现"""
        return cls(
            user=excel_data[AuthorizeExcelHeader.USER],
            access_dbs=excel_data[AuthorizeExcelHeader.ACCESS_DBS].split(EXCEL_DIVIDER),
            target_instances=excel_data[AuthorizeExcelHeader.TARGET_INSTANCES].split(EXCEL_DIVIDER),
            source_ips=ExcelAuthorizeMeta.format_ip(excel_data.get(AuthorizeExcelHeader.SOURCE_IPS)),
            cluster_type=cluster_type,
        )

    @classmethod
    def serializer_record_data(cls, ticket_id: int) -> List[Dict]:
        """将授权记录进行序列化"""

        def __format(_data):
            if isinstance(_data, (list, dict)):
                return "\n".join(_data)
            return _data

        # 目前授权只有：授权单据和开区单据，仅一个inner flow，可以直接取first
        flow = Flow.objects.filter(ticket_id=ticket_id, flow_type=FlowType.INNER_FLOW).first()
        authorize_results = BaseService.get_flow_output(flow)["data"].get("authorize_results", [])
        field_map = AUTHORIZE_KEY__EXCEL_FIELD_MAP

        record_data_list = []
        for index, info in enumerate(flow.details["ticket_data"]["rules_set"]):
            data = {field_map[field]: __format(value) for field, value in info.items() if field in field_map}
            data.update({AuthorizeExcelHeader.ERROR: authorize_results[index]})
            record_data_list.append(data)

        return record_data_list


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
        if not ips:
            return []
        # 编译捕获ip:port的正则表达式(注意用?:取消分组)
        ip_pattern = re.compile(IP_RE_PATTERN)
        return ip_pattern.findall(ips)

    @classmethod
    def serialize_excel_data(cls, data: Dict) -> Dict:
        """将数据解析为权限excel data类的数据, 每个集群类型自己实现"""
        excel_data = {
            AuthorizeExcelHeader.USER: data["user"],
            AuthorizeExcelHeader.TARGET_INSTANCES: EXCEL_DIVIDER.join(data["target_instances"]),
            AuthorizeExcelHeader.ACCESS_DBS: EXCEL_DIVIDER.join([rule["dbname"] for rule in data["account_rules"]]),
            AuthorizeExcelHeader.SOURCE_IPS: EXCEL_DIVIDER.join(cls.format_ip(str(data.get("source_ips")))),
            AuthorizeExcelHeader.ERROR: data["message"],
        }
        return excel_data
