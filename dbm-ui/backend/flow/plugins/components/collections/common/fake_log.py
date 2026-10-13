# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import time
from typing import List

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend.flow.plugins.components.collections.common.base_service import BaseService

BYTES_PER_MB = 1024 * 1024


class FakeLogService(BaseService):
    """日志模拟测试组件，仅写入流程日志，不依赖外部服务。"""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs") or {}
        # 按日志大小(MB)决定输出多少条日志，1MB = 1024 * 1024 字节
        log_size_mb = float(kwargs.get("log_size_mb") or 1)
        message = kwargs.get("message") or _("模拟日志")
        is_fail = bool(kwargs.get("is_fail", False))
        running = bool(kwargs.get("running", False))
        node_type = _("失败节点") if is_fail else _("成功节点")

        target_bytes = int(log_size_mb * BYTES_PER_MB)
        written_bytes = 0
        log_count = 0

        self.log_info(_("开始输出模拟日志，目标大小：{}MB").format(log_size_mb))
        # 按实际写入的字节数累加，直到达到目标大小
        while written_bytes < target_bytes:
            log_count += 1
            log_line = _("[{}] {}").format(log_count, message)
            if running:
                time.sleep(0.1)
            self.log_info(log_line)
            written_bytes += len(log_line.encode("utf-8"))

        if is_fail:
            self.log_error(_("[{}] 模拟日志输出完成，节点返回失败").format(node_type))
            return False

        self.log_info(_("模拟日志输出完成，共输出 {} 条日志，约 {:.2f}MB").format(log_count, written_bytes / BYTES_PER_MB))
        data.outputs["log_count"] = log_count
        data.outputs["log_size_mb"] = round(written_bytes / BYTES_PER_MB, 2)
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]

    def outputs_format(self) -> List:
        return [
            Service.OutputItem(name="log_count", key="log_count", type="int"),
            Service.OutputItem(name="log_size_mb", key="log_size_mb", type="float"),
            Service.OutputItem(name="is_fail", key="is_fail", type="bool"),
        ]


class FakeLogComponent(Component):
    name = _("模拟日志打印")
    code = "fake_log"
    bound_service = FakeLogService
