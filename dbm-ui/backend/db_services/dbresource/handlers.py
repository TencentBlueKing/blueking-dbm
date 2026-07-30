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
import itertools
import logging
import math
import time
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List

from celery import shared_task
from django.db import transaction
from django.utils.translation import gettext as _

from backend import env
from backend.components import CCApi
from backend.components.dbresource.client import DBResourceApi
from backend.components.gse.client import GseApi
from backend.configuration.constants import COST_ESTIMATE_TEMPLATE, DBType, SystemSettingsEnum
from backend.configuration.models import SystemSettings
from backend.db_dirty.constants import MachineEventType, PoolType
from backend.db_meta.enums.comm import SystemTagEnum
from backend.db_meta.enums.spec import SpecClusterType, SpecMachineType
from backend.db_meta.models import AppCache, Machine, Spec, Tag
from backend.db_services.dbresource.exceptions import ResourceReturnException, SpecOperateException
from backend.db_services.dbresource.models import ResourceReplenishRecord
from backend.db_services.ipchooser.constants import ModeType
from backend.db_services.ipchooser.handlers.topo_handler import TopoHandler
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.db_services.ipchooser.types import ScopeList
from backend.db_services.taskflow.handlers import TaskFlowHandler
from backend.flow.consts import StateType
from backend.flow.utils.cc_manage import CcManage
from backend.ticket.constants import FlowErrCode, TicketFlowStatus, TicketStatus, TicketType
from backend.ticket.models import Flow, Ticket, Todo
from backend.utils.cache import func_cache_decorator
from backend.utils.excel import ExcelHandler

logger = logging.getLogger("root")


class ClusterSpecFilter(object):
    """集群规格的过滤器"""

    def __init__(
        self, capacity, future_capacity, spec_cluster_type, spec_machine_type, qps=None, shard_num=0, old_spec_id=0
    ):
        # 用户的当前容量，期望容量，期望qps范围和分片数(可选)
        self.capacity: int = capacity
        self.future_capacity: int = future_capacity
        self.qps: Dict = qps
        self.filter_shard_num = shard_num
        # 当前集群的筛选规格
        self.specs: List[Dict[str, Any]] = [
            {
                **spec.to_dict(),
                "capacity": spec.capacity,
            }
            for spec in Spec.objects.filter(
                spec_machine_type=spec_machine_type, spec_cluster_type=spec_cluster_type, enable=True
            )
        ]

    def calc_machine_pair(self):
        """计算每种规格所需的机器组数和集群总容量: 目标容量 / 规格容量"""
        for spec in self.specs:
            spec["machine_pair"] = math.ceil(self.capacity / spec["capacity"])
            # 集群容量：机器组数 * 规格容量；集群qps：机器组数 * 规格qps的min
            spec["cluster_capacity"] = spec["machine_pair"] * spec["capacity"]
            if self.qps:
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
            # 如果当前分片数不等于过滤分片数，忽略
            if self.filter_shard_num and spec["cluster_shard_num"] != self.filter_shard_num:
                continue
            # 如果qps范围没有存在交集，忽略
            if self.qps:
                qps_range = {
                    "min": spec["machine_pair"] * spec["qps"]["min"],
                    "max": spec["machine_pair"] * spec["qps"]["max"],
                }
                if not self._qps_check(self.qps, qps_range):
                    continue

            valid_specs.append(spec)

        self.specs = valid_specs

    def custom_filter(self):
        """自定义过滤规则"""
        pass

    def get_target_specs(self):
        if not self.specs:
            return []

        self.calc_machine_pair()
        self.calc_cluster_shard_num()
        self.system_filter()
        self.custom_filter()

        return self.specs


class TenDBClusterSpecFilter(ClusterSpecFilter):
    """TendbCluster集群规格的过滤器"""

    def __init__(self, capacity, future_capacity, spec_cluster_type, spec_machine_type, qps=None, shard_num=0):
        super().__init__(capacity, future_capacity, spec_cluster_type, spec_machine_type, qps, shard_num)
        # 如果不存在qps，则过滤
        valid_specs = [spec for spec in self.specs if spec["qps"]]
        self.specs = valid_specs

    def calc_cluster_shard_num(self):
        for spec in self.specs:
            # 一定要保证集群总分片数是机器组数的整数倍，因此单机分片数要上取整
            cluster_shard_num = math.ceil(self.future_capacity / spec["capacity"])
            single_machine_shard_num = math.ceil(cluster_shard_num / spec["machine_pair"])
            spec["cluster_shard_num"] = single_machine_shard_num * spec["machine_pair"]

    def custom_filter(self):
        """tendbcluster要求集群分片数为2的幂次"""
        valid_specs: List[Dict[str, Any]] = [
            spec
            for spec in self.specs
            if spec["cluster_shard_num"] and (spec["cluster_shard_num"] & (spec["cluster_shard_num"] - 1)) == 0
        ]
        self.specs = valid_specs


class RedisSpecFilter(ClusterSpecFilter):
    """Redis规格过滤器基类"""

    def _qps_check(self, user_qps_range, spec_qps_range):
        # redis不需要qps校验
        return True

    def custom_filter(self):
        """对规格方案进行排序,根据目标容量,以及未来容量来决定排序方式"""
        if self.future_capacity >= self.capacity:
            self.specs.sort(key=lambda x: (-x["cluster_shard_num"], -x["capacity"], x["machine_pair"]))
        else:
            self.specs.sort(key=lambda x: (x["cluster_shard_num"], -x["capacity"], x["machine_pair"]))


class TendisPlusSpecFilter(RedisSpecFilter):
    """TendisPlus集群规格过滤器"""

    # 最佳容量管理大小 300G
    SINGLE_SHARD_SIZE = 1200
    # 单机 1 ， 2，4 分片 可选
    SINGLE_SHARD_NUMBS = [1, 2, 4]

    def calc_machine_pair(self):
        """计算每种规格所需的机器组数，TendisPlus至少需要三组"""
        for spec in self.specs:
            spec["machine_pair"] = max(math.ceil(self.capacity / spec["capacity"]), 3)
            spec["cluster_capacity"] = spec["machine_pair"] * spec["capacity"]

    def calc_cluster_shard_num(self):
        # 先进行排序
        self.specs.sort(key=lambda x: (x["capacity"]))

        # 选取合适的规格
        spec_idx, spec_cnt, candidate_specs = 0, len(self.specs), []
        # 取相近的规格
        for spec in self.specs:
            if self.capacity <= spec["capacity"]:
                candidate_specs.append(spec)
                if spec_idx >= 1:
                    candidate_specs.append(self.specs[spec_idx - 1])
                break
            spec_idx += 1

        # 最后取两个规格
        if self.capacity > self.specs[spec_cnt - 1]["capacity"]:
            candidate_specs.append(self.specs[spec_cnt - 1])
            if spec_cnt > 2:
                candidate_specs.append(self.specs[spec_cnt - 2])

        aviable_specs: List[Dict[str, Any]] = []
        for spec in candidate_specs:
            shard = max(1, math.ceil(spec["capacity"] / self.SINGLE_SHARD_SIZE) - 1)
            if shard > 2:
                shard = int(shard / 2) * 2
            spec["cluster_shard_num"] = spec["machine_pair"] * shard
            aviable_specs.append(spec)
        self.specs = aviable_specs

    def custom_filter(self):
        super().custom_filter()


class RedisClusterSpecFilter(RedisSpecFilter):
    """官方RedisCluster集群规格过滤器"""

    # 最小机器组数
    MIN_MACHINE_PAIR = 3
    # 单个实例建议的容量规格
    BASE_SINGLE_CAPCITY = 6
    # 支持简单阔缩容倍数（非DTS方式/Slot迁移扩容方式）
    SCALE_MULITPLE = 4

    def __init__(self, capacity, future_capacity, spec_cluster_type, spec_machine_type, qps=None, shard_num=0):
        # 这里的规格类型要转为tendis cache, redis cluster的规格类型同cache
        spec_machine_type = SpecMachineType.TendisTwemproxyRedisInstance
        super().__init__(capacity, future_capacity, spec_cluster_type, spec_machine_type, qps, shard_num)

    def calc_machine_pair(self):
        """计算每种规格所需的机器组数和集群总容量: 目标容量 / 规格容量"""
        for spec in self.specs:
            spec["capacity"] = spec["mem"]["min"]
            # 至少是三组机器
            spec["machine_pair"] = max(math.ceil(self.capacity / spec["capacity"]), self.MIN_MACHINE_PAIR)
            # 集群容量：机器组数 * 规格容量；集群qps：机器组数 * 规格qps的min
            spec["cluster_capacity"] = spec["machine_pair"] * spec["capacity"]
            if self.qps:
                spec["cluster_qps"] = spec["machine_pair"] * spec["qps"]["min"]

    def calc_cluster_shard_num(self):
        self.future_capacity = int(self.future_capacity)
        self.capacity = int(self.capacity)
        valid_specs: List[Dict[str, Any]] = []
        max_capcity = self.capacity
        if self.future_capacity > self.capacity:
            max_capcity = min(self.future_capacity, int(self.capacity) * int(self.SCALE_MULITPLE) / 2)
        # 先进行排序
        self.specs.sort(key=lambda x: (x["capacity"]))

        print(self.specs)

        # 选取合适的规格
        spec_idx, instance_cap, spec_cnt, avaiable_specs = 0, self.BASE_SINGLE_CAPCITY, len(self.specs), []
        for spec in self.specs:
            if self.capacity <= spec["capacity"] * self.MIN_MACHINE_PAIR:
                avaiable_specs.append(spec)
                if spec_idx >= 1:
                    avaiable_specs.append(self.specs[spec_idx - 1])
                if spec_idx >= 3:
                    avaiable_specs.append(self.specs[spec_idx - 2])
                break
            spec_idx += 1

        if self.capacity > self.specs[spec_cnt - 1]["capacity"] * self.SCALE_MULITPLE:
            instance_cap = self.BASE_SINGLE_CAPCITY * self.SCALE_MULITPLE

        if self.capacity > self.specs[spec_cnt - 1]["capacity"]:
            avaiable_specs.append(self.specs[spec_cnt - 1])
            if spec_cnt > 2:
                avaiable_specs.append(self.specs[spec_cnt - 2])

        for spec_new in avaiable_specs:
            # 一定要保证集群总分片数是机器组数的整数倍，
            cluster_shard_num = math.ceil(max_capcity / instance_cap)
            single_machine_shard_num = math.ceil(cluster_shard_num / spec_new["machine_pair"])
            # 并且单机分片数需要取整，取偶
            single_machine_shard_num = max(single_machine_shard_num + (single_machine_shard_num & 1), 2)
            # 保证3分片打底
            spec_new["cluster_shard_num"] = max(
                single_machine_shard_num * spec_new["machine_pair"], self.MIN_MACHINE_PAIR
            )
            valid_specs.append(spec_new)

        self.specs = valid_specs

    def custom_filter(self):
        super().custom_filter()


class TendisSSDSpecFilter(RedisSpecFilter):
    """TendisSSD集群规格过滤器"""

    # 单实例最大容量 50G
    SINGLE_MAX_CAPACITY = 100
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

    # 单个实例建议的容量规格
    BASE_SINGLE_CAPCITY = 6
    # 支持简单阔缩容倍数（非DTS方式）
    SCALE_MULITPLE = 4

    def calc_cluster_shard_num(self):
        valid_specs: List[Dict[str, Any]] = []
        max_capcity = self.capacity
        if self.future_capacity > self.capacity:
            max_capcity = min(self.future_capacity, self.capacity * self.SCALE_MULITPLE / 2)
        # 先进行排序
        self.specs.sort(key=lambda x: (x["capacity"]))

        # 选取合适的规格
        spec_idx, instance_cap, spec_cnt, avaiable_specs = 0, self.BASE_SINGLE_CAPCITY, len(self.specs), []
        for spec in self.specs:
            if self.capacity <= spec["capacity"]:
                avaiable_specs.append(spec)
                if spec_idx >= 1:
                    avaiable_specs.append(self.specs[spec_idx - 1])
                if spec_idx >= 3:
                    avaiable_specs.append(self.specs[spec_idx - 2])
                break
            spec_idx += 1

        if self.capacity > self.specs[spec_cnt - 1]["capacity"] * self.SCALE_MULITPLE:
            instance_cap = self.BASE_SINGLE_CAPCITY * self.SCALE_MULITPLE

        if self.capacity > self.specs[spec_cnt - 1]["capacity"]:
            avaiable_specs.append(self.specs[spec_cnt - 1])
            if spec_cnt > 2:
                avaiable_specs.append(self.specs[spec_cnt - 2])
            if spec_cnt > 3:
                avaiable_specs.append(self.specs[spec_cnt - 3])

        for spec_new in avaiable_specs:
            # 一定要保证集群总分片数是机器组数的整数倍，并且单机分片数需要取整，取偶
            cluster_shard_num = math.ceil(max_capcity / instance_cap)
            single_machine_shard_num = math.ceil(cluster_shard_num / spec_new["machine_pair"])
            single_machine_shard_num = max(single_machine_shard_num + (single_machine_shard_num & 1), 2)
            spec_new["cluster_shard_num"] = max(single_machine_shard_num * spec_new["machine_pair"], 4)

            valid_specs.append(spec_new)

        self.specs = valid_specs

    def custom_filter(self):
        super().custom_filter()


class MongoDBShardSpecFilter(object):
    """mongodb集群的部署方案"""

    def __init__(self, capacity, spec_cluster_type, spec_machine_type, **kwargs):
        if spec_cluster_type != SpecClusterType.MongoDB or spec_machine_type != SpecMachineType.MONGODB:
            raise SpecOperateException(_("请保证输入的集群类型是Mongodb，且机器规格为mongodb"))

        self.specs: List[Dict[str, Any]] = []
        mongodb_specs = Spec.objects.filter(
            spec_machine_type=spec_machine_type, spec_cluster_type=spec_cluster_type, enable=True
        )
        for spec in mongodb_specs:
            spec_info = {**spec.to_dict(), "capacity": spec.capacity}
            spec_info["machine_pair"] = math.ceil(capacity / spec_info["capacity"])
            if self.get_spec_shard_info(spec_info, **kwargs):
                self.specs.append(spec_info)

    @classmethod
    def get_shard_spec(cls, spec: dict, shard_num: int):
        shard_cpu_spec = int(spec["cpu"]["min"] * spec["machine_pair"] / shard_num)
        shard_mem_spec = int(spec["mem"]["min"] * spec["machine_pair"] / shard_num)
        shard_capacity_spec = int(spec["capacity"] * spec["machine_pair"] / shard_num)
        shard_spec = _("{}核{}G内存{}G容量").format(shard_cpu_spec, shard_mem_spec, shard_capacity_spec)
        return shard_spec

    def get_spec_shard_info(self, spec, **kwargs):
        # 获取规格的推荐分片数和合法分片数
        # 最小值：每组机器一个分片；最大值：2个cpu一个分片；推荐值：4个cpu一个分片(mongodb的规格cpu上下限一致，没有浮动)
        min_shard_num = spec["machine_pair"]
        max_shard_num = int(spec["machine_pair"] * spec["cpu"]["min"] / 2)

        if min_shard_num > max_shard_num:
            return False

        # 可选分片数: shard_num % machine_pair == 0
        shard_num_choices = list(range(min_shard_num, max_shard_num + 1, min_shard_num))

        # 如果加了分片过滤，则shard_num_choices只能可选过滤的分片数
        if kwargs.get("shard_num"):
            if kwargs["shard_num"] not in shard_num_choices:
                return False
            shard_num_choices = [kwargs["shard_num"]]

        spec["shard_choices"] = []
        for shard_num in shard_num_choices:
            shard_info = {"shard_num": shard_num, "shard_spec": self.get_shard_spec(spec, shard_num)}
            spec["shard_choices"].append(shard_info)

        spec["shard_recommend"] = min(spec["shard_choices"], key=lambda x: abs(x["shard_num"] - max_shard_num / 2))
        return True

    def get_target_specs(self):
        return self.specs


class ResourceHandler(object):
    """资源池接口的处理函数"""

    @classmethod
    def spec_resource_count(
        cls, bk_biz_id: int, bk_cloud_id: int, sub_zone_ids: List[int], spec_ids: List[int], city: str
    ):
        """规格预估资源数量"""
        specs = Spec.objects.filter(spec_id__in=spec_ids)
        if not specs.exists():
            return {}
        # 获取resource_type
        spec_cluster_type = list(set(specs.values_list("spec_cluster_type", flat=True)))
        if len(spec_cluster_type) > 1:
            raise SpecOperateException(_("请保证请求的规格类型一致"))
        resource_type = spec_cluster_type[0]
        # 构造申请参数
        spec_count_details = [
            spec.get_group_apply_params(group_mark=str(spec.spec_id), count=1, group_count=1, bk_cloud_id=bk_cloud_id)
            for spec in specs
        ]
        spec_count_details = list(itertools.chain(*spec_count_details))
        spec_count_params = {
            "location_spec": {"city": "" if city == "default" else city, "sub_zone_ids": sub_zone_ids},
            "for_biz_id": bk_biz_id,
            "resource_type": resource_type,
            "bk_cloud_id": bk_cloud_id,
            "details": spec_count_details,
        }
        # 获取规格的预估数量，注意剔除分组后缀
        spec_apply_count = DBResourceApi.apply_count(params=spec_count_params)
        spec_apply_count = {k.split("_")[0]: v for k, v in spec_apply_count.items()}
        return spec_apply_count

    @staticmethod
    def resource_list(params):
        """资源列表"""

        def _format_resource_fields(data, _cloud_info, _biz_infos, _tag_infos):
            data.update(
                {
                    "bk_cloud_name": _cloud_info[str(data["bk_cloud_id"])]["bk_cloud_name"],
                    "bk_host_innerip": data["ip"],
                    "bk_mem": data.pop("dram_cap"),
                    "bk_cpu": data.pop("cpu_num"),
                    "bk_disk": data.pop("total_storage_cap"),
                    "resource_type": data.pop("rs_type"),
                    "for_biz": {
                        "bk_biz_id": data["dedicated_biz"],
                        "bk_biz_name": _biz_infos.get(data["dedicated_biz"]),
                    },
                    "agent_status": int(
                        (data.pop("gse_agent_status_code") == GseApi.Constants.GSE_AGENT_RUNNING_CODE)
                    ),
                    "labels": [{"id": _tag, "name": _tag_infos.get(int(_tag))} for _tag in data.pop("labels") or []],
                }
            )
            return data

        resource_data = DBResourceApi.resource_list(params=params)
        if not resource_data["details"]:
            return {"count": 0, "results": []}

        # 获取云区域信息和业务信息
        cloud_info = ResourceQueryHelper.search_cc_cloud(get_cache=True)
        for_biz_ids = [data["dedicated_biz"] for data in resource_data["details"] if data["dedicated_biz"]]
        for_biz_infos = AppCache.batch_get_app_attr(bk_biz_ids=for_biz_ids, attr_name="bk_biz_name")
        # 获取标签信息
        label_ids = itertools.chain(*[data["labels"] for data in resource_data["details"] if data["labels"]])
        label_ids = [int(id) for id in label_ids if isinstance(id, int) or id.isdigit()]
        tag_infos = {tag.id: tag.value for tag in Tag.objects.filter(id__in=label_ids)}
        # 格式化资源池字段信息
        for data in resource_data.get("details") or []:
            _format_resource_fields(data, cloud_info, for_biz_infos, tag_infos)

        resource_data["results"] = resource_data.pop("details")
        return resource_data

    @classmethod
    def spec_cost_estimate(cls, db_type: DBType, resource_spec: dict):
        """规格预估运营成本"""
        # 获取组件运营单价
        cost_estimate = SystemSettings.get_setting_value(key=SystemSettingsEnum.COST_ESTIMATE, default={})
        db_cost_estimate = cost_estimate.get(db_type, COST_ESTIMATE_TEMPLATE)

        # 获取规格信息
        spec_ids = [spec["spec_id"] for role, spec in resource_spec.items()]
        spec_map = Spec.objects.in_bulk(spec_ids, field_name="spec_id")

        # 计算预期成本
        excepted_cost = 0
        for role, apply_spec in resource_spec.items():
            spec = spec_map[apply_spec["spec_id"]]
            # 申请数量，后端是组数要乘2
            count = apply_spec["count"] * 2 if role == "backend_group" else apply_spec["count"]
            # 每台机器预估单价
            cpu_per_cost = spec.cpu["max"] * db_cost_estimate["cpu"]
            mem_per_cost = spec.mem["max"] * db_cost_estimate["mem"]
            disk_per_cost = sum([db_cost_estimate["storage"][d["type"]] * d["min"] for d in spec.storage_spec])
            # 合并计算总价
            excepted_cost += (cpu_per_cost + mem_per_cost + disk_per_cost) * count

        return int(excepted_cost)

    @classmethod
    def standardized_resource_host(cls, hosts: List[Dict]):
        """标准化主机信息，将cc字段统一成资源池字段"""
        host_ids = [host["bk_host_id"] for host in hosts]
        # 获取主机通用信息
        hosts = ResourceQueryHelper.search_cc_hosts(role_host_ids=host_ids)
        # 获取主机拓扑信息
        host_topos = CCApi.batch_find_host_biz_relations({"bk_host_id": host_ids})
        host_biz_map = {host["bk_host_id"]: host["bk_biz_id"] for host in host_topos}
        # 补充主机信息
        for host in hosts:
            host.update(
                bk_biz_id=host_biz_map.get(host["bk_host_id"]),
                status=int(host.get("status", 0)),
                ip=host.get("bk_host_innerip"),
                city=host.get("idc_city_name"),
                host_id=host.get("bk_host_id"),
                os_name=host.get("bk_os_name"),
                os_type=host.get("bk_os_type"),
                device_class=host.get("svr_device_class"),
                bk_cpu=host.get("bk_cpu") or 0,
                bk_mem=host.get("bk_mem") or 0,
                bk_disk=host.get("bk_disk") or 0,
            )
        return hosts

    @classmethod
    def create_replenish(cls, username, bk_biz_id: int, infos: List[Dict], remark: str = "", record_id: int = None):
        """创建海磊资源池补货单
        @param record_id: 已预创建的补货记录ID，异步调用时传入；为空则自动创建
        注：因为这个接口有限频，所以必须！！异步调用！！
        """
        ticket_ids, details = [], defaultdict(lambda: 0)
        # 海磊限制，每个单据最大申请数量不超过100
        MAX_COUNT_PER_TICKET = 100

        for info in infos:
            count = info.get("count", 0)
            # 当还有剩余数量时，继续创建单据
            while count > 0:
                resource_count = min(MAX_COUNT_PER_TICKET, count)
                count -= resource_count
                replenish_info = info.copy()
                replenish_info["count"] = resource_count

                # 创建补货单
                ticket = Ticket.create_ticket(
                    ticket_type=TicketType.RESOURCE_HCM_REPLENISH,
                    creator=username,
                    bk_biz_id=bk_biz_id,
                    details=replenish_info,
                    remark=remark,
                )
                # 填充补货记录信息
                details[replenish_info["db_type"]] += replenish_info["count"]
                ticket_ids.append(ticket.id)
                # 暂停一下，控制提交频率
                time.sleep(0.5)

        # 更新或创建补货记录
        if record_id:
            ResourceReplenishRecord.objects.filter(id=record_id).update(ticket_ids=ticket_ids, details=dict(details))
        elif ticket_ids:
            ResourceReplenishRecord.objects.create(creator=username, ticket_ids=ticket_ids, details=details)

    @classmethod
    @func_cache_decorator(cache_time=60 * 10)
    def calc_resource_water_level(cls, need_replenish: bool = True):
        """计算资源池水位(计算较慢，默认缓存10min)"""

        # 获取补货比例、操作系统映射、园区映射、规格信息映射
        spec_map = {spec.spec_id: spec for spec in Spec.objects.filter(tags__key=SystemTagEnum.REPLENISH)}
        ratio_map = SystemSettings.get_setting_value(SystemSettingsEnum.REPLENISH_RATIO_MAP, {})
        os_map = SystemSettings.get_setting_value(SystemSettingsEnum.REPLENISH_OS_MAP, {})
        os_map = {os_name: os_key for os_key, os_names in os_map.items() for os_name in os_names}
        subzone_map = SystemSettings.get_setting_value(SystemSettingsEnum.REPLENISH_SUBZONE_MAP, {})
        subzone_map = {name: zone_key for zone_key, zone_names in subzone_map.items() for name in zone_names}
        # excluded_city = SystemSettings.get_setting_value(SystemSettingsEnum.REPLENISH_EXCLUDED_CITY, ["default"])

        # 不符合水位数据的统计函数定义
        exclusive_spec = []
        exclusive_machine = {"empty_os": [], "empty_city": [], "empty_subzone": []}

        def add_exclusive_machine_infos(hosts):
            for host in hosts:
                if not host["bk_os_name"]:
                    exclusive_machine["empty_os"].append(host["ip"])
                if not host["bk_city__bk_idc_city_name"] or host["bk_city__bk_idc_city_name"] == "default":
                    exclusive_machine["empty_city"].append(host["ip"])
                if not host["bk_sub_zone"]:
                    exclusive_machine["empty_subzone"].append(host["ip"])

        def add_exclusive_spec_infos(spec_ids):
            for spec_id in spec_ids:
                if spec_id in spec_map and not spec_map[spec_id].device_class:
                    exclusive_spec.append({"spec_id": spec_id, "spec_name": spec_map[spec_id].spec_name})

        # 按照规格 + 地域 + 园区 + 操作系统聚合主机
        machine_water_level_map = defaultdict(
            lambda: defaultdict(
                lambda: defaultdict(lambda: defaultdict(lambda: {"machine_count": 0, "resource_count": 0}))
            )
        )

        machines = Machine.objects.filter(bk_cloud_id=0).values(
            "spec_id", "bk_os_name", "bk_city__bk_idc_city_name", "bk_sub_zone", "ip"
        )
        for m in machines:
            spec_id, city_name, subzone = m["spec_id"], m["bk_city__bk_idc_city_name"], m["bk_sub_zone"]
            bk_os_name = (m["bk_os_name"] or "").strip().lower().replace(" ", "")
            # 取映射
            bk_os_name = os_map.get(bk_os_name, bk_os_name)
            subzone = subzone_map.get(subzone, subzone)
            machine_water_level_map[spec_id][bk_os_name][city_name][subzone]["machine_count"] += 1

        resource_water_level = DBResourceApi.water_level()["data"] or []
        for info in resource_water_level:
            spec_id, city_name, subzone = info["spec_id"], info["city"], info["sub_zone"]
            bk_os_name = info["os_name_origin"].strip().lower().replace(" ", "")
            # 取映射
            bk_os_name = os_map.get(bk_os_name, bk_os_name)
            subzone = subzone_map.get(subzone, subzone)
            machine_water_level_map[spec_id][bk_os_name][city_name][subzone]["resource_count"] += info["count"]

        # 打平聚合信息，生成资源水位
        default_ratio = ratio_map.get(str(0), 0.01)
        water_level: List[Dict] = [
            {
                "spec_id": spec_id,
                "spec_machine_type": spec_map[spec_id].spec_machine_type,
                "spec_name": spec_map[spec_id].spec_name,
                "db_type": spec_map[spec_id].spec_cluster_type,
                "os_name": bk_os_name,
                "city": city_name,
                "subzone": subzone,
                "machine_count": subzone_info["machine_count"],
                "resource_count": subzone_info["resource_count"],
                "machine_refer_count": math.ceil(
                    subzone_info["machine_count"] * ratio_map.get(str(spec_id), default_ratio)
                ),
            }
            for spec_id, spec_info in machine_water_level_map.items()
            for bk_os_name, bk_os_info in spec_info.items()
            for city_name, city_info in bk_os_info.items()
            for subzone, subzone_info in city_info.items()
            # 过滤掉：操作系统为空，机型为空，城市为空(default)
            if spec_id in spec_map
        ]
        # 仅展示需要补货资源信息（重新计算 machine_refer_count）
        if need_replenish:
            water_level = [info for info in water_level if info["machine_refer_count"] > info["resource_count"]]

        # 获取不符合水位统计信息
        add_exclusive_spec_infos(list(machine_water_level_map.keys()))
        add_exclusive_machine_infos(machines)

        # 补货固定显示时间上午九点
        flush_time = "09:00:00"
        update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return {
            "update_time": update_time,
            "water_level": water_level,
            "flush_time": flush_time,
            "exclusive_spec": exclusive_spec,
            "exclusive_machine": exclusive_machine,
        }

    @classmethod
    def get_replenish_ticket_apply_info_map(cls, ticket_ids: List[int], runtime_info: bool = False) -> Dict[int, Dict]:
        """获取补货单据申请/交付信息映射"""
        tickets = Ticket.objects.prefetch_related("flows").filter(
            id__in=ticket_ids, ticket_type=TicketType.RESOURCE_HCM_REPLENISH.value
        )
        replenish_records = ResourceReplenishRecord.objects.all().values("ticket_ids", "id")
        ticket_replenish_map = {tid: record["id"] for record in replenish_records for tid in record["ticket_ids"]}

        ticket_apply_count_map = {}
        for ticket in tickets:
            inner_flow = list(ticket.flows.all())[-1]
            delivery_count = len(inner_flow.output_data[0]["values"]) if inner_flow and inner_flow.output_data else 0
            info = {
                "apply_count": ticket.details.get("count", 0),
                "delivery_count": delivery_count,
                "details": ticket.details,
                "record_id": ticket_replenish_map.get(ticket.id, ""),
            }
            if runtime_info:
                info.update({"ticket": ticket, "inner_flow": inner_flow})
            ticket_apply_count_map[ticket.id] = info

        return ticket_apply_count_map

    @classmethod
    def get_evnet_info(cls, bk_host_ids, remark, host_id_ip_map):
        from backend.db_services.dbresource.constants import RESOURCE_UPDATE_REMARK

        remark_map = {}
        hosts = []
        for index, host_id in enumerate(bk_host_ids):
            remark_list = []
            remark_info = remark[index]
            for label_key in remark_info:
                before_value = (
                    remark_info[label_key]["before_value"] if remark_info[label_key].get("before_value") else _("无")
                )
                after_value = (
                    remark_info[label_key]["after_value"] if remark_info[label_key].get("after_value") else _("无")
                )
                if before_value == after_value:
                    continue
                remark_list.append(f"{RESOURCE_UPDATE_REMARK[label_key]}: {before_value}→{after_value}")
            if not remark_list:
                continue
            new_remark = ";".join(remark_list)
            remark_map[host_id] = new_remark
            hosts.append({"ip": host_id_ip_map[str(host_id)], "bk_host_id": host_id})

        return remark_map, hosts

    @classmethod
    def resource_export(cls, params):
        data_list = []
        headers = [
            {"id": "ip", "name": _("IP")},
            {"id": "bk_cloud_name", "name": _("管控区域")},
            {"id": "agent_status", "name": _("Agent 状态")},
            {"id": "bk_biz_name", "name": _("所属业务")},
            {"id": "resource_type", "name": _("所属DB")},
            {"id": "labels", "name": _("资源标签")},
            {"id": "city", "name": _("地域")},
            {"id": "sub_zone", "name": _("园区")},
            {"id": "rack_id", "name": _("机架")},
            {"id": "os_type", "name": _("操作系统类型")},
            {"id": "os_name", "name": _("操作系统名称")},
            {"id": "device_class", "name": _("机型")},
            {"id": "bk_cpu", "name": _("CPU(核)")},
            {"id": "bk_mem", "name": _("内存(G)")},
            {"id": "total_data_storage_cap", "name": _("数据盘容量（G）")},
            {"id": "create_time", "name": _("转入时间")},
            {"id": "operator", "name": _("转入人")},
        ]

        resource_res = cls.resource_list(params)
        results = resource_res["results"]
        if results:
            for res in results:
                data_list.append(
                    {
                        "ip": res["ip"],
                        "bk_cloud_name": res["bk_cloud_name"],
                        "agent_status": _("正常") if res["agent_status"] == 1 else _("异常"),
                        "bk_biz_name": _("公共资源池")
                        if res["for_biz"]["bk_biz_id"] == 0
                        else res["for_biz"]["bk_biz_name"],
                        "resource_type": _("通用") if res["resource_type"] == "PUBLIC" else res["resource_type"],
                        "labels": " ".join(label["name"] for label in res["labels"]),
                        "city": res["city"],
                        "sub_zone": res["sub_zone"],
                        "rack_id": res["rack_id"],
                        "os_type": res["os_type"],
                        "os_name": res["os_name"],
                        "device_class": res["device_class"],
                        "bk_cpu": res["bk_cpu"],
                        "bk_mem": round(res["bk_mem"] / 1024, 2),
                        "total_data_storage_cap": res.get("total_data_storage_cap", 0),
                        "create_time": res["create_time"],
                        "operator": res["operator"],
                    }
                )

        wb = ExcelHandler.serialize(data_list, headers=headers, match_header=True)

        return ExcelHandler.response(wb, "dbm_resource_list.xlsx")

    @classmethod
    def list_dba_hosts(cls, params, bk_biz_id):
        scope_list: ScopeList = [{"scope_id": bk_biz_id, "scope_type": "biz", "bk_biz_id": bk_biz_id}]
        trees: List[Dict] = TopoHandler.trees(all_scope=True, mode=ModeType.IDLE_ONLY.value, scope_list=scope_list)
        node_list: ScopeList = [
            {"instance_id": trees[0]["instance_id"], "meta": trees[0]["meta"], "object_id": "module"}
        ]
        params.update(readable_node_list=node_list)
        host_infos = TopoHandler.query_hosts(**params)

        # 查询DBA业务下的空闲机，并排除掉已经在资源池的空闲机
        resource_hosts = DBResourceApi.resource_list_all()["details"] or []
        resource_host_ids = [host["bk_host_id"] for host in resource_hosts]

        for host in host_infos["data"]:
            host.update(occupancy=(host["host_id"] in resource_host_ids))
        return host_infos

    @classmethod
    def resource_import(cls, data, username):
        host_ids = [host["host_id"] for host in data.pop("hosts")]

        # 查询主机信息，并按照集群类型聚合
        host_infos = ResourceQueryHelper.search_cc_hosts(role_host_ids=host_ids)
        os_hosts = defaultdict(list)
        for host in host_infos:
            host.update(ip=host["bk_host_innerip"], host_id=host["bk_host_id"], city_name=host.get("idc_city_name"))
            os_hosts[host["bk_os_type"]].append(host)

        # 按照集群类型分别导入
        ticket_ids = []
        for os_type, hosts in os_hosts.items():
            # 补充必要的单据参数
            data.update(
                ticket_type=TicketType.RESOURCE_IMPORT,
                created_by=username,
                uid=None,
                hosts=hosts,
                operator=username,
                os_type=os_type,
            )
            # 目前产品上重导入只允许从故障池转入资源池
            remark = _("故障池主机转回资源池") if data.get("return_resource") else ""
            # 创建资源导入单据
            ticket = Ticket.create_ticket(
                ticket_type=TicketType.RESOURCE_IMPORT,
                creator=username,
                bk_biz_id=data["bk_biz_id"],
                remark=remark,
                details=data,
            )
            ticket_ids.append(ticket.id)
        return ticket_ids

    @classmethod
    def resource_delete(cls, data, username, hosts_qs=None):
        from backend.db_dirty.models import DirtyMachine, MachineEvent

        bk_host_ids = [host["bk_host_id"] for host in data["hosts"]]

        # 检查主机数量 & 仍处于资源池
        if not hosts_qs:
            hosts_qs = DirtyMachine.objects.filter(bk_host_id__in=bk_host_ids)
        if hosts_qs.count() != len(bk_host_ids):
            raise ResourceReturnException(_("删除主机部分不存在资源池，请重新操作"))
        if list(set(hosts_qs.values_list("pool", flat=True))) != [PoolType.Resource]:
            raise ResourceReturnException(_("请保证删除的主机处于资源池中"))

        if data["event"] == MachineEventType.UndoImport:
            # 撤销导入需要判断机器是否可退回
            ok, message = MachineEvent.hosts_can_return(bk_host_ids)
            if not ok:
                raise ResourceReturnException(message)

            # 从资源池删除机器，并退回各个业务的空闲机。这里主机的业务ID就是导入时的来源业务
            biz_hosts_groups = itertools.groupby(data["hosts"], key=lambda x: x["bk_biz_id"])
            for bk_biz_id, hosts in biz_hosts_groups:
                hosts = list(hosts)
                MachineEvent.host_event_trigger(bk_biz_id, hosts, data["event"], username, remark=data["remark"])
                CcManage.transfer_host_to_idlemodule_across_biz(bk_biz_id, [host["bk_host_id"] for host in hosts])
        else:
            # 转移故障池/待回收池则仅记录主机事件
            MachineEvent.host_event_trigger(
                env.DBA_APP_BK_BIZ_ID, data["hosts"], data["event"], username, remark=data["remark"]
            )
            Todo.host_todo_trigger(bk_host_ids, [username], data["event"], None)

        # 调用资源池api删除资源
        resp = DBResourceApi.resource_delete(params={"bk_host_ids": bk_host_ids}, raw=True)
        if resp["code"]:
            raise ResourceReturnException(_("资源删除失败，错误信息: {}").format(resp.get("message")))
        return resp


@shared_task
def async_create_replenish(username, bk_biz_id, infos, remark="", record_id=None):
    """异步创建补货单据，避免前端同步请求超时"""
    ResourceHandler.create_replenish(username, bk_biz_id, infos, remark, record_id=record_id)


@shared_task
def async_retry_replenish_tickets(replenish_record_id, username, ticket_ids=None):
    from backend.ticket.flow_manager.inner import HCMReplenishResourceTaskFlow

    # 对补货记录加行锁， 防止多次重试
    with transaction.atomic():
        replenish = ResourceReplenishRecord.objects.select_for_update().filter(id=replenish_record_id).first()
        if not replenish:
            return

        if replenish.details.get("lock"):
            return

        # 对传过来的单据id进行过滤
        retry_ticket_ids = (
            [ticket_id for ticket_id in replenish.ticket_ids if ticket_id in ticket_ids]
            if ticket_ids
            else replenish.ticket_ids
        )

        # 打上标记
        details = replenish.details
        details["lock"] = True
        replenish.details = details
        replenish.save(update_fields=["details"])

    try:
        tickets = Ticket.objects.filter(id__in=retry_ticket_ids, status=TicketStatus.FAILED)
        if not tickets:
            return

        error_flows = Flow.objects.filter(ticket__in=tickets, status=TicketFlowStatus.FAILED)
        for flow in error_flows:
            if flow.err_code == FlowErrCode.HCM_APPLY_LACK_RESOURCE_ERROR:
                HCMReplenishResourceTaskFlow(flow).retry()
            else:
                flow_handler = TaskFlowHandler(root_id=flow.flow_obj_id)
                node_ids = flow_handler.get_specific_node_ids(status=StateType.FAILED)
                for node_id in node_ids:
                    flow_handler.retry_node(node_id, username)

    except Exception as err:
        logger.error("retry replenish ticket node error: {}".format(err))
    finally:
        replenish = ResourceReplenishRecord.objects.filter(id=replenish_record_id).first()
        if replenish and replenish.details.get("lock"):
            details = replenish.details
            details["lock"] = False
            replenish.details = details
            replenish.save(update_fields=["details"])
            logger.info("clear  retry  replenish flag")
