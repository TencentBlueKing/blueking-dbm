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
from typing import Dict, List, Union

from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models import ProxyInstance, StorageInstance


@dataclass
class DBInstance:
    bk_host_id: int
    ip: str
    bk_cloud_id: int
    port: int
    spec_config: dict

    @classmethod
    def from_inst_obj(cls, inst_obj: Union[Dict, StorageInstance, ProxyInstance]) -> "DBInstance":
        if isinstance(inst_obj, Dict):
            return cls(
                inst_obj["bk_host_id"],
                inst_obj["ip"],
                inst_obj["bk_cloud_id"],
                inst_obj["port"],
                inst_obj["spec_config"],
            )

        return cls(
            inst_obj.machine.bk_host_id,
            inst_obj.machine.ip,
            inst_obj.machine.bk_cloud_id,
            inst_obj.port,
            inst_obj.machine.spec_config,
        )

    def __str__(self):
        return f"{self.bk_host_id}-{self.bk_cloud_id}-{self.ip}-{self.port}"

    def as_dict(self):
        return asdict(self)


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

        return filter_conditions
