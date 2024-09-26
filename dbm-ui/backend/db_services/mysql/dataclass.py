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

from backend.constants import IP_PORT_DIVIDER, IP_PORT_RE_PATTERN
from backend.db_meta.enums.cluster_type import ClusterType


@dataclass
class ClusterFilter:
    """
    对集群的条件过滤选项，默认是精确匹配
    """

    # 后续需要其他过滤选项可继续添加
    id: int = None
    bk_biz_id: int = None
    immute_domain: str = None
    cluster_type: List[str] = None

    def __post_init__(self):
        if not self.cluster_type:
            self.cluster_type = [ClusterType.TenDBCluster, ClusterType.TenDBHA, ClusterType.TenDBSingle]

    @classmethod
    def from_dict(cls, init_data: Dict) -> "ClusterFilter":
        return cls(**init_data)

    def export_filter_conditions(self):
        filter_dict = asdict(self)
        filter_conditions: Dict = {
            filter_key: filter_dict[filter_key] for filter_key in filter_dict if filter_dict[filter_key]
        }

        # 格式化过滤条件
        if isinstance(filter_conditions["cluster_type"], list):
            filter_conditions["cluster_type__in"] = filter_conditions.pop("cluster_type")

        # 如果是实例过滤. TODO: 临时给插件支持，后续统一替换成filter_clusters接口
        if re.compile(IP_PORT_RE_PATTERN).match(filter_conditions.get("immute_domain", "")):
            ip, port = filter_conditions.pop("immute_domain").split(IP_PORT_DIVIDER)
            filter_conditions["storageinstance__machine__ip"] = ip
            filter_conditions["storageinstance__port"] = port

        return filter_conditions
