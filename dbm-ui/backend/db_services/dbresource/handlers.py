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

from backend.components.dbresource.client import DBResourceApi
from backend.db_meta.models import Spec


class ClusterSpecFilter(object):
    """集群规格的过滤器"""

    def __init__(self, capacity, future_capacity, qps, spec_cluster_type, spec_machine_type, shard_num=0):
        # 用户的当前容量，期望容量，期望qps范围和分片数(可选)
        self.capacity: int = capacity
        self.future_capacity: int = future_capacity
        self.qps: Dict = qps
        self.filter_shard_num = shard_num
        # 当前集群的筛选规格
        self.specs: List[Dict[str, Any]] = [
            {**model_to_dict(spec), "capacity": spec.capacity}
            for spec in Spec.objects.filter(spec_machine_type=spec_machine_type, spec_cluster_type=spec_cluster_type)
        ]

    def calc_machine_pair(self):
        """计算每种规格所需的机器组数和集群总容量: 目标容量 / 规格容量"""
        for spec in self.specs:
            spec["machine_pair"] = math.ceil(self.capacity / spec["capacity"])
            # 集群容量：机器组数 * 规格容量；集群qps：机器组数 * 规格qps的min
            spec["cluster_capacity"] = spec["machine_pair"] * spec["capacity"]
            spec["cluster_qps"] = spec["machine_pair"] * spec["qps"]["min"]

    def calc_cluster_shard_num(self):
        """计算每种规格的分片数, 根据不同的集群计算方式也不同"""
        raise NotImplementedError()

    def _qps_check(self, user_qps_range, spec_qps_range):
        """默认判断规则：当前qps与用户需要存在交集"""
        if user_qps_range["min"] > spec_qps_range["max"] or user_qps_range["max"] < spec_qps_range["min"]:
            return False

        return True

    def system_filter(self):
        """系统自带的过滤：qps和分片数"""
        valid_specs: List[Dict[str, Any]] = []
        for spec in self.specs:
            qps_range = {
                "min": spec["machine_pair"] * spec["qps"]["min"],
                "max": spec["machine_pair"] * spec["qps"]["max"],
            }
            if not self._qps_check(self.qps, qps_range):
                continue

            if self.filter_shard_num and spec["cluster_shard_num"] != self.filter_shard_num:
                continue

            valid_specs.append(spec)

        self.specs = valid_specs

    def custom_filter(self):
        """自定义过滤规则"""
        pass

    def get_target_specs(self):
        self.calc_machine_pair()
        self.calc_cluster_shard_num()
        self.system_filter()
        self.custom_filter()
        return self.specs


class TenDBClusterSpecFilter(ClusterSpecFilter):
    """TendbCluster集群规格的过滤器"""

    def calc_cluster_shard_num(self):
        for spec in self.specs:
            # 一定要保证集群总分片数是机器组数的整数倍，因此单机分片数要上取整
            cluster_shard_num = math.ceil(self.future_capacity / spec["capacity"])
            single_machine_shard_num = math.ceil(cluster_shard_num / spec["machine_pair"])
            spec["cluster_shard_num"] = single_machine_shard_num * spec["machine_pair"]


class RedisSpecFilter(ClusterSpecFilter):
    """Redis规格过滤器基类"""

    # 建议规格数，超出将淘汰末尾规格
    RECOMMEND_SPEC_NUM = 4
    # 淘汰规格比例
    DISUSE_SPEC_RATIO = 0.5
    # 按照机器组数正向/逆向排序
    MACHINE_PAIR_SORT = False

    def _qps_check(self, user_qps_range, spec_qps_range):
        # redis可以接受规格qps过大，不接受规格qps小于用户的最小值
        if user_qps_range["min"] > spec_qps_range["max"]:
            return False

        return True

    def custom_filter(self):
        """对规格方案进行排序，如果存在大于4个方案，则按比例淘汰末尾规格方案"""
        self.specs.sort(key=lambda x: x["machine_pair"], reverse=self.MACHINE_PAIR_SORT)
        if len(self.specs) > self.RECOMMEND_SPEC_NUM:
            self.specs = self.specs[: -int(len(self.specs) * self.DISUSE_SPEC_RATIO)]

    def filter_too_large_building_capacity(self):
        """过滤掉过大的建设容量，当建设容量大于目标容量时，默认只保留最小的一个"""
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
                sorted(exceed_target_capacity_specs, key=lambda x: x["machine_pair"] * x["capacity"])[0]
            )

        self.specs = in_target_capacity_specs


class TendisPlusSpecFilter(RedisSpecFilter):
    """TendisPlus集群规格过滤器"""

    # 最佳容量管理大小 300G
    OPTIMAL_MANAGE_CAPACITY = 300

    def _qps_check(self, user_qps_range, spec_qps_range):
        # TendisPlus集群不需要qps过滤
        return True

    def calc_machine_pair(self):
        """计算每种规格所需的机器组数，TendisPlus至少需要三组"""
        for spec in self.specs:
            spec["machine_pair"] = max(math.ceil(self.capacity / spec["capacity"]), 3)
            spec["cluster_capacity"] = spec["machine_pair"] * spec["capacity"]

    def calc_cluster_shard_num(self):
        for spec in self.specs:
            spec["cluster_shard_num"] = max(3, math.ceil(self.capacity / self.OPTIMAL_MANAGE_CAPACITY))
            # 将分片数上取整为机器组数的倍数
            spec["cluster_shard_num"] = (
                math.ceil(spec["cluster_shard_num"] / spec["machine_pair"]) * spec["machine_pair"]
            )

    def custom_filter(self):
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
            single_machine_shard_num = max(single_machine_shard_num + (single_machine_shard_num & 1), 2)
            spec["cluster_shard_num"] = single_machine_shard_num * spec["machine_pair"]

    def custom_filter(self):
        super().custom_filter()


class TendisCacheSpecFilter(RedisSpecFilter):
    """TendisCache集群规格过滤器"""

    def calc_cluster_shard_num(self):
        for spec in self.specs:
            # 计算单机分片数，CPU去中间数的偶数
            single_machine_shard_num = int((spec["cpu"]["min"] + spec["cpu"]["max"]) / 2)
            single_machine_shard_num = max(single_machine_shard_num + (single_machine_shard_num & 1), 2)
            spec["cluster_shard_num"] = single_machine_shard_num * spec["machine_pair"]

    def custom_filter(self):
        super().filter_too_large_building_capacity()
        super().custom_filter()


class ResourceHandler(object):
    """资源池接口的处理函数"""

    @classmethod
    def spec_resource_count(cls, bk_biz_id: int, resource_type: str, bk_cloud_id: int, spec_ids: List[int]):
        # 构造申请参数
        spec_count_details = [
            spec.get_apply_params_detail(group_mark=str(spec.spec_id), count=0, bk_cloud_id=bk_cloud_id)
            for spec in Spec.objects.filter(spec_id__in=spec_ids)
        ]
        spec_count_params = {
            "bk_biz_id": bk_biz_id,
            "resource_type": resource_type,
            "bk_cloud_id": bk_cloud_id,
            "details": spec_count_details,
        }
        return DBResourceApi.apply_count(params=spec_count_params)
