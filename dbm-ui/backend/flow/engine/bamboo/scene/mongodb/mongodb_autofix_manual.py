# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

MongoDB 自愈人工处理 Flow：无自动修复动作；审批/确认后空节点成功，供人工跟踪结案。
"""
import logging
from typing import Dict, Optional

from django.utils.translation import gettext as _

from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.plugins.components.collections.common.empty_node import EmptyNodeComponent

logger = logging.getLogger("flow")


class MongoAutofixManualFlow:
    """自愈人工处理：记录原因并空跑成功（不自动 replace / ensure / fix）。"""

    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data or {}

    def run(self):
        infos = self.data.get("infos") or []
        reasons = []
        for info in infos:
            reasons.append(
                "{} {}:{} confirm={}".format(
                    info.get("immute_domain") or "",
                    info.get("ip"),
                    info.get("port") or (info.get("ports") or ["-"])[0],
                    info.get("confirm_result") or info.get("reason") or "",
                )
            )
        logger.info("mongo autofix manual ticket uid=%s reasons=%s", self.data.get("uid"), reasons)

        pipeline = Builder(root_id=self.root_id, data=self.data)
        pipeline.add_act(
            act_name=_("MongoDB-自愈人工处理确认({})").format("; ".join(reasons)[:120] or "-"),
            act_component_code=EmptyNodeComponent.code,
            kwargs={},
        )
        pipeline.run_pipeline()
