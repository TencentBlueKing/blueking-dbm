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
import math
from typing import Any, Dict, List

from django.forms import model_to_dict

from backend.db_meta.models import Spec


class ClusterSpecFilter(object):
    """集群规格的过滤器"""

    def __init__(self, capacity, future_capacity, qps, spec_cluster_type, spec_machine_type):
        self.capacity: int = capacity
        self.future_capacity: int = future_capacity
        self.qps: Dict = qps
        self.specs: List[Dict[str, Any]] = [
            {**model_to_dict(spec), "capacity": spec.capacity}
            for spec in Spec.objects.filter(spec_machine_type=spec_machine_type, spec_cluster_type=spec_cluster_type)
        ]

    def calc_machine_pair(self):
        """计算每种规格所需的机器组数和集群总容量: 目标容量 / 规格容量"""
        for spec in self.specs:
            spec["machine_pair"] = math.ceil(self.capacity / spec["capacity"])
            spec["cluster_capacity"] = spec["machine_pair"] * spec["capacity"]

    def calc_cluster_shard_num(self):
        """计算每种规格的分片数, 根据不同的集群计算方式也不同"""
        raise NotImplementedError()

    def qps_filter(self):
        """根据qps进行筛选: 剔除掉与用户qps没有交集的规格"""
        valid_specs: List[Dict[str, Any]] = []
        for spec in self.specs:
            qps_range = {
                "min": spec["machine_pair"] * spec["qps"]["min"],
                "max": spec["machine_pair"] * spec["qps"]["max"],
            }
            # 如果当前规格的qps范围与用户的qps范围没有交集，则过滤
            if qps_range["min"] > self.qps["max"] or qps_range["max"] < self.qps["min"]:
                continue

            valid_specs.append(spec)

        self.specs = valid_specs

    def custom_filter(self):
        """自定义过滤规则"""
        pass

    def get_target_specs(self):
        self.calc_machine_pair()
        self.calc_cluster_shard_num()
        self.qps_filter()
        self.custom_filter()
        return self.specs


class TenDBClusterSpecFilter(ClusterSpecFilter):
    """TendbCluster集群规格的过滤器"""

    def calc_cluster_shard_num(self):
        for spec in self.specs:
            spec["cluster_shard_num"] = math.ceil(self.future_capacity / spec["capacity"])


class RedisSpecFilter(ClusterSpecFilter):
    """Redis规格过滤器基类"""

    # 建议规格数，超出将淘汰末尾规格
    RECOMMEND_SPEC_NUM = 4
    # 淘汰规格比例
    DISUSE_SPEC_RATIO = 0.5
    # 按照机器组数正向/逆向排序
    MACHINE_PAIR_SORT = False

    def custom_filter(self):
        """对规格方案进行排序，如果存在大于4个方案，则按比例淘汰末尾规格方案"""
        self.specs.sort(key=lambda x: x["machine_pair"], reverse=self.MACHINE_PAIR_SORT)
        if len(self.specs) > self.RECOMMEND_SPEC_NUM:
            self.specs = self.specs[: -int(len(self.specs) * self.DISUSE_SPEC_RATIO)]


class TendisPlusSpecFilter(RedisSpecFilter):
    """TendisPlus集群规格过滤器"""

    # 最佳容量管理大小 300G
    OPTIMAL_MANAGE_CAPACITY = 300

    def qps_filter(self):
        # TendisPlus集群不需要qps过滤
        pass

    def calc_machine_pair(self):
        """计算每种规格所需的机器组数，TendisPlus至少需要三组"""
        for spec in self.specs:
            spec["machine_pair"] = max(math.ceil(self.capacity / spec["capacity"]), 3)
            spec["cluster_capacity"] = spec["machine_pair"] * spec["capacity"]

    def calc_cluster_shard_num(self):
        for spec in self.specs:
            spec["cluster_shard_num"] = max(3, math.ceil(self.capacity / self.OPTIMAL_MANAGE_CAPACITY))

    def custom_filter(self):
        """
        TendisPlus自定义过滤规则：至少需要三组机器，保留最近接建设容量大于目标容量的规格方案
        """
        exceed_target_capacity_specs: List[Dict[str, Any]] = []
        in_target_capacity_specs: List[Dict[str, Any]] = []
        for spec in self.specs:
            # 首先筛选出建设容量超出目标容量的规格
            if spec["machine_pair"] * spec["capacity"] > self.capacity:
                exceed_target_capacity_specs.append(spec)
            else:
                in_target_capacity_specs.append(spec)

        # 如果存在多个建设容量>目标容量的规格，则取最接近目标容量的规格
        if exceed_target_capacity_specs:
            in_target_capacity_specs.append(
                sorted(exceed_target_capacity_specs, key=lambda x: x["machine_pair"] * spec["capacity"])[0]
            )

        # 方案淘汰
        self.specs = in_target_capacity_specs
        super().custom_filter()


class TendisSSDSpecFilter(RedisSpecFilter):
    """TendisSSD集群规格过滤器"""

    # 单实例最大容量 50G
    SINGLE_MAX_CAPACITY = 50
    MACHINE_PAIR_SORT = True

    def calc_cluster_shard_num(self):
        for spec in self.specs:
            # 计算单机分片数，容量/50-取整为最接近的偶数
            single_machine_shard_num = int(spec["capacity"] / self.SINGLE_MAX_CAPACITY)
            single_machine_shard_num = single_machine_shard_num + (single_machine_shard_num & 1)
            spec["cluster_shard_num"] = single_machine_shard_num * spec["machine_pair"]

    def custom_filter(self):
        super().custom_filter()


class TendisCacheSpecFilter(RedisSpecFilter):
    """TendisCache集群规格过滤器"""

    def calc_cluster_shard_num(self):
        for spec in self.specs:
            # 计算单机分片数，CPU去中间数的偶数
            single_machine_shard_num = int((spec["cpu"]["min"] + spec["cpu"]["max"]) / 2)
            single_machine_shard_num = single_machine_shard_num + (single_machine_shard_num & 1)
            spec["cluster_shard_num"] = single_machine_shard_num * spec["machine_pair"]

    def custom_filter(self):
        super().custom_filter()
