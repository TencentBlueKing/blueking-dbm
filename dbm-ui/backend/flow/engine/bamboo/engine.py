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
from typing import Any, Dict, List, Optional

from bamboo_engine import api, builder, states
from bamboo_engine.api import EngineAPIResult
from bamboo_engine.builder import Data
from django.utils.translation import ugettext as _
from pipeline.eri.runtime import BambooDjangoRuntime

from backend.flow.engine.bamboo.builder import Builder
from backend.flow.engine.exceptions import PipelineError
from backend.flow.models import FlowNode, FlowTree, StateType
from backend.utils.string import i18n_str
from backend.utils.time import datetime2timestamp

logger = logging.getLogger("json")


class BambooEngine:
    builder_cls = Builder

    def __init__(self, root_id: str, data: Optional[Dict] = None, pipeline_data: Optional[Data] = None):
        self.builder = self.builder_cls(root_id, data, pipeline_data=pipeline_data)
        self.runtime = BambooDjangoRuntime()
        self.root_id = root_id
        self.data = data

    def run(self, pipeline_data: Optional[Data] = None) -> Optional[EngineAPIResult]:
        """
        开始运行 pipeline
        """
        start = self.builder.build_tree()
        if not start:
            return None
        pipeline = builder.build_tree(start_elem=start, id=self.root_id, data=pipeline_data)
        pipeline_copy = copy.deepcopy(pipeline)
        insensitive_data = self.hide_sensitive_data(pipeline_copy)
        # 考虑到有些任务没有单据关联，因此uid一般为root_id，此时创建FlowTree的时候uid应该为null
        uid = self.data.get("uid") if isinstance(self.data.get("uid"), int) else None
        tree = FlowTree.objects.create(
            uid=uid,
            ticket_type=self.data["ticket_type"],
            root_id=self.root_id,
            tree=insensitive_data,
            bk_biz_id=self.data["bk_biz_id"],
            status=StateType.CREATED,
            created_by=self.data["created_by"],
        )
        tree.save()
        result = api.run_pipeline(runtime=self.runtime, pipeline=pipeline)
        return result

    def pause_pipeline(self) -> EngineAPIResult:
        """
        暂停 pipeline 的执行
        """
        result = api.pause_pipeline(runtime=BambooDjangoRuntime(), pipeline_id=self.root_id)
        return result

    def resume_pipeline(self) -> EngineAPIResult:
        result = api.resume_pipeline(runtime=BambooDjangoRuntime(), pipeline_id=self.root_id)
        return result

    def revoke_pipeline(self) -> EngineAPIResult:
        result = api.revoke_pipeline(runtime=BambooDjangoRuntime(), pipeline_id=self.root_id)
        return result

    def force_fail_pipeline(self, node_id: str) -> EngineAPIResult:
        result = api.forced_fail_activity(runtime=BambooDjangoRuntime(), node_id=node_id, ex_data="force failed")
        return result

    def retry_node(self, node_id: str, data: Optional[dict] = None) -> EngineAPIResult:
        result = api.retry_node(runtime=BambooDjangoRuntime(), node_id=node_id, data=data)
        return result

    def skip_node(self, node_id: str) -> EngineAPIResult:
        result = api.skip_node(runtime=BambooDjangoRuntime(), node_id=node_id)
        return result

    def force_fail_node(self, node_id: str, ex_data: str) -> EngineAPIResult:
        result = api.forced_fail_activity(runtime=BambooDjangoRuntime(), node_id=node_id, ex_data=ex_data)
        return result

    def get_node_input_data(self, node_id: str) -> EngineAPIResult:
        result = api.get_execution_data_inputs(runtime=BambooDjangoRuntime(), node_id=node_id)
        return result

    def get_node_histories(self, node_id: str) -> EngineAPIResult:
        result = api.get_node_histories(runtime=BambooDjangoRuntime(), node_id=node_id)
        return result

    def get_pipeline_states(self) -> EngineAPIResult:
        result = api.get_pipeline_states(runtime=BambooDjangoRuntime(), root_id=self.root_id)
        self.format_bamboo_engine_status(result.data)
        return result

    def get_children_states(self, node_id: str) -> EngineAPIResult:
        result = api.get_children_states(runtime=BambooDjangoRuntime(), node_id=node_id)
        return result

    def get_execution_data(self, node_id: str) -> EngineAPIResult:
        result = api.get_execution_data(runtime=BambooDjangoRuntime(), node_id=node_id)
        return result

    def format_bamboo_engine_status(self, pipeline_status_tree: Dict[str, Any]):
        """
        递归获取子流程的状态，转换通过 bamboo engine api 获取的任务状态格式
        :param pipeline_status_tree: 状态流程树
        """
        for __, status_tree in pipeline_status_tree.items():

            if not status_tree.get("children"):
                continue

            self.format_bamboo_engine_status(status_tree["children"])
            child_status = set([child_tree["state"] for _, child_tree in status_tree["children"].items()])

            if status_tree["state"] == StateType.RUNNING:
                if StateType.FAILED in child_status:
                    status_tree["state"] = StateType.FAILED
                elif StateType.REVOKED in child_status:
                    status_tree["state"] = StateType.REVOKED
                elif StateType.SUSPENDED in child_status:
                    status_tree["state"] = StateType.SUSPENDED

    def hide_sensitive_data(self, copy_data: Dict):
        """隐藏pipeline中敏感数据"""
        for key, value in list(copy_data.items()):
            if key == "inputs":
                copy_data.pop(key)
                continue
            if type(value) == dict:
                self.hide_sensitive_data(value)
        return copy_data

    def get_subprocess_state(self, children: Dict, children_status: List):
        """获取指定子流程结点状态"""
        for key, __ in children.items():
            children_status.append(children[key]["state"])

    def recursion_subprocess_status(self, activities: Dict, node_maps: Dict):
        """为子流程添加状态"""
        raw_data = copy.deepcopy(activities)
        for node_id, activity in raw_data.items():
            for key, value in activity.items():
                if value == "SubProcess":
                    children_status_list = []
                    children_states = self.get_children_states(node_id=node_id).data
                    try:
                        children = children_states[node_id]["children"]
                        self.get_subprocess_state(children, children_status_list)
                        status = children_states[node_id]["state"]
                        if status == states.RUNNING and states.FAILED in children_status_list:
                            status = states.FAILED
                        elif status == states.RUNNING and states.REVOKED in children_status_list:
                            status = states.REVOKED
                    except KeyError:
                        status = states.CREATED

                    act_status = []
                    self.recursion_subprocess_activity_status(
                        self.root_id, activity["pipeline"]["activities"], act_status, node_maps
                    )
                    if states.FAILED in act_status:
                        status = states.FAILED
                    elif states.REVOKED in act_status:
                        status = states.REVOKED

                    activities[node_id]["status"] = status
                elif key == "pipeline":
                    self.recursion_subprocess_status(activities[node_id]["pipeline"]["activities"], node_maps)

    def recursion_nodes_status(self, node: FlowNode, status: str, raw_data: Dict):
        for key, values in raw_data.items():
            if key == node.node_id:
                raw_data[key]["status"] = status
                raw_data[key]["created_at"] = datetime2timestamp(node.created_at)
                raw_data[key]["started_at"] = datetime2timestamp(node.started_at)
                raw_data[key]["updated_at"] = datetime2timestamp(node.updated_at)
                raw_data[key]["hosts"] = node.hosts
                continue

            if isinstance(values, dict):
                self.recursion_nodes_status(node, status, values)

    def recursion_subprocess_activity_status(self, root_id: str, activities: Dict, act_status: List, node_maps: Dict):
        for node_id, activity in activities.items():
            for key, value in activity.items():
                if key == "type" and value == "SubProcess":
                    self.recursion_subprocess_activity_status(
                        root_id, activity["pipeline"]["activities"], act_status, node_maps
                    )
                elif key == "type" and value == "ServiceActivity":
                    status = node_maps[node_id]
                    act_status.append(status)

    def recursion_translate_activity(self, activities: Dict):
        """递归翻译节点名称"""
        for activity in activities.values():
            activity["name"] = i18n_str(activity["name"])
            if "pipeline" in activity:
                self.recursion_translate_activity(activity["pipeline"]["activities"])

    def get_pipeline_tree_states(self) -> Optional[Dict]:
        """获取流程数据包括状态"""
        tree = self.get_pipeline_tree()
        if not tree:
            return None
        activities = tree["activities"]
        node_maps = {}
        nodes = FlowNode.objects.filter(root_id=self.root_id)
        for node in nodes:
            node_maps[node.node_id] = node.status
        self.recursion_subprocess_status(activities, node_maps)
        self.recursion_translate_activity(activities)
        for node in nodes:
            self.recursion_nodes_status(node, node.status, tree)
        return tree

    def get_pipeline_tree(self) -> Optional[Dict]:
        try:
            flow = FlowTree.objects.get(root_id=self.root_id)
            return flow.tree
        except FlowTree.DoesNotExist:
            return None

    def get_node_short_histories(self, node_id) -> List[Dict[str, Any]]:
        result = api.get_node_short_histories(runtime=BambooDjangoRuntime(), node_id=node_id)
        return result.data

    def callback(self, node_id: str, desc: Any) -> EngineAPIResult:
        states = self.get_pipeline_states().data
        if not isinstance(states, dict):
            raise PipelineError(_("获取流程失败"))
        children = states[self.root_id]["children"][node_id]
        if not isinstance(children, dict):
            raise PipelineError(_("获取流程节点失败"))
        version = children.get("version", None)
        if version is None:
            raise PipelineError(_("获取节点运行版本失败"))
        result = api.callback(
            runtime=BambooDjangoRuntime(), node_id=node_id, version=version, data={"description": desc}
        )
        return result
