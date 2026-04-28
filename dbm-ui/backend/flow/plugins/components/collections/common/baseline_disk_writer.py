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
from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.flow.plugins.components.collections.common.base_service import BaseService


class BaselineDiskWriteService(BaseService):
    """
    把 dbactuator os disk-benchmark 的输出按 disk_name 写入 BaselineDisk 表

    上游必须是一个 ExecuteDBActuatorScriptComponent (write_payload_var="benchmark_result"),
    它会把 actuator 的 <ctx>...</ctx> JSON 解析后写入 trans_data.benchmark_result

    本 act 的 kwargs (来自 flow):
        disk_name    : (必填) BaselineDisk 唯一键, 决定 update_or_create
        disk_type    : 磁盘类型枚举值, 如 NVME_SSD; 缺失时不更新该字段
        disk_model   : 磁盘型号, 如 3570; 缺失时不更新
        is_local     : 是否本地盘, 缺失时不更新
        capacity_gb  : 单盘容量 GB; 缺失时回落 actuator 上报的 environment.capacity_gb
    """

    def _execute(self, data, parent_data) -> bool:
        # 延迟导入: dbm_aiagent app 只在 ENABLE_DBM_AI=true 时进入 INSTALLED_APPS,
        # 顶层 import 会让 ENABLE_DBM_AI=false 的环境也跑不起来
        from backend.dbm_aiagent.models import BaselineDisk

        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")

        disk_name = kwargs.get("disk_name")
        if not disk_name:
            self.log_error(_("disk_name 为空, 无法写入 BaselineDisk"))
            return False

        result = getattr(trans_data, "benchmark_result", None) if trans_data is not None else None
        if not isinstance(result, dict):
            self.log_error(_("从 trans_data.benchmark_result 没拿到 actuator 输出, 无法写入 BaselineDisk"))
            return False

        # 5 个性能字段, 严格对齐 actuator 输出 + BaselineDisk 字段
        defaults = {
            "performance_iops": int(result.get("performance_iops", 0) or 0),
            "performance_throughput_mbps": int(result.get("performance_throughput_mbps", 0) or 0),
            "sequential_write_throughput_mbps": int(result.get("sequential_write_throughput_mbps", 0) or 0),
            "random_read_iops": int(result.get("random_read_iops", 0) or 0),
            "write_latency_ms": float(result.get("write_latency_ms", 0.0) or 0.0),
        }

        # 元数据字段, 优先 flow 入参, 缺失时 fallback environment
        env = result.get("environment") or {}
        if kwargs.get("disk_type"):
            defaults["disk_type"] = kwargs["disk_type"]
        if kwargs.get("disk_model"):
            defaults["disk_model"] = kwargs["disk_model"]
        elif env.get("disk_model"):
            defaults["disk_model"] = env["disk_model"]
        if "is_local" in kwargs and kwargs["is_local"] is not None:
            defaults["is_local"] = bool(kwargs["is_local"])
        if kwargs.get("capacity_gb"):
            defaults["capacity_gb"] = int(kwargs["capacity_gb"])
        elif env.get("capacity_gb"):
            try:
                defaults["capacity_gb"] = int(round(float(env["capacity_gb"])))
            except (TypeError, ValueError):
                pass

        obj, created = BaselineDisk.objects.update_or_create(disk_name=disk_name, defaults=defaults)
        verb = _("新建") if created else _("更新")
        self.log_info(
            _(
                "BaselineDisk {} 完成: disk_name={}, iops={}, throughput={}MB/s, seq_write={}MB/s, "
                "random_read_iops={}, write_latency={}ms"
            ).format(
                verb,
                disk_name,
                defaults["performance_iops"],
                defaults["performance_throughput_mbps"],
                defaults["sequential_write_throughput_mbps"],
                defaults["random_read_iops"],
                defaults["write_latency_ms"],
            )
        )
        return True


class BaselineDiskWriteComponent(Component):
    name = _("基线磁盘性能数据写入")
    code = "baseline_disk_write"
    bound_service = BaselineDiskWriteService
