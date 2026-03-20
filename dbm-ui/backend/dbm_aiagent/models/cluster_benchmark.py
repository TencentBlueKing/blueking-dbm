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
from django.db import models
from django.utils.translation import gettext_lazy as _

from backend.bk_web.constants import LEN_NORMAL, LEN_SHORT
from backend.bk_web.models import AuditedModel

from .host_baseline import BaselineDisk, BaselineHost


class BenchmarkHostConfig(AuditedModel):
    """
    性能基准测试主机配置
    用于记录压测集群使用的完整主机配置信息，包括主机、磁盘和操作系统
    可被多个 Benchmark 结果复用
    """

    baseline_host = models.ForeignKey(
        BaselineHost,
        on_delete=models.PROTECT,
        help_text=_("关联的基线主机配置"),
    )
    baseline_disk = models.ForeignKey(
        BaselineDisk,
        on_delete=models.PROTECT,
        help_text=_("关联的基线磁盘配置"),
    )
    os_version = models.CharField(
        _("操作系统版本"),
        max_length=LEN_NORMAL,
        help_text=_("操作系统版本，如 CentOS 7.9, Ubuntu 20.04"),
    )
    disk_quantity = models.IntegerField(_("磁盘数量"), help_text=_("该配置使用的磁盘数量，如 2、4、8、16"))

    class Meta(AuditedModel.Meta):
        verbose_name = _("性能基准测试主机配置")
        verbose_name_plural = _("性能基准测试主机配置")
        unique_together = ("baseline_host", "baseline_disk", "os_version", "disk_quantity")
        ordering = ["baseline_host", "baseline_disk"]
        indexes = [
            models.Index(fields=["baseline_host"]),
            models.Index(fields=["baseline_disk"]),
            models.Index(fields=["os_version"]),
        ]

    def __str__(self):
        return f"{self.baseline_host.device_class} - {self.baseline_disk.disk_name} - {self.os_version}"


class TenDBSingleBenchmark(AuditedModel):
    """
    TenDBSingle 性能基准测试结果表
    集群结构：单个 MySQL 实例
    """

    host_config = models.ForeignKey(
        BenchmarkHostConfig,
        on_delete=models.CASCADE,
        related_name="tendbsingle_benchmarks",
        help_text=_("关联的主机配置"),
    )
    mysql_version = models.CharField(_("MySQL版本"), max_length=LEN_NORMAL, help_text=_("MySQL版本，如 5.7.20"))

    # 压测配置
    stress_test_tool = models.CharField(
        _("压测工具"), max_length=LEN_NORMAL, null=True, blank=True, help_text=_("压测工具名称，如 sysbench, tpcc")
    )
    stress_test_tool_version = models.CharField(
        _("压测工具版本"), max_length=LEN_NORMAL, null=True, blank=True, help_text=_("压测工具版本号")
    )
    loaded_data_volume_gb = models.IntegerField(
        _("预导入数据量(GB)"), null=True, blank=True, help_text=_("压测前预先导入到集群的数据量，单位GB")
    )
    loaded_data_volume_rows = models.BigIntegerField(
        _("预导入数据量(行数)"), null=True, blank=True, help_text=_("压测前预先导入到集群的数据行数")
    )
    concurrent_threads = models.IntegerField(_("并发线程数"), help_text=_("并发线程数，如 10, 20, 50, 100, 200, 500, 1000"))
    read_write_ratio = models.CharField(
        _("读写比例"), max_length=LEN_SHORT, null=True, blank=True, help_text=_("读写比例，如 读写8/2")
    )

    # 压测结果
    avg_qps = models.IntegerField(_("平均QPS"), null=True, blank=True, help_text=_("平均QPS（Queries Per Second）"))
    avg_tps = models.FloatField(_("平均TPS"), null=True, blank=True, help_text=_("平均TPS（Transactions Per Second）"))
    avg_latency_ms = models.FloatField(_("平均耗时(ms)"), null=True, blank=True, help_text=_("平均耗时，单位毫秒"))
    p95_latency_ms = models.FloatField(_("95%平均耗时(ms)"), null=True, blank=True, help_text=_("95%平均耗时，单位毫秒"))
    io_usage_rate = models.FloatField(_("IO使用率(%)"), null=True, blank=True, help_text=_("IO使用率，百分比，0-100"))
    cpu_usage_rate = models.FloatField(_("CPU使用率(%)"), null=True, blank=True, help_text=_("CPU使用率，百分比，0-100"))

    class Meta(AuditedModel.Meta):
        verbose_name = _("TenDBSingle性能基准测试结果")
        verbose_name_plural = _("TenDBSingle性能基准测试结果")
        unique_together = ("host_config", "mysql_version", "concurrent_threads", "read_write_ratio")
        ordering = ["host_config", "mysql_version", "concurrent_threads"]
        indexes = [
            # 主机配置查询
            models.Index(fields=["host_config"]),
            # 版本查询
            models.Index(fields=["mysql_version"]),
            # 性能范围查询
            models.Index(fields=["concurrent_threads"]),
            models.Index(fields=["avg_qps"]),
            # 组合查询
            models.Index(fields=["host_config", "mysql_version"]),
        ]

    def __str__(self):
        return f"TenDBSingle - {self.host_config} - MySQL {self.mysql_version} - {self.concurrent_threads}{_('线程')}"


class TenDBHABenchmark(AuditedModel):
    """
    TenDBHA 性能基准测试结果表
    集群结构：Proxy（多个）+ Backend（1 Master + N Slave）
    注意：不同组件类型使用不同的主机配置（Proxy 和 Backend 可以用不同机型）
    """

    # Proxy 配置
    proxy_host_config = models.ForeignKey(
        BenchmarkHostConfig,
        on_delete=models.CASCADE,
        related_name="tendbha_proxy_benchmarks",
        help_text=_("Proxy 主机配置"),
    )
    proxy_version = models.CharField(_("Proxy版本"), max_length=LEN_NORMAL, help_text=_("Proxy版本号"))
    proxy_count = models.IntegerField(_("Proxy数量"), help_text=_("Proxy节点数量，如 2, 3, 4"))

    # Backend 配置
    backend_host_config = models.ForeignKey(
        BenchmarkHostConfig,
        on_delete=models.CASCADE,
        related_name="tendbha_backend_benchmarks",
        help_text=_("Backend 主机配置"),
    )
    backend_version = models.CharField(_("Backend版本"), max_length=LEN_NORMAL, help_text=_("Backend（MySQL）版本"))
    backend_master_count = models.IntegerField(_("Master数量"), default=1, help_text=_("Master数量（通常为1）"))
    backend_slave_count = models.IntegerField(_("Slave数量"), help_text=_("Slave节点数量"))

    # 压测配置
    stress_test_tool = models.CharField(
        _("压测工具"), max_length=LEN_NORMAL, null=True, blank=True, help_text=_("压测工具名称，如 sysbench, tpcc")
    )
    stress_test_tool_version = models.CharField(
        _("压测工具版本"), max_length=LEN_NORMAL, null=True, blank=True, help_text=_("压测工具版本号")
    )
    concurrent_threads = models.IntegerField(_("并发线程数"), help_text=_("并发线程数"))
    loaded_data_volume_gb = models.IntegerField(
        _("预导入数据量(GB)"), null=True, blank=True, help_text=_("压测前预先导入到集群的数据量，单位GB")
    )
    loaded_data_volume_rows = models.BigIntegerField(
        _("预导入数据量(行数)"), null=True, blank=True, help_text=_("压测前预先导入到集群的数据行数")
    )
    read_write_ratio = models.CharField(
        _("读写比例"), max_length=LEN_SHORT, null=True, blank=True, help_text=_("读写比例，如 读写8/2")
    )

    # 压测结果（整体性能指标）
    avg_qps = models.IntegerField(_("平均QPS"), null=True, blank=True, help_text=_("平均QPS（Queries Per Second）"))
    avg_tps = models.FloatField(_("平均TPS"), null=True, blank=True, help_text=_("平均TPS（Transactions Per Second）"))
    avg_latency_ms = models.FloatField(_("平均耗时(ms)"), null=True, blank=True, help_text=_("平均耗时，单位毫秒"))
    p95_latency_ms = models.FloatField(_("95%平均耗时(ms)"), null=True, blank=True, help_text=_("95%平均耗时，单位毫秒"))

    # Proxy 资源使用率
    proxy_io_usage_rate = models.FloatField(
        _("Proxy IO使用率(%)"), null=True, blank=True, help_text=_("Proxy IO使用率，百分比，0-100")
    )
    proxy_cpu_usage_rate = models.FloatField(
        _("Proxy CPU使用率(%)"), null=True, blank=True, help_text=_("Proxy CPU使用率，百分比，0-100")
    )

    # Backend 资源使用率
    backend_io_usage_rate = models.FloatField(
        _("Backend IO使用率(%)"), null=True, blank=True, help_text=_("Backend IO使用率，百分比，0-100")
    )
    backend_cpu_usage_rate = models.FloatField(
        _("Backend CPU使用率(%)"), null=True, blank=True, help_text=_("Backend CPU使用率，百分比，0-100")
    )

    class Meta(AuditedModel.Meta):
        verbose_name = _("TenDBHA性能基准测试结果")
        verbose_name_plural = _("TenDBHA性能基准测试结果")
        unique_together = (
            "proxy_host_config",
            "backend_host_config",
            "proxy_version",
            "backend_version",
            "proxy_count",
            "backend_slave_count",
            "concurrent_threads",
            "read_write_ratio",
        )
        ordering = ["proxy_host_config", "backend_host_config", "concurrent_threads"]
        indexes = [
            # Proxy 配置查询
            models.Index(fields=["proxy_host_config"]),
            models.Index(fields=["proxy_version"]),
            models.Index(fields=["proxy_count"]),
            # Backend 配置查询
            models.Index(fields=["backend_host_config"]),
            models.Index(fields=["backend_version"]),
            models.Index(fields=["backend_slave_count"]),
            # 性能范围查询
            models.Index(fields=["concurrent_threads"]),
            models.Index(fields=["avg_qps"]),
            # 组合查询
            models.Index(fields=["proxy_host_config", "backend_host_config", "proxy_version", "backend_version"]),
        ]

    def __str__(self):
        return (
            f"TenDBHA - Proxy:{self.proxy_count}({self.proxy_version}) "
            f"Backend:{self.backend_master_count}M+{self.backend_slave_count}S({self.backend_version}) "
            f"- {self.concurrent_threads}{_('线程')}"
        )


class TenDBClusterBenchmark(AuditedModel):
    """
    TenDBCluster 性能基准测试结果表
    集群结构：Spider（多个）+ 分片（多个，每个分片是 1 Master + 1 Slave）
    注意：不同组件类型使用不同的主机配置（Spider 和 Remote 可以用不同机型）
    """

    # Spider 配置
    spider_host_config = models.ForeignKey(
        BenchmarkHostConfig,
        on_delete=models.CASCADE,
        related_name="tendbcluster_spider_benchmarks",
        help_text=_("Spider 主机配置"),
    )
    spider_version = models.CharField(_("Spider版本"), max_length=LEN_NORMAL, help_text=_("Spider版本号"))
    spider_count = models.IntegerField(_("Spider数量"), help_text=_("Spider节点数量"))

    # Remote（分片）配置
    remote_host_config = models.ForeignKey(
        BenchmarkHostConfig,
        on_delete=models.CASCADE,
        related_name="tendbcluster_remote_benchmarks",
        help_text=_("Remote 主机配置"),
    )
    remote_version = models.CharField(_("Remote版本"), max_length=LEN_NORMAL, help_text=_("Remote（MySQL）版本"))
    shard_count = models.IntegerField(_("分片数量"), help_text=_("分片数量，每个分片包含 1 Master + 1 Slave"))

    # 压测配置
    stress_test_tool = models.CharField(
        _("压测工具"), max_length=LEN_NORMAL, null=True, blank=True, help_text=_("压测工具名称，如 sysbench, tpcc")
    )
    stress_test_tool_version = models.CharField(
        _("压测工具版本"), max_length=LEN_NORMAL, null=True, blank=True, help_text=_("压测工具版本号")
    )
    concurrent_threads = models.IntegerField(_("并发线程数"), help_text=_("并发线程数"))
    loaded_data_volume_gb = models.IntegerField(
        _("预导入数据量(GB)"), null=True, blank=True, help_text=_("压测前预先导入到集群的数据量，单位GB")
    )
    loaded_data_volume_rows = models.BigIntegerField(
        _("预导入数据量(行数)"), null=True, blank=True, help_text=_("压测前预先导入到集群的数据行数")
    )
    read_write_ratio = models.CharField(
        _("读写比例"), max_length=LEN_SHORT, null=True, blank=True, help_text=_("读写比例，如 读写8/2")
    )

    # 压测结果（整体性能指标）
    avg_qps = models.IntegerField(_("平均QPS"), null=True, blank=True, help_text=_("平均QPS（Queries Per Second）"))
    avg_tps = models.FloatField(_("平均TPS"), null=True, blank=True, help_text=_("平均TPS（Transactions Per Second）"))
    avg_latency_ms = models.FloatField(_("平均耗时(ms)"), null=True, blank=True, help_text=_("平均耗时，单位毫秒"))
    p95_latency_ms = models.FloatField(_("95%平均耗时(ms)"), null=True, blank=True, help_text=_("95%平均耗时，单位毫秒"))

    # Spider 资源使用率
    spider_io_usage_rate = models.FloatField(
        _("Spider IO使用率(%)"), null=True, blank=True, help_text=_("Spider IO使用率，百分比，0-100")
    )
    spider_cpu_usage_rate = models.FloatField(
        _("Spider CPU使用率(%)"), null=True, blank=True, help_text=_("Spider CPU使用率，百分比，0-100")
    )

    # Remote 资源使用率
    remote_io_usage_rate = models.FloatField(
        _("Remote IO使用率(%)"), null=True, blank=True, help_text=_("Remote IO使用率，百分比，0-100")
    )
    remote_cpu_usage_rate = models.FloatField(
        _("Remote CPU使用率(%)"), null=True, blank=True, help_text=_("Remote CPU使用率，百分比，0-100")
    )

    class Meta(AuditedModel.Meta):
        verbose_name = _("TenDBCluster性能基准测试结果")
        verbose_name_plural = _("TenDBCluster性能基准测试结果")
        unique_together = (
            "spider_host_config",
            "remote_host_config",
            "spider_version",
            "remote_version",
            "spider_count",
            "shard_count",
            "concurrent_threads",
            "read_write_ratio",
        )
        ordering = ["spider_host_config", "remote_host_config", "concurrent_threads"]
        indexes = [
            # Spider 配置查询
            models.Index(fields=["spider_host_config"]),
            models.Index(fields=["spider_version"]),
            models.Index(fields=["spider_count"]),
            # Remote 配置查询
            models.Index(fields=["remote_host_config"]),
            models.Index(fields=["remote_version"]),
            models.Index(fields=["shard_count"]),
            # 性能范围查询
            models.Index(fields=["concurrent_threads"]),
            models.Index(fields=["avg_qps"]),
            # 组合查询
            models.Index(
                fields=["spider_host_config", "remote_host_config", "spider_version", "remote_version", "shard_count"]
            ),
        ]

    def __str__(self):
        return (
            f"TenDBCluster - Spider:{self.spider_count}({self.spider_version}) "
            f"Shard:{self.shard_count}({self.remote_version}) "
            f"- {self.concurrent_threads}{_('线程')}"
        )
