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
from typing import Dict, Optional

from django.utils.translation import gettext as _

from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.plugins.components.collections.common.fake_log import FakeLogComponent


class FakeLogFlow:
    """日志模拟测试流程，不执行远程命令。"""

    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data or {}

    def fake_log_flow(self):
        pipeline = Builder(root_id=self.root_id, data=self.data)
        pipeline.add_act(
            act_name=_("模拟日志打印"),
            act_component_code=FakeLogComponent.code,
            kwargs={
                "log_size_mb": self.data.get("log_size_mb", 1),
                "message": self.data.get("message", _("模拟日志")),
            },
        )
        pipeline.add_act(
            act_name=_("失败但有日志"),
            act_component_code=FakeLogComponent.code,
            kwargs={
                "log_size_mb": self.data.get("log_size_mb", 1),
                "message": self.data.get("fail_message", _("失败模拟日志")),
                "is_fail": True,
            },
            # 前置失败节点需忽略错误，否则后续节点不会被执行
            error_ignorable=True,
        )
        pipeline.add_act(
            act_name=_("失败但有日志"),
            act_component_code=FakeLogComponent.code,
            kwargs={
                "log_size_mb": self.data.get("log_size_mb", 1),
                "message": self.data.get("fail_message", _("失败模拟日志")),
                "is_fail": True,
                "running": True,
            },
        )
        pipeline.run_pipeline()
