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
from collections import defaultdict
from typing import Any, Dict, List, Optional, Union

from bamboo_engine import api, builder, states
from bamboo_engine.api import EngineAPIResult
from bamboo_engine.builder import Data
from bamboo_engine.eri import NodeType
from django.utils.translation import gettext as _
from pipeline.eri.models import Schedule, State
from pipeline.eri.runtime import BambooDjangoRuntime

from backend.db_services.taskflow.utils import force_skip_and_retry_decorator
from backend.flow.engine.bamboo.builder import Builder
from backend.flow.engine.exceptions import PipelineError
from backend.flow.models import FlowNode, FlowTree, StateType
from backend.ticket.constants import TicketType
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
            db_type=TicketType.get_db_type_by_ticket(self.data["ticket_type"]),
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

    @force_skip_and_retry_decorator("can_retry")
    def retry_node(self, node_id: str, data: Optional[dict] = None, is_force: bool = False) -> EngineAPIResult:
        result = api.retry_node(runtime=BambooDjangoRuntime(), node_id=node_id, data=data)
        return result

    def retry_schedule(self, node_id: str) -> EngineAPIResult:
        """
        从 schedule 阶段重试失败节点
        与 retry_node 不同：retry_node 走 runtime.execute 会从 execute 阶段重头执行（重新下发动作）；
        本方法复用节点失败时残留的 Schedule 对象，直接从 schedule 阶段重新进入调度，不重跑 execute。
        仅适用于 execute 已成功、已进入 schedule（轮询/回调）阶段的节点，且 schedule 幂等（通常如此）
        """
        runtime = BambooDjangoRuntime()
        try:
            # node = runtime.get_node(node_id)
            state = runtime.get_state(node_id)

            # 仅允许对 RUNNING, FAILED, FINISHED 节点执行
            if state.name not in [states.RUNNING, states.FAILED, states.FINISHED]:
                raise PipelineError(_("节点当前状态为 {}, 只能对失败/完成节点执行 schedule 重试").format(state.name))

            # 按 node_id 取残留的 schedule（不按 version 过滤，避免被强制失败等操作刷新过的 state 版本打断）
            # execute 阶段就失败的节点不会有 schedule，这里取不到即说明无法从 schedule 重试
            db_schedule = Schedule.objects.filter(node_id=node_id).order_by("-id").first()
            if not db_schedule:
                raise PipelineError(_("节点 {} 不存在调度对象, 可能尚未进入 schedule 阶段, 请使用 retry_node").format(node_id))

            # kill / 强制失败只会把进程置为 asleep，故 sleep 进程仍可查到
            process_info = runtime.get_sleep_process_info_with_current_node_id(node_id)
            if not process_info:
                raise PipelineError(_("找不到处于睡眠状态且当前节点为 {} 的进程").format(node_id))

            # 状态：失败 ---> 准备
            if state.name == states.FAILED:
                runtime.set_state(
                    node_id=node_id,
                    to_state=states.READY,
                    version=state.version,
                    is_retry=True,
                    clear_started_time=True,
                    clear_archived_time=True,
                )
            # 状态：准备/成功 --> running
            if state.name != states.RUNNING:
                runtime.set_state(
                    node_id=node_id,
                    to_state=states.RUNNING,
                    version=state.version,
                    set_started_time=True,
                )

            # 将 schedule 版本对齐到当前 RUNNING 版本, 并复位 finished/expired, 使其可被重新调度
            Schedule.objects.filter(id=db_schedule.id).update(
                version=state.version, finished=False, expired=False, scheduling=False
            )

            # 不唤醒进程：schedule 阶段进程本就处于 sleep，对齐 callback 行为
            runtime.schedule(
                process_id=process_info.process_id,
                node_id=node_id,
                schedule_id=db_schedule.id,
            )
        except Exception as e:  # pylint: disable=broad-except
            logger.exception("retry_schedule for node(%s) failed", node_id)
            return EngineAPIResult(result=False, message="fail", exc=e)

        return EngineAPIResult(result=True, message="success")

    @force_skip_and_retry_decorator("can_skip")
    def skip_node(self, node_id: str, is_force: bool = False) -> EngineAPIResult:
        result = api.skip_node(runtime=BambooDjangoRuntime(), node_id=node_id)
        return result

    def force_fail_node(self, node_id: str, ex_data: str) -> EngineAPIResult:
        result = api.forced_fail_activity(runtime=BambooDjangoRuntime(), node_id=node_id, ex_data=ex_data)
        return result

    def get_node_input_data(self, node_id: str) -> EngineAPIResult:
        result = api.get_execution_data_inputs(runtime=BambooDjangoRuntime(), node_id=node_id)
        return result

    def get_node_output_data(self, node_id: str) -> EngineAPIResult:
        result = api.get_execution_data_outputs(runtime=BambooDjangoRuntime(), node_id=node_id)
        return result

    def get_node_histories(self, node_id: str) -> EngineAPIResult:
        result = api.get_node_histories(runtime=BambooDjangoRuntime(), node_id=node_id)
        return result

    def get_node_execution_data(self, node_id: str):
        result = api.get_execution_data(runtime=BambooDjangoRuntime(), node_id=node_id)
        return result

    def get_node_state(self, node_id: str) -> State:
        result = self.runtime.get_state_or_none(node_id)
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
            if isinstance(value, dict):
                self.hide_sensitive_data(value)
        return copy_data

    def recursion_subprocess_status(
        self, activities: Dict, flow_node_maps: Dict, node_children_status: Dict[str, Dict[str, Union[str, List]]]
    ):
        """为子流程添加状态"""
        for node_id, activity in activities.items():
            if activity.get("pipeline"):
                self.recursion_subprocess_status(
                    activities[node_id]["pipeline"]["activities"], flow_node_maps, node_children_status
                )

            if activity.get("type") == "SubProcess":
                status = node_children_status[node_id]["status"]
                children_status_list = node_children_status.get(node_id, {}).get("children_states", [])
                if status == states.RUNNING and states.FAILED in children_status_list:
                    status = states.FAILED
                elif status == states.RUNNING and states.REVOKED in children_status_list:
                    status = states.REVOKED

                act_status = []
                if activity.get("pipeline"):
                    self.recursion_subprocess_act_status(
                        self.root_id, activity["pipeline"]["activities"], act_status, flow_node_maps
                    )
                if states.FAILED in act_status:
                    status = states.FAILED
                elif states.REVOKED in act_status:
                    status = states.REVOKED
                activities[node_id]["status"] = status

    def recursion_nodes_status(self, tree: Dict, flow_node_maps: Dict, node_state_maps: Dict):
        for key, values in tree.items():
            if key in flow_node_maps:
                node = flow_node_maps[key]
                tree[key]["status"] = StateType.EXPIRED if node.is_expired else node.status
                tree[key]["created_at"] = int(datetime2timestamp(node.created_at))
                tree[key]["started_at"] = int(datetime2timestamp(node.started_at))
                tree[key]["updated_at"] = int(datetime2timestamp(node.updated_at))
                tree[key]["hosts"] = node.hosts
                # 补充node跳过和重试信息
                if key in node_state_maps:
                    tree[key]["skip"] = node_state_maps[key].skip
                    tree[key]["retry"] = node_state_maps[key].retry
                continue

            if isinstance(values, dict):
                self.recursion_nodes_status(values, flow_node_maps, node_state_maps)

    def recursion_subprocess_act_status(self, root_id: str, activities: Dict, act_status: List, flow_node_maps: Dict):
        for node_id, activity in activities.items():
            activity_type = activity.get("type")
            if activity_type == "SubProcess":
                self.recursion_subprocess_act_status(
                    root_id, activity["pipeline"]["activities"], act_status, flow_node_maps
                )
            elif activity_type == "ServiceActivity":
                status = flow_node_maps[node_id].status
                act_status.append(status)

    def recursion_translate_activity(self, activities: Dict):
        """递归翻译节点名称"""
        for activity in activities.values():
            activity["name"] = i18n_str(activity["name"])
            if "pipeline" in activity:
                self.recursion_translate_activity(activity["pipeline"]["activities"])

    def recursion_activity_name(self, activities: Dict, flow_node_name_map: Dict):
        """递归获取节点名称"""
        for node_id, activity in activities.items():
            flow_node_name_map.update({node_id: activity["name"]})
            if "pipeline" in activity:
                self.recursion_activity_name(activity["pipeline"]["activities"], flow_node_name_map)

    def get_pipeline_tree_states(self) -> Optional[Dict]:
        """获取流程数据包括状态"""
        tree = self.get_pipeline_tree()
        if not tree:
            return None
        activities = tree["activities"]
        flow_node_maps = {node.node_id: node for node in FlowNode.objects.filter(root_id=self.root_id)}
        node_state_maps = {node.node_id: node for node in BambooDjangoRuntime().get_state_by_root(self.root_id)}
        # pipeline 节点状态，根据父亲节点分组
        node_children_status = defaultdict(lambda: {"status": "", "children_states": []})
        for node in node_state_maps.values():
            node_children_status[node.node_id]["status"] = node.name
            node_children_status[node.parent_id]["children_states"].append(node.name)

        self.recursion_subprocess_status(activities, flow_node_maps, node_children_status)
        self.recursion_translate_activity(activities)
        self.recursion_nodes_status(tree, flow_node_maps, node_state_maps)
        return tree

    def get_pipeline_tree(self) -> Optional[Dict]:
        """获取流程树"""
        try:
            flow = FlowTree.objects.get(root_id=self.root_id)
            return flow.tree
        except FlowTree.DoesNotExist:
            return None

    def get_pipeline_tree_nodes(self) -> List[str]:
        """获取流程树节点(包括动作节点和gateway节点)"""
        node_ids: List[str] = []

        def recurse_pipeline_tree(pipeline_tree):
            # 获取当前根节点
            node_ids.append(pipeline_tree["id"])
            # 获取start/end event节点
            node_ids.extend([pipeline_tree["start_event"]["id"], pipeline_tree["end_event"]["id"]])
            # 获取geteway节点
            gateway_nodes = list(pipeline_tree.get("gateways", {}).keys())
            node_ids.extend(gateway_nodes)
            # 获取动作节点
            for node_id, activity in pipeline_tree.get("activities", {}).items():
                # 如果有子流程，递归检查子流程内的活动
                if activity.get("type") == NodeType.SubProcess.value:
                    recurse_pipeline_tree(activity["pipeline"])
                if activity.get("type") == NodeType.ServiceActivity.value:
                    node_ids.append(node_id)

        recurse_pipeline_tree(self.get_pipeline_tree())
        return node_ids

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
