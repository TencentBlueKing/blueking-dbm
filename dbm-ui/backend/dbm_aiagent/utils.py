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

import importlib
from typing import Callable, Dict, List, Optional, Tuple, Type

from django.db.models import QuerySet

from backend.dbm_aiagent.models import (
    BaselineDisk,
    BaselineHost,
    BenchmarkHostConfig,
    TenDBClusterBenchmark,
    TenDBHABenchmark,
    TenDBSingleBenchmark,
)


def get_class_from_qualname(func: Callable) -> Optional[Type]:
    """
    从函数的 __qualname__ 中获取所属的类
    """
    if not hasattr(func, "__qualname__"):
        return None

    qualname_parts = func.__qualname__.split(".")
    if len(qualname_parts) < 2:
        return None

    # 类名是倒数第二个部分
    class_name = qualname_parts[-2]
    module = importlib.import_module(func.__module__)
    if module:
        return getattr(module, class_name, None)

    return None


def list_to_choices(values: List[str]) -> List[Tuple[str, str]]:
    res = []
    for ele in values:
        res.append((ele, ele))

    return res


def query_baseline_specs(device_class: str, disk_type: Optional[str] = None) -> Dict[str, Optional[QuerySet]]:
    """
    根据主机机型和磁盘类型查询基线配置数据

    @param device_class: 主机机型编码，如 "ITA3.4XLARGE64-p2w"
    @param disk_type: 磁盘类型（可选），如 "NVME_SSD"，传入 None 则查询所有磁盘配置
    @return: 包含基线主机配置和基线磁盘配置查询集的字典
        {
            "baseline_host": BaselineHost实例或None,
            "baseline_disks": BaselineDisk查询集（可能为空）
        }

    使用示例：
        # 查询指定主机机型和磁盘类型
        result = query_baseline_specs("ITA3.4XLARGE64-p2w", "NVME_SSD")
        if result["baseline_host"]:
            print(f"基线主机配置: {result['baseline_host'].device_class}")
        for disk in result["baseline_disks"]:
            print(f"基线磁盘配置: {disk.disk_name}")

        # 仅查询主机机型
        result = query_baseline_specs("ITA3.4XLARGE64-p2w")
        # 查询所有磁盘配置
        result = query_baseline_specs("", "NVME_SSD")
    """
    result = {"baseline_host": None, "baseline_disks": BaselineDisk.objects.none()}

    # 查询基线主机配置
    if device_class:
        try:
            result["baseline_host"] = BaselineHost.objects.get(device_class=device_class)
        except BaselineHost.DoesNotExist:
            # 主机机型不存在，返回 None
            pass

    # 查询基线磁盘配置
    if disk_type:
        result["baseline_disks"] = BaselineDisk.objects.filter(disk_type=disk_type)
    elif not device_class:
        # 如果没有指定主机机型也没有指定磁盘类型，则返回空查询集
        result["baseline_disks"] = BaselineDisk.objects.none()

    return result


def query_baseline_host(device_class: str) -> Optional[BaselineHost]:
    """
    根据主机机型编码查询基线主机配置

    @param device_class: 主机机型编码，如 "ITA3.4XLARGE64-p2w"
    @return: BaselineHost实例或None

    使用示例：
        baseline_host = query_baseline_host("ITA3.4XLARGE64-p2w")
        if baseline_host:
            print(f"基线主机配置: {baseline_host.device_class}, vCPU: {baseline_host.vcpu}, 内存: {baseline_host.memory_gb}GB")
    """
    try:
        return BaselineHost.objects.get(device_class=device_class)
    except BaselineHost.DoesNotExist:
        return None


def query_baseline_disks(disk_type: str) -> QuerySet:
    """
    根据磁盘类型查询基线磁盘配置

    @param disk_type: 磁盘类型，如 "NVME_SSD"
    @return: BaselineDisk查询集

    使用示例：
        baseline_disks = query_baseline_disks("NVME_SSD")
        for disk in baseline_disks:
            print(f"基线磁盘配置: {disk.disk_name}, IOPS: {disk.performance_iops}")
    """
    return BaselineDisk.objects.filter(disk_type=disk_type)


def query_baseline_disk_by_name(disk_name: str) -> Optional[BaselineDisk]:
    """
    根据磁盘配置名称查询基线磁盘配置

    @param disk_name: 磁盘配置名称，如 "NVMe_SSD_3570"
    @return: BaselineDisk实例或None

    使用示例：
        baseline_disk = query_baseline_disk_by_name("NVMe_SSD_3570")
        if baseline_disk:
            print(f"基线磁盘配置: {baseline_disk.disk_name}, IOPS: {baseline_disk.performance_iops}")
    """
    try:
        return BaselineDisk.objects.get(disk_name=disk_name)
    except BaselineDisk.DoesNotExist:
        return None


def query_benchmark_host_config(
    device_class: str, disk_type: str, os_version: str, disk_quantity: int
) -> Optional[BenchmarkHostConfig]:
    """
    查询或获取性能基准测试主机配置

    @param device_class: 主机机型编码，如 "ITA3.4XLARGE64-p2w"
    @param disk_type: 磁盘类型，如 "NVME_SSD"
    @param os_version: 操作系统版本，如 "CentOS 7.9"
    @param disk_quantity: 磁盘数量
    @return: BenchmarkHostConfig实例或None

    使用示例：
        config = query_benchmark_host_config("ITA3.4XLARGE64-p2w", "NVME_SSD", "CentOS 7.9", 4)
    """
    try:
        baseline_host = BaselineHost.objects.get(device_class=device_class)
        baseline_disk = BaselineDisk.objects.filter(disk_type=disk_type).first()

        if not baseline_disk:
            return None

        config = BenchmarkHostConfig.objects.get(
            baseline_host=baseline_host,
            baseline_disk=baseline_disk,
            os_version=os_version,
            disk_quantity=disk_quantity,
        )
        return config
    except (BaselineHost.DoesNotExist, BenchmarkHostConfig.DoesNotExist):
        return None


def query_tendbsingle_benchmark(
    device_class: str,
    disk_type: str,
    mysql_version: str,
    os_version: Optional[str] = None,
    disk_quantity: Optional[int] = None,
    concurrent_threads: Optional[int] = None,
) -> QuerySet:
    """
    查询 TenDBSingle 性能基准测试结果

    @param device_class: 主机机型编码
    @param disk_type: 磁盘类型
    @param mysql_version: MySQL 版本
    @param os_version: 操作系统版本（可选）
    @param disk_quantity: 磁盘数量（可选）
    @param concurrent_threads: 并发线程数（可选）
    @return: TenDBSingleBenchmark查询集

    使用示例：
        benchmarks = query_tendbsingle_benchmark("ITA3.4XLARGE64-p2w", "NVME_SSD", "5.7.20")
    """
    try:
        baseline_host = BaselineHost.objects.get(device_class=device_class)
        baseline_disk_qs = BaselineDisk.objects.filter(disk_type=disk_type)

        if not baseline_disk_qs.exists():
            return TenDBSingleBenchmark.objects.none()

        # 构建配置查询条件
        config_filters = {
            "baseline_host": baseline_host,
            "baseline_disk__in": baseline_disk_qs,
        }
        if os_version:
            config_filters["os_version"] = os_version
        if disk_quantity:
            config_filters["disk_quantity"] = disk_quantity

        configs = BenchmarkHostConfig.objects.filter(**config_filters)

        # 查询基准测试结果
        benchmark_filters = {"host_config__in": configs, "mysql_version": mysql_version}
        if concurrent_threads:
            benchmark_filters["concurrent_threads"] = concurrent_threads

        return TenDBSingleBenchmark.objects.filter(**benchmark_filters).order_by("-avg_qps")

    except BaselineHost.DoesNotExist:
        return TenDBSingleBenchmark.objects.none()


def query_tendbha_benchmark(
    proxy_device_class: str,
    proxy_disk_type: str,
    backend_device_class: str,
    backend_disk_type: str,
    proxy_version: str,
    backend_version: str,
    proxy_os_version: Optional[str] = None,
    backend_os_version: Optional[str] = None,
    proxy_count: Optional[int] = None,
    slave_count: Optional[int] = None,
    concurrent_threads: Optional[int] = None,
) -> QuerySet:
    """
    查询 TenDBHA 性能基准测试结果

    @param proxy_device_class: Proxy 机型
    @param proxy_disk_type: Proxy 磁盘类型
    @param backend_device_class: Backend 机型
    @param backend_disk_type: Backend 磁盘类型
    @param proxy_version: Proxy 版本
    @param backend_version: Backend 版本
    @param proxy_os_version: Proxy 操作系统版本（可选）
    @param backend_os_version: Backend 操作系统版本（可选）
    @param proxy_count: Proxy 数量（可选）
    @param slave_count: Slave 数量（可选）
    @param concurrent_threads: 并发线程数（可选）
    @return: TenDBHABenchmark查询集

    使用示例：
        benchmarks = query_tendbha_benchmark(
            "SA3.2XLARGE32", "NVME_SSD",
            "ITA3.4XLARGE64", "CLOUD_SSD",
            "1.2.3", "5.7.20"
        )
    """
    try:
        # 查询 Proxy 配置
        proxy_host = BaselineHost.objects.get(device_class=proxy_device_class)
        proxy_disks = BaselineDisk.objects.filter(disk_type=proxy_disk_type)

        # 查询 Backend 配置
        backend_host = BaselineHost.objects.get(device_class=backend_device_class)
        backend_disks = BaselineDisk.objects.filter(disk_type=backend_disk_type)

        if not proxy_disks.exists() or not backend_disks.exists():
            return TenDBHABenchmark.objects.none()

        # 构建 Proxy 配置查询条件
        proxy_config_filters = {"baseline_host": proxy_host, "baseline_disk__in": proxy_disks}
        if proxy_os_version:
            proxy_config_filters["os_version"] = proxy_os_version

        # 构建 Backend 配置查询条件
        backend_config_filters = {"baseline_host": backend_host, "baseline_disk__in": backend_disks}
        if backend_os_version:
            backend_config_filters["os_version"] = backend_os_version

        proxy_configs = BenchmarkHostConfig.objects.filter(**proxy_config_filters)
        backend_configs = BenchmarkHostConfig.objects.filter(**backend_config_filters)

        # 查询基准测试结果
        benchmark_filters = {
            "proxy_host_config__in": proxy_configs,
            "backend_host_config__in": backend_configs,
            "proxy_version": proxy_version,
            "backend_version": backend_version,
        }
        if proxy_count:
            benchmark_filters["proxy_count"] = proxy_count
        if slave_count:
            benchmark_filters["backend_slave_count"] = slave_count
        if concurrent_threads:
            benchmark_filters["concurrent_threads"] = concurrent_threads

        return TenDBHABenchmark.objects.filter(**benchmark_filters).order_by("-avg_qps")

    except (BaselineHost.DoesNotExist, BaselineDisk.DoesNotExist):
        return TenDBHABenchmark.objects.none()


def query_tendbcluster_benchmark(
    spider_device_class: str,
    spider_disk_type: str,
    remote_device_class: str,
    remote_disk_type: str,
    spider_version: str,
    remote_version: str,
    spider_os_version: Optional[str] = None,
    remote_os_version: Optional[str] = None,
    spider_count: Optional[int] = None,
    shard_count: Optional[int] = None,
    concurrent_threads: Optional[int] = None,
) -> QuerySet:
    """
    查询 TenDBCluster 性能基准测试结果

    @param spider_device_class: Spider 机型
    @param spider_disk_type: Spider 磁盘类型
    @param remote_device_class: Remote 机型
    @param remote_disk_type: Remote 磁盘类型
    @param spider_version: Spider 版本
    @param remote_version: Remote 版本
    @param spider_os_version: Spider 操作系统版本（可选）
    @param remote_os_version: Remote 操作系统版本（可选）
    @param spider_count: Spider 数量（可选）
    @param shard_count: 分片数量（可选）
    @param concurrent_threads: 并发线程数（可选）
    @return: TenDBClusterBenchmark查询集

    使用示例：
        benchmarks = query_tendbcluster_benchmark(
            "SA3.2XLARGE32", "NVME_SSD",
            "ITA3.4XLARGE64", "CLOUD_SSD",
            "3.4.5", "5.7.20",
            shard_count=4
        )
    """
    try:
        # 查询 Spider 配置
        spider_host = BaselineHost.objects.get(device_class=spider_device_class)
        spider_disks = BaselineDisk.objects.filter(disk_type=spider_disk_type)

        # 查询 Remote 配置
        remote_host = BaselineHost.objects.get(device_class=remote_device_class)
        remote_disks = BaselineDisk.objects.filter(disk_type=remote_disk_type)

        if not spider_disks.exists() or not remote_disks.exists():
            return TenDBClusterBenchmark.objects.none()

        # 构建 Spider 配置查询条件
        spider_config_filters = {"baseline_host": spider_host, "baseline_disk__in": spider_disks}
        if spider_os_version:
            spider_config_filters["os_version"] = spider_os_version

        # 构建 Remote 配置查询条件
        remote_config_filters = {"baseline_host": remote_host, "baseline_disk__in": remote_disks}
        if remote_os_version:
            remote_config_filters["os_version"] = remote_os_version

        spider_configs = BenchmarkHostConfig.objects.filter(**spider_config_filters)
        remote_configs = BenchmarkHostConfig.objects.filter(**remote_config_filters)

        # 查询基准测试结果
        benchmark_filters = {
            "spider_host_config__in": spider_configs,
            "remote_host_config__in": remote_configs,
            "spider_version": spider_version,
            "remote_version": remote_version,
        }
        if spider_count:
            benchmark_filters["spider_count"] = spider_count
        if shard_count:
            benchmark_filters["shard_count"] = shard_count
        if concurrent_threads:
            benchmark_filters["concurrent_threads"] = concurrent_threads

        return TenDBClusterBenchmark.objects.filter(**benchmark_filters).order_by("-avg_qps")

    except (BaselineHost.DoesNotExist, BaselineDisk.DoesNotExist):
        return TenDBClusterBenchmark.objects.none()
