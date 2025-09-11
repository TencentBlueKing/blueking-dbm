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

import copy
import datetime
from collections import defaultdict

from backend.components.bkmonitorv3.client import BKMonitorV3Api
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models.cluster import Cluster
from backend.db_services.ipchooser.handlers.host_handler import HostHandler
from backend.db_services.redis.capacity_evaluate_service.repositories.cvm_repo import CvmSpec
from backend.db_services.redis.capacity_evaluate_service.repositories.redis_cluster_repo import DbmClusterRepository
from backend.db_services.redis.capacity_evaluate_service.util import is_dev, logger_debug

# UNIFY_QUERY_PARAMS is used to query prometheus
UNIFY_QUERY_PARAMS = {
    "bk_biz_id": 3,
    "query_configs": [
        {
            "data_source_label": "prometheus",
            "data_type_label": "time_series",
            "promql": "",  # we will set promql in exec_promql_instant
            "interval": 60,
            "alias": "a",
        }
    ],
    "expression": "a",
    "alias": "a",
    "start_time": 1697100405,  # we will set start_time in exec_promql_instant
    "end_time": 1697101305,  # we will set end_time in exec_promql_instant
    "slimit": 500,
    "down_sample_range": "1s",
    # 取最新的几个周期，可以加速查询（如果指标数据不连续，则查不出数据）
    "type": "instant",
}


class ClusterTopoInfo:
    """
    集群拓扑信息,shard_list,proxy_list,storage_list,host_infos
    """

    cluster_id: int
    cluster_type: str
    cluster_domain: str
    bk_biz_id: int
    proxy_list: list = []
    storage_list: list = []
    shard_list: list = []
    host_infos: list = []
    proxy_cpu_total, proxy_mem_total = 0, 0
    proxy_spec, shard_spec = "", ""
    storage_cpu_total, storage_mem_total_m, storage_disk_total = 0, 0, 0

    def __dict__(self):
        return {
            "cluster_id": self.cluster_id,
            "cluster_domain": self.cluster_domain,
            "bk_biz_id": self.bk_biz_id,
            "cluster_type": self.cluster_type,
            "proxy_list": self.proxy_list,
            "storage_list": self.storage_list,
            "proxy_cpu_total": self.proxy_cpu_total,
            "proxy_mem_total": self.proxy_mem_total,
            "proxy_num": self.proxy_num,
            "shard_num": self.shard_num,
            "proxy_spec": self.proxy_spec,
            "shard_spec": self.shard_spec,
            "storage_cpu_total": self.storage_cpu_total,
            "storage_mem_total_m": self.storage_mem_total_m,
            "storage_disk_total": self.storage_disk_total,
        }

    def __init__(self, cluster_id: int, bk_biz_id: int):
        self.cluster_id = cluster_id
        self.bk_biz_id = bk_biz_id

    @property
    def proxy_num(self):
        return len(self.proxy_list)

    @property
    def shard_num(self):
        return len(self.shard_list)

    def get_master_ip_list(self) -> list:
        master_ip_list = []
        for shard in self.shard_list:
            master_ip_list.append(shard["members"][0]["ip"])
        return master_ip_list

    def fetch_data(self):
        """fetch data from db, proxy, storage, host_infos"""
        self.fetch_instance_data()
        self.fetch_host_infos()
        self.generate_spec_info()

    def fetch_host_infos(self):
        """fetch host_infos from db"""
        bk_host_ids = []
        for proxy in self.proxy_list:
            bk_host_ids.append(proxy["bk_host_id"])
        for storage in self.storage_list:
            bk_host_ids.append(storage["bk_host_id"])
        host_infos = HostHandler.check(scope_list=[], ip_list=[], ipv6_list=[], key_list=bk_host_ids)
        for host in host_infos:
            print(f"host_info: {host}")
            cvm_spec = CvmSpec.from_host_info(host)
            if cvm_spec is None:
                raise Exception(f"cvm_spec is None, host_info: {host}")
            host["cvm_spec"] = cvm_spec
        self.host_infos = host_infos

    def fetch_instance_data(self):
        """fetch instance data from db"""
        cluster = Cluster.objects.get(id=self.cluster_id)
        if cluster.bk_biz_id != self.bk_biz_id:
            pass
            # todo 检查用户对cluster.bk_biz_id 是否有权限
        self.cluster_type = cluster.cluster_type
        self.cluster_domain = cluster.immute_domain
        proxy_list = DbmClusterRepository.fetch_proxy_list(cluster.bk_biz_id, cluster.id)
        storage_list = DbmClusterRepository.fetch_storage_list(cluster.id, with_shard_name=True)
        shard_list = DbmClusterRepository.build_shard_list_by_instance_list(storage_list)
        self.proxy_list = proxy_list
        self.shard_list = shard_list
        self.storage_list = storage_list
        self.fetch_host_infos()

    def generate_spec_info(self):
        """generate spec info, proxy_spec, shard_spec"""

        # prepare data
        bk_host_ids = []
        ip_list = []
        bk_cloud_id_list = []
        # proxy_num_in_cluster 和 shard_num_in_cluster 用于统计每个ip的proxy和shard数量
        _proxy_num_in_cluster = defaultdict(int)
        _shard_num_in_cluster = defaultdict(int)
        for proxy in self.proxy_list:
            _proxy_num_in_cluster[proxy["ip"]] += 1
            bk_host_ids.append(proxy["bk_host_id"])
            ip_list.append(proxy["ip"])
            bk_cloud_id_list.append(proxy["bk_cloud_id"])
        for shard in self.shard_list:
            first_member = shard["members"][0]
            _shard_num_in_cluster[first_member["ip"]] += 1
            bk_host_ids.append(first_member["bk_host_id"])
            ip_list.append(first_member["ip"])
            bk_cloud_id_list.append(first_member["bk_cloud_id"])

        bk_cloud_id_list = list(set(bk_cloud_id_list))
        bk_host_ids = list(set(bk_host_ids))
        ip_list = list(set(ip_list))
        if len(bk_cloud_id_list) > 1:
            raise Exception("cluster has multiple bk_cloud_id")

        if len(bk_host_ids) == 0:
            return

        # inst_num_by_ip 每个机器上注册的实例数量. 用于计算本集群的占比 （按平均比例）
        inst_num_by_ip = DbmClusterRepository.fetch_ip_instance_count(ip_list, bk_cloud_id_list[0])
        host_infos_map = {host["ip"]: host for host in self.host_infos}

        # calculate proxy spec, save to proxy_spec_map
        proxy_spec_map = defaultdict(int)
        proxy_cpu_total, proxy_mem_total, proxy_disk_total = 0, 0, 0
        for ip, num in _proxy_num_in_cluster.items():
            if ip not in host_infos_map:
                raise Exception(f"ip {ip} not found in host_infos_map")
            inst_num_total = inst_num_by_ip[ip]
            cvm_spec = host_infos_map[ip]["cvm_spec"]
            proxy_cpu_core_m = cvm_spec.cpu_core_m * 1 / inst_num_total
            proxy_mem_m = cvm_spec.mem_total_m * 1 / inst_num_total
            proxy_disk_m = cvm_spec.disk_size_total_m * 1 / inst_num_total
            proxy_cpu_total += proxy_cpu_core_m
            proxy_mem_total += proxy_mem_m
            proxy_disk_total += proxy_disk_m
            proxy_spec_map[self.format_spec(proxy_cpu_core_m, proxy_mem_m, 0, "", True)] += num

        # calculate shard spec, save to shard_spec_map
        storage_cpu_total, storage_mem_total_m, storage_disk_total = 0, 0, 0
        shard_spec_map = defaultdict(int)
        for ip, num in _shard_num_in_cluster.items():
            if ip not in host_infos_map:
                raise Exception(f"ip {ip} not found in host_infos_map")
            inst_num_total = inst_num_by_ip[ip]
            cvm_spec = host_infos_map[ip]["cvm_spec"]
            shard_cpu_core_m = cvm_spec.cpu_core_m * 1 / inst_num_total
            shard_mem_m = cvm_spec.mem_total_m * 1 / inst_num_total
            shard_disk_m = cvm_spec.disk_size_total_m * 1 / inst_num_total
            storage_cpu_total += shard_cpu_core_m
            storage_mem_total_m += shard_mem_m
            storage_disk_total += shard_disk_m
            shard_spec_map[self.format_spec(shard_cpu_core_m, shard_mem_m, shard_disk_m, "", False)] += num

        # generate proxy spec and shard spec string
        proxy_spec = ";".join(f"{spec}x{num}" for spec, num in proxy_spec_map.items())
        shard_spec = ";".join(f"{spec}x{num}" for spec, num in shard_spec_map.items())

        # save to self
        self.proxy_cpu_total = proxy_cpu_total
        self.proxy_mem_total = proxy_mem_total
        self.proxy_spec = proxy_spec
        self.shard_spec = shard_spec
        self.storage_cpu_total = storage_cpu_total
        self.storage_mem_total_m = storage_mem_total_m
        self.storage_disk_total = storage_disk_total
        self.shard_cpu_core_m = storage_cpu_total

    @classmethod
    def format_spec(cls, cpu_core_m: int, mem_total_m: int, disk_total_m: int, disk_type: str, no_disk: bool = False):
        """format spec info to string"""
        cpu_core = cpu_core_m / 1000
        mem_total_g = mem_total_m / 1024
        disk_total_g = disk_total_m / 1024
        if cpu_core == 0:
            cpu_core = 0
        if mem_total_g == 0:
            mem_total_g = 0
        if disk_total_m == 0:
            disk_total_m = 0

        # 将cpu_core转为字串，保留1位小数，如果小数位为0，则去掉小数位
        cpu_core_str = f"{cpu_core:.1f}"
        if cpu_core_str.endswith(".0"):
            cpu_core_str = cpu_core_str[:-2]
        mem_total_g_str = f"{mem_total_g:.1f}"
        if mem_total_g_str.endswith(".0"):
            mem_total_g_str = mem_total_g_str[:-2]
        disk_total_g_str = f"{disk_total_g:.1f}"
        if disk_total_g_str.endswith(".0"):
            disk_total_g_str = disk_total_g_str[:-2]
        if no_disk:
            return f"{cpu_core_str}c{mem_total_g_str}g"
        elif disk_type != "":
            return f"{cpu_core_str}c{mem_total_g_str}g{disk_total_g_str}g({disk_type})"
        else:
            return f"{cpu_core_str}c{mem_total_g_str}g{disk_total_g_str}g"

    def get_shard_cpu_core_limit(self):
        """the limit of cpu core used by each shard"""
        if ClusterType.is_memory_redis(self.cluster_type):
            return 1000  # 1000m=1c
        elif ClusterType.is_ssd_redis(self.cluster_type):
            if self.cluster_type == ClusterType.TwemproxyTendisSSDInstance.value:
                return 1000  # 1000m=1c
            else:
                return 1000 * 1000  # 1000c, No Limit
        elif ClusterType.is_mongodb(self.cluster_type):
            return 1000 * 1000  # 1000c, No Limit
        else:
            raise Exception(f"not support cluster_type: {self.cluster_type}")


class ClusterCapacityInfo:
    """cluster capacity info"""

    topo_info: ClusterTopoInfo
    mem_total_m: int
    mem_free_m: int
    mem_used_m: int
    mem_used_max_shard_m: int
    debug_info: dict = {}

    def __init__(self, topo_info: ClusterTopoInfo):
        self.topo_info = topo_info

    def get_mem_total_m(self):
        return self.topo_info.storage_mem_total_m

    def get_mem_free_m(self):
        return self.get_mem_total_m() - self.mem_used_m

    def __dict__(self):
        return {
            "mem_total_m": self.get_mem_total_m(),
            "mem_free_m": self.get_mem_free_m(),
            "mem_used_m": self.mem_used_m,
            "topo_info": self.topo_info.__dict__(),
            "debug_info": self.debug_info,
        }

    def generate_capacity_info(self, bk_biz_id: int):
        """fetch memory used from tsdb, if there are missing instances, return error info"""
        query_errors = []
        instance_address_str = "|".join(self.topo_info.get_master_ip_list())
        sql = f"""avg by (cluster_domain,instance,instance_role) (
        bkmonitor:exporter_dbm_redis_exporter:__default__:redis_memory_used_bytes
        {{bk_target_ip =~ "{instance_address_str}"}})"""
        end_time = datetime.datetime.now()
        start_time = end_time - datetime.timedelta(minutes=5)
        tsdb_result = exec_promql_instant(sql, bk_biz_id, start_time, end_time)
        query_result = tsdb_result_to_map(tsdb_result, "instance")

        # test, set query_result
        if is_dev():
            logger_debug("is_dev, set query_result for test")
            for shard in self.topo_info.shard_list:
                first_member = shard["members"][0]
                instance = first_member["ip"] + ":" + str(first_member["port"])
                query_result[instance] = 1024 * 1024 * 1024

        miss_instances = []
        total_result = 0  # total of query result
        max_result = 0  # max of query result
        count = 0

        if len(self.topo_info.shard_list) == 0:
            query_errors.append("shard_list is empty")
            return query_errors

        for shard in self.topo_info.shard_list:
            first_member = shard["members"][0]
            instance = first_member["ip"] + ":" + str(first_member["port"])
            if instance not in query_result:
                miss_instances.append(instance)
                continue
            v = query_result[instance]
            total_result += v / 1024 / 1024
            if v > max_result:
                max_result = v
            count += 1

        self.mem_used_m = total_result
        self.mem_used_max_shard_m = max_result / 1024 / 1024

        self.debug_info.update({"query_sql": sql})
        self.debug_info.update({"query_result": query_result})
        self.debug_info.update({"sum": total_result})
        self.debug_info.update({"max": max_result})
        self.debug_info.update({"count": count})
        self.debug_info.update({"miss_instances": miss_instances})

        if len(miss_instances) > 0:
            query_errors.append(f"miss_instances: {miss_instances}")
        return query_errors


def tsdb_result_to_map(tsdb_result: dict, key_name: str):
    """
    convert tsdb result to map
    """
    result = {}
    for item in tsdb_result["series"]:
        result[item["dimensions"][key_name]] = item["datapoints"][0][0]
    return result


def exec_promql_instant(promql: str, bk_biz_id: int, start_time, end_time):
    """
    execute promql
    """
    params = copy.deepcopy(UNIFY_QUERY_PARAMS)
    params["bk_biz_id"] = bk_biz_id
    params["start_time"] = int(start_time.timestamp())
    params["end_time"] = int(end_time.timestamp())
    params["query_configs"][0]["promql"] = promql
    try:
        out = BKMonitorV3Api.unify_query(params, use_admin=True)
        return out
    except Exception:
        return None
