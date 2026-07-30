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
import logging
from typing import Dict, Optional

from bamboo_engine.builder import SubProcess
from django.utils.translation import gettext as _

from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.plugins.components.collections.common.check_resolv_conf import ExecuteShellScriptComponent
from backend.flow.plugins.components.collections.common.empty_node import EmptyNodeComponent
from backend.flow.plugins.components.collections.common.pause import PauseComponent
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

    def __build_second_level_sub_flow(self, flow_name: str, with_pause: bool = True) -> SubProcess:
        """
        构建第二层子流程：并行网关执行到一半插入待继续节点，用于测试并行分支下的人工确认
        @param flow_name: 子流程名称
        @param with_pause: 并行网关中是否挂载待继续节点
        """
        sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
        sub_pipeline.add_act(
            act_name=_("{}-前置检查").format(flow_name),
            act_component_code=EmptyNodeComponent.code,
            kwargs={},
        )
        # 并行网关的分支中混入待继续节点，网关只有在人工继续后才能汇聚
        parallel_acts = [
            {
                "act_name": _("{}-并行-{}").format(flow_name, index),
                "act_component_code": FakeSemanticCheckComponent.code,
                "kwargs": {"parallel_acts": "1"},
            }
            for index in range(2)
        ]
        if with_pause:
            parallel_acts.insert(
                1,
                {
                    "act_name": _("{}-并行待继续").format(flow_name),
                    "act_component_code": PauseComponent.code,
                    "kwargs": {},
                    "retryable": False,
                    "skippable": False,
                },
            )
        sub_pipeline.add_parallel_acts(acts_list=parallel_acts)
        sub_pipeline.add_act(
            act_name=_("{}-收尾").format(flow_name),
            act_component_code=EmptyNodeComponent.code,
            kwargs={},
        )
        return sub_pipeline.build_sub_process(sub_name=flow_name)

    def __build_first_level_sub_flow(self, flow_name: str) -> SubProcess:
        """
        构建第一层子流程：串行节点 + 并行网关 + 并行嵌套第二层子流程
        @param flow_name: 子流程名称
        """
        sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
        sub_pipeline.add_act(
            act_name=_("{}-初始化").format(flow_name),
            act_component_code=EmptyNodeComponent.code,
            kwargs={},
        )
        # 并行网关中同时挂载普通活动节点和第二层子流程
        sub_pipeline.add_parallel_acts(
            acts_list=[
                {
                    "act_name": _("{}-并行-{}").format(flow_name, index),
                    "act_component_code": FakeSemanticCheckComponent.code,
                    "kwargs": {"parallel_acts": "1"},
                }
                for index in range(2)
            ]
            + [self.__build_second_level_sub_flow(flow_name=_("{}-并行子流程").format(flow_name))]
        )
        # 串行的待继续节点，人工继续后才进入下一批并行子流程
        sub_pipeline.add_act(
            act_name=_("{}-串行待继续").format(flow_name),
            act_component_code=PauseComponent.code,
            kwargs={},
            retryable=False,
            skippable=False,
        )
        sub_pipeline.add_parallel_sub_pipeline(
            sub_flow_list=[
                self.__build_second_level_sub_flow(flow_name=_("{}-二层子流程-1").format(flow_name)),
                self.__build_second_level_sub_flow(flow_name=_("{}-二层子流程-2").format(flow_name), with_pause=False),
            ]
        )
        sub_pipeline.add_act(
            act_name=_("{}-收尾").format(flow_name),
            act_component_code=EmptyNodeComponent.code,
            kwargs={},
        )
        return sub_pipeline.build_sub_process(sub_name=flow_name)

    def fake_semantic_check(self):
        """
        模拟执行SQL语义检查的任务编排
        """

        fake_semantic_check = Builder(root_id=self.root_id, data=self.data)
        fake_semantic_check.add_act(
            **{
                "act_name": _("执行自定义命令"),
                "act_component_code": ExecuteShellScriptComponent.code,
                "kwargs": self.data["params"],
            }
        )
        fake_semantic_check.add_act(
            act_name=_("串行1"), act_component_code=FakeSemanticCheckComponent.code, kwargs={}, skippable=False
        )
        fake_semantic_check.add_act(act_name=_("串行2"), act_component_code=FakeSemanticCheckComponent.code, kwargs={})
        fake_semantic_check.add_act(act_name=_("串行3"), act_component_code=FakeSemanticCheckComponent.code, kwargs={})
        parallel_num = 2
        parallel_acts = [
            {
                "act_name": _("并行-{}").format(index),
                "act_component_code": FakeSemanticCheckComponent.code,
                "kwargs": {"parallel_acts": "1"},
            }
            for index in range(parallel_num)
        ]
        fake_semantic_check.add_parallel_acts(acts_list=parallel_acts)
        fake_semantic_check.add_act(act_name=_("串行5"), act_component_code=FakeSemanticCheckComponent.code, kwargs={})
        # 并行两个一级子流程，每个一级子流程内部再嵌套二级子流程
        fake_semantic_check.add_parallel_sub_pipeline(
            sub_flow_list=[
                self.__build_first_level_sub_flow(flow_name=_("一级子流程-A")),
                self.__build_first_level_sub_flow(flow_name=_("一级子流程-B")),
            ]
        )
        # 串行嵌入一个一级子流程，验证子流程串行编排
        fake_semantic_check.add_sub_pipeline(sub_flow=self.__build_first_level_sub_flow(flow_name=_("一级子流程-C")))
        parallel2_acts = [
            {
                "act_name": _("并行2-1"),
                "act_component_code": PauseComponent.code,
                "kwargs": {"parallel_acts": "1"},
                "retryable": False,
                "skippable": False,
            },
            {
                "act_name": _("错误并行2-2"),
                "act_component_code": PauseComponent.code,
                "kwargs": {"is_error": True},
            },
        ]
        fake_semantic_check.add_parallel_acts(acts_list=parallel2_acts)
        fake_semantic_check.add_act(act_name=_("串行结束"), act_component_code=FakeSemanticCheckComponent.code, kwargs={})
        fake_semantic_check.run_pipeline()
