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

from backend.bk_web.constants import LEN_MIDDLE, LEN_NORMAL, LEN_SHORT
from backend.bk_web.models import AuditedModel


class DiskType(models.TextChoices):
    """
    磁盘类型枚举
    """

    # 本地盘类型
    NVME_SSD = "NVME_SSD", _("NVMe SSD 硬盘")
    SATA_SSD = "SATA_SSD", _("SATA SSD 硬盘")
    SAS = "SAS", _("SAS 硬盘")
    HDD = "HDD", _("HDD 机械硬盘")
    # 腾讯云硬盘类型
    TENCENT_CLOUD_PREMIUM = "CLOUD_PREMIUM", _("高性能云硬盘")
    TENCENT_CLOUD_BSSD = "CLOUD_BSSD", _("通用型SSD云硬盘")
    TENCENT_CLOUD_SSD = "CLOUD_SSD", _("SSD云硬盘")
    TENCENT_CLOUD_HSSD = "CLOUD_HSSD", _("增强型SSD云硬盘")
    TENCENT_CLOUD_TSSD = "CLOUD_TSSD", _("极速型SSD云硬盘")


class BaselineHost(AuditedModel):
    """
    基线主机配置表
    用于记录真实物理主机的硬件配置和性能参数作为基准数据，如 ITA3.4XLARGE64-p2w 等实际机型
    """

    device_class = models.CharField(
        _("机型编码"), max_length=LEN_MIDDLE, unique=True, help_text=_("机型的唯一编码，如 ITA3.4XLARGE64-p2w")
    )
    spec_type = models.CharField(_("机型系列"), max_length=LEN_NORMAL, default="", help_text=_("机型所属的系列类型，如 高IO型ITA3"))
    cpu_model = models.CharField(_("CPU型号"), max_length=LEN_NORMAL, default="", help_text=_("CPU型号，如 AMD EPYC 7K83"))
    cpu_frequency_ghz = models.FloatField(
        _("CPU主频(GHz)"), null=True, blank=True, help_text=_("CPU主频或全核睿频，单位GHz，如 2.55")
    )
    network_card_speed = models.CharField(
        _("网卡速度"), max_length=LEN_SHORT, null=True, blank=True, help_text=_("网卡速度，如 100G")
    )
    vcpu = models.IntegerField(_("vCPU数量"), help_text=_("虚拟CPU核心数量"))
    memory_gb = models.IntegerField(_("内存大小(GB)"), help_text=_("内存大小，单位GB"))
    max_connections_w = models.IntegerField(
        _("最大连接数(万)"), null=True, blank=True, help_text=_("最大连接数，单位万，如 110 (表示110万)")
    )
    network_pps_w = models.IntegerField(
        _("网络收发包(万pps)"), null=True, blank=True, help_text=_("网络每秒收发包数量，单位万pps，如 130 (表示130万pps)")
    )
    intranet_bandwidth_gbps = models.FloatField(_("内网带宽能力(Gbps)"), null=True, blank=True, help_text=_("内网带宽能力，单位Gbps"))
    queue_count = models.IntegerField(_("队列数"), null=True, blank=True, help_text=_("主机硬件队列数量"))
    remarks = models.TextField(_("备注"), blank=True, null=True, help_text=_("其他非结构化的备注信息"))

    class Meta(AuditedModel.Meta):
        verbose_name = _("基线主机配置")
        verbose_name_plural = _("基线主机配置")
        ordering = ["device_class"]
        indexes = [
            models.Index(fields=["spec_type", "cpu_model"]),
        ]

    def __str__(self):
        return self.device_class


class BaselineDisk(AuditedModel):
    """
    基线磁盘配置表（独立基准数据）
    用于记录磁盘的硬件规格和性能数据作为基准数据，不与主机配置强绑定
    """

    disk_name = models.CharField(
        _("磁盘配置名称"), max_length=LEN_MIDDLE, unique=True, help_text=_("磁盘配置的唯一名称，如 NVMe_SSD_3570")
    )
    disk_type = models.CharField(
        _("磁盘类型"), max_length=LEN_SHORT, choices=DiskType.choices, help_text=_("磁盘类型，如 NVMe SSD")
    )
    disk_model = models.CharField(_("磁盘型号"), max_length=LEN_NORMAL, help_text=_("磁盘型号或系列编码，如 3570"))
    is_local = models.BooleanField(_("是否本地盘"), default=True, help_text=_("指示磁盘是否为本地盘"))
    capacity_gb = models.IntegerField(_("单盘容量(GB)"), null=True, blank=True, help_text=_("单块磁盘的容量大小，如 3570"))
    performance_iops = models.IntegerField(_("性能IOPS"), null=True, blank=True, help_text=_("磁盘的平均IOPS性能指标"))
    performance_throughput_mbps = models.IntegerField(
        _("性能吞吐(MB/s)"), null=True, blank=True, help_text=_("磁盘的平均吞吐量性能指标(MB/s)")
    )
    sequential_write_throughput_mbps = models.IntegerField(
        _("顺序写吞吐(MB/s)"), null=True, blank=True, help_text=_("磁盘的顺序写吞吐量性能指标(MB/s)")
    )
    random_read_iops = models.IntegerField(_("随机读IOPS"), null=True, blank=True, help_text=_("磁盘的随机读IOPS性能指标"))
    write_latency_ms = models.FloatField(_("写延迟(ms)"), null=True, blank=True, help_text=_("磁盘的写延迟性能指标，单位毫秒"))

    class Meta(AuditedModel.Meta):
        verbose_name = _("基线磁盘配置")
        verbose_name_plural = _("基线磁盘配置")
        ordering = ["disk_type", "disk_model"]
        indexes = [
            models.Index(fields=["disk_type"]),
            models.Index(fields=["disk_model"]),
        ]

    def __str__(self):
        return f"{self.disk_name} - {self.get_disk_type_display()}"
