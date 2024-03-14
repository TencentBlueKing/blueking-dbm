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
import operator
import re
from dataclasses import asdict, dataclass
from functools import reduce
from typing import Dict, List

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db.models import Q

from backend.constants import IP_RE_PATTERN
from backend.db_meta.models import Cluster
from backend.db_services.mysql.permission.constants import CloneType


@dataclass
class CloneMeta:
    """权限克隆元数据基类"""

    ticket_id: int = None
    clone_uid: str = None

    clone_type: str = None
    clone_list: List = None
    clone_file: InMemoryUploadedFile = None

    def __post_init__(self):
        if not self.clone_list:
            return

        # 客户端克隆：将所有的target ip变为列表格式
        if self.clone_type == CloneType.CLIENT.value:
            ip_pattern = re.compile(IP_RE_PATTERN)
            for clone_data in self.clone_list:
                ip_match = ip_pattern.findall(clone_data["target"])
                clone_data["target"] = list(ip_match)
        # 实例克隆：补充集群ID用作鉴权
        else:
            domain_filters = reduce(
                operator.or_, [Q(immute_domain=data["cluster_domain"]) for data in self.clone_list]
            )
            domain__cluster = {cluster.immute_domain: cluster for cluster in Cluster.objects.filter(domain_filters)}
            for clone_data in self.clone_list:
                clone_data["cluster_id"] = domain__cluster[clone_data["cluster_domain"]].id

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, init_data: Dict) -> "CloneMeta":
        return cls(**init_data)
