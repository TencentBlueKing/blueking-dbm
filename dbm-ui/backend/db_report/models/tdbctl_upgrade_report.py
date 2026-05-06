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

from backend.bk_web.models import AuditedModel
from backend.db_report.enums import TdbctlInstanceRole, TdbctlUpgradeStatus


class TdbctlUpgradeRecord(AuditedModel):
    """
    tdbctl 升级记录表 - 实例级别（每个实例只保留一条记录）

    用于记录平台所有 TenDBCluster 集群的 tdbctl 中控升级情况，
    支持全局调度升级任务和追踪升级进度。

    记录更新策略：
    - 使用 update_or_create() 方法，按 (ip, port) 唯一标识更新记录
    - 每次升级时将历史信息追加到 upgrade_history 列表
    - upgrade_count 累计升级次数
    """

    # 业务信息
    bk_biz_id = models.IntegerField(default=0, help_text=_("业务ID"))
    bk_cloud_id = models.IntegerField(default=0, help_text=_("云区域ID"))

    # 集群信息
    cluster_id = models.IntegerField(default=0, help_text=_("集群ID"))
    cluster_domain = models.CharField(max_length=255, default="", help_text=_("集群域名"))

    # 实例信息（ip + port 作为唯一标识）
    ip = models.GenericIPAddressField(help_text=_("tdbctl实例IP"))
    port = models.IntegerField(help_text=_("tdbctl实例端口"))
    spider_port = models.IntegerField(default=0, help_text=_("对应的spider端口"))
    instance_role = models.CharField(
        max_length=32,
        choices=TdbctlInstanceRole.get_choices(),
        default=TdbctlInstanceRole.SECONDARY.value,
        help_text=_("实例角色:primary/secondary"),
    )

    # 版本信息（当前最新状态）
    current_version = models.CharField(max_length=128, default="", help_text=_("升级前版本"))
    target_version = models.CharField(max_length=128, default="", help_text=_("目标版本"))
    upgraded_version = models.CharField(max_length=128, default="", help_text=_("实际升级后版本"))

    # 升级状态（当前最新状态）
    status = models.CharField(
        max_length=32,
        choices=TdbctlUpgradeStatus.get_choices(),
        default=TdbctlUpgradeStatus.PENDING.value,
        help_text=_("升级状态"),
    )

    # 关联信息
    task_id = models.CharField(max_length=128, default="", help_text=_("关联的flow任务ID"))
    pkg_id = models.IntegerField(default=0, help_text=_("升级包ID"))
    error_msg = models.TextField(default="", help_text=_("错误信息"))
    batch_id = models.CharField(max_length=128, default="", help_text=_("批次ID"))

    # 升级历史记录（JSON格式存储历史变化）
    # 格式示例：[
    #   {"time": "2025-01-01 10:00:00", "from_version": "2.4.11", "to_version": "2.4.12",
    #    "status": "success", "task_id": "xxx", "operator": "admin"},
    #   {"time": "2025-02-01 10:00:00", "from_version": "2.4.12", "to_version": "2.5.0",
    #    "status": "failed", "task_id": "yyy", "error_msg": "xxx", "operator": "admin"}
    # ]
    upgrade_history = models.JSONField(default=list, help_text=_("升级历史记录"))

    # 升级次数统计
    upgrade_count = models.IntegerField(default=0, help_text=_("累计升级次数"))

    class Meta:
        # 唯一约束：每个实例只保留一条记录
        unique_together = [["ip", "port"]]
        indexes = [
            models.Index(fields=["cluster_id", "status"]),
            models.Index(fields=["bk_biz_id", "status"]),
            models.Index(fields=["status", "target_version"]),
        ]
        verbose_name = _("tdbctl升级记录")
        verbose_name_plural = _("tdbctl升级记录")

    def __str__(self):
        return f"{self.ip}:{self.port} - {self.status}"

    def append_history(
        self, from_version: str, to_version: str, status: str, task_id: str, operator: str, error_msg: str = ""
    ):
        """
        追加升级历史记录

        @param from_version: 升级前版本
        @param to_version: 目标版本
        @param status: 升级状态
        @param task_id: 任务ID
        @param operator: 操作人
        @param error_msg: 错误信息（可选）
        """
        from django.utils import timezone

        history_entry = {
            "time": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
            "from_version": from_version,
            "to_version": to_version,
            "status": status,
            "task_id": task_id,
            "operator": operator,
        }
        if error_msg:
            history_entry["error_msg"] = error_msg

        if self.upgrade_history is None:
            self.upgrade_history = []
        self.upgrade_history.append(history_entry)

    @classmethod
    def need_upgrade(cls, instance_ip: str, instance_port: int, target_version: str) -> bool:
        """
        判断实例是否需要升级

        @param instance_ip: 实例IP
        @param instance_port: 实例端口
        @param target_version: 目标版本
        @return: True 表示需要升级，False 表示不需要
        """
        try:
            record = cls.objects.get(ip=instance_ip, port=instance_port)
        except cls.DoesNotExist:
            return True  # 无记录，需要升级

        if record.status == TdbctlUpgradeStatus.SUCCESS.value and record.target_version == target_version:
            return False  # 已成功升级到目标版本

        if record.status == TdbctlUpgradeStatus.RUNNING.value:
            return False  # 正在升级中

        return True  # 其他情况需要升级

    @classmethod
    def get_upgrade_progress(cls, bk_biz_id: int = None, target_version: str = None) -> dict:
        """
        获取升级进度统计

        @param bk_biz_id: 业务ID（可选，不传则统计全部）
        @param target_version: 目标版本（可选）
        @return: 进度统计信息
        """
        queryset = cls.objects.all()
        if bk_biz_id:
            queryset = queryset.filter(bk_biz_id=bk_biz_id)
        if target_version:
            queryset = queryset.filter(target_version=target_version)

        total = queryset.count()
        pending = queryset.filter(status=TdbctlUpgradeStatus.PENDING.value).count()
        running = queryset.filter(status=TdbctlUpgradeStatus.RUNNING.value).count()
        success = queryset.filter(status=TdbctlUpgradeStatus.SUCCESS.value).count()
        failed = queryset.filter(status=TdbctlUpgradeStatus.FAILED.value).count()
        skipped = queryset.filter(status=TdbctlUpgradeStatus.SKIPPED.value).count()

        return {
            "total": total,
            "pending": pending,
            "running": running,
            "success": success,
            "failed": failed,
            "skipped": skipped,
        }
