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
import logging
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.plugins.components.collections.mysql.fake_semantic_check import FakeSemanticCheckComponent

logger = logging.getLogger("flow")


class MySQLFakeSemanticCheck(object):
    """
    模拟执行SQL语义检查，仅用作测试
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        :param root_id : 任务流程定义的root_id
        :param data : 单据传递参数
        """

        self.root_id = root_id
        self.data = data

    def fake_semantic_check(self):
        """
        模拟执行SQL语义检查的任务编排
        """

        fake_semantic_check = Builder(root_id=self.root_id, data=self.data)
        fake_semantic_check.add_act(act_name=_("串行1"), act_component_code=FakeSemanticCheckComponent.code, kwargs={})
        fake_semantic_check.add_act(act_name=_("串行2"), act_component_code=FakeSemanticCheckComponent.code, kwargs={})
        fake_semantic_check.add_act(act_name=_("串行3"), act_component_code=FakeSemanticCheckComponent.code, kwargs={})

        parallel_acts = [
            {
                "act_name": _("并行1"),
                "act_component_code": FakeSemanticCheckComponent.code,
                "kwargs": {},
            },
            {
                "act_name": _("并行2"),
                "act_component_code": FakeSemanticCheckComponent.code,
                "kwargs": {},
            },
            {
                "act_name": _("错误并行3"),
                "act_component_code": FakeSemanticCheckComponent.code,
                "kwargs": {"is_error": True},
            },
        ]
        fake_semantic_check.add_parallel_acts(acts_list=parallel_acts)

        fake_semantic_check.add_act(act_name=_("串行结束"), act_component_code=FakeSemanticCheckComponent.code, kwargs={})

        fake_semantic_check.run_pipeline()
