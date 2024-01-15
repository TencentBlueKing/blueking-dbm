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

import json
import logging
import re
import time
from datetime import timedelta
from json import JSONDecodeError
from operator import itemgetter
from typing import Any, Dict, List, Optional

from bamboo_engine.api import EngineAPIResult
from bamboo_engine.eri import NodeType
from django.utils import timezone
from django.utils.translation import gettext as _

from backend import env
from backend.bk_web.constants import LogLevelName
from backend.components import BKLogApi
from backend.db_services.taskflow import task
from backend.db_services.taskflow.constants import LOG_START_STRIP_PATTERN
from backend.db_services.taskflow.exceptions import (
    CallbackNodeException,
    ForceFailNodeException,
    RevokePipelineException,
    SkipNodeException,
)
from backend.flow.consts import StateType
from backend.flow.engine.bamboo.engine import BambooEngine
from backend.flow.models import FlowNode, FlowTree
from backend.utils.string import format_json_string
from backend.utils.time import calculate_cost_time, datetime2str

logger = logging.getLogger("root")


class TaskFlowHandler:
    def __init__(self, root_id: str):
        self.root_id = root_id

    def revoke_pipeline(self):
        """撤销当前流程"""

        # 如果当前的pipeline未被创建，则直接更新FlowTree的状态为撤销态
        tree = FlowTree.objects.get(root_id=self.root_id)
        if tree.status in [StateType.CREATED, StateType.READY]:
            tree.status = StateType.REVOKED
            tree.save()
            return EngineAPIResult(result=True, message=_("pipeline未创建，仅更新FlowTree"))

        # 撤销pipeline
        bamboo_engine = BambooEngine(root_id=self.root_id)
        result = bamboo_engine.revoke_pipeline()
        if not result.result:
            raise RevokePipelineException(",".join(result.exc.args))

        # 终止正在运行的节点，并将节点状态设置为revoke
        running_node_ids = list(
            FlowNode.objects.filter(root_id=self.root_id, status=StateType.RUNNING).values_list("node_id", flat=True)
        )
        for node_id in running_node_ids:
            # TODO 这里无法强制失败节点以后再设置节点的状态为revoke，这里需要强制失败吗？
            # self.force_fail_node(node_id)
            # 更新节点状态为revoke
            bamboo_engine.runtime.set_state(node_id=node_id, to_state=StateType.REVOKED)

        return result

    def retry_node(self, node_id: str):
        """重试节点"""
        return task.retry_node(root_id=self.root_id, node_id=node_id, retry_times=1)

    def batch_retry_nodes(self):
        """批量重试节点"""
        node_ids = self.get_failed_node_ids()
        for node_id in node_ids:
            try:
                self.retry_node(node_id)
            except Exception as err:
                logger.error(f"{node_id} retry failed, {err}")

    def skip_node(self, node_id: str):
        """跳过节点"""
        result = BambooEngine(root_id=self.root_id).skip_node(node_id=node_id)
        if not result.result:
            raise SkipNodeException(",".join(result.exc.args))

        return result

    def force_fail_node(self, node_id: str):
        """强制失败节点"""
        result = BambooEngine(root_id=self.root_id).force_fail_node(node_id=node_id, ex_data=_("人工强制失败"))
        if not result.result:
            raise ForceFailNodeException(",".join(result.exc.args))

        return result

    def callback_node(self, node_id: str, desc: Optional[Any]):
        """回调节点"""
        engine = BambooEngine(root_id=self.root_id)
        result = engine.callback(node_id=node_id, desc=desc)
        logger.info(
            f"callback node----root_id:{self.root_id}, node_id:{node_id}\n"
            f"flow_tree:{engine.get_pipeline_tree_states()}"
        )
        if not result.result:
            raise CallbackNodeException(",".join(result.exc.args))

        return result

    def get_failed_node_ids(self) -> List[str]:
        """
        获取失败节点ID列表
        """
        node_ids = []
        tree_states = BambooEngine(root_id=self.root_id).get_pipeline_tree_states()
        activities = tree_states.get("activities", {})

        def recurse_activities(current_activities):
            for act_id, activity in current_activities.items():
                # 如果有子流程，递归检查子流程内的活动
                if "pipeline" in activity:
                    pipeline_activities = activity["pipeline"].get("activities", {})
                    recurse_activities(pipeline_activities)
                if activity.get("status") == StateType.FAILED and activity.get("type") == NodeType.ServiceActivity:
                    node_ids.append(act_id)

        recurse_activities(activities)
        return node_ids

    def get_node_histories(self, node_id: str) -> List[Dict[str, Any]]:
        """获取节点历史版本信息"""
        histories = [
            {
                "started_time": history["started_time"],
                "finished_time": history["archived_time"],
                "cost_time": calculate_cost_time(history["archived_time"], history["started_time"]),
                "version": history["version"],
            }
            for history in BambooEngine(root_id=self.root_id).get_node_short_histories(node_id=node_id)
        ]
        # 补充当前节点的版本
        flow_node = FlowNode.objects.get(root_id=self.root_id, node_id=node_id)
        histories.append(
            {
                "started_time": flow_node.started_at,
                "finished_time": flow_node.updated_at,
                "cost_time": calculate_cost_time(flow_node.updated_at, flow_node.started_at),
                "version": flow_node.version_id,
            }
        )
        return sorted(histories, key=itemgetter("started_time"), reverse=True)

    def get_version_logs(self, node_id: str, version_id: str) -> List[Dict[str, str]]:
        """获取节点的日志信息"""
        try:
            flow_node = FlowNode.objects.get(root_id=self.root_id, node_id=node_id)
        except FlowNode.DoesNotExist:
            return [self.generate_log_record(message=_("节点尚未运行，请稍后查看"))]
        if flow_node.updated_at < timezone.now() - timedelta(days=7):
            return [self.generate_log_record(message=_("节点日志仅保留7天"))]

        resp = BKLogApi.esquery_search(
            {
                "indices": f"{env.DBA_APP_BK_BIZ_ID}_bklog.dbm_log,{env.DBA_APP_BK_BIZ_ID}_bklog.dbm_dbactuator",
                "start_time": datetime2str(flow_node.started_at),
                # 检索节点开始后一天内的日志，一般情况下，节点执行时间不会超过一天
                "end_time": datetime2str(flow_node.updated_at + timedelta(days=1)),
                # TODO 可优化检索，需清洗后根据 root_id、node_id、version_id 进行检索
                "query_string": f"{self.root_id} AND {node_id} AND {version_id}",
                "start": 0,
                "size": 1000,
                "sort_list": [["dtEventTimeStamp", "asc"], ["gseIndex", "asc"], ["iterationIndex", "asc"]],
            }
        )
        logs = []
        for hit in resp["hits"]["hits"]:
            log = self._format_log(hit["_source"]["log"], hit["_source"]["serverIp"], hit["_index"])
            if log:
                logs.append(
                    self.generate_log_record(
                        timestamp=hit["_source"].get("time"), levelname=log["levelname"], message=log["log"]
                    )
                )
        if not logs:
            return [self.generate_log_record(message=_("日志上报中，请稍后查看"))]
        return logs

    @staticmethod
    def generate_log_record(
        message: str, levelname: str = LogLevelName.INFO.value, timestamp: Optional[float] = None
    ) -> Dict:
        if not timestamp:
            # 使用13位时间戳
            timestamp = int(round(time.time() * 1000))
        return {"timestamp": timestamp, "levelname": levelname, "message": message}

    @staticmethod
    def _format_log(log: str, ip: str, index: str) -> Optional[Dict[str, str]]:
        """格式化日志，为方便前端组件渲染"""

        # flow日志默认不展示ip
        prefix = "[flow]" if f"{env.DBA_APP_BK_BIZ_ID}_bklog_dbm_log" in index else f"[dbactuator-{ip}]"
        log = re.sub(LOG_START_STRIP_PATTERN, "", log)

        try:
            log = json.loads(log)
        except JSONDecodeError:
            # TODO 日志清洗后则无需json反序列化
            return
        levelname = log.get("levelname", LogLevelName.INFO.value)
        if levelname == LogLevelName.DEBUG.value:
            # 不暴露debug日志给用户
            return
        if levelname == LogLevelName.INFO.value:
            # 目前前端组件不支持自定义配色，暂时由后端处理INFO日志，不添加 ## 标签则展示白色
            # TODO 待前端组件优化后可去掉此段处理
            log = f"{prefix}: {format_json_string(log['msg'])}"
        else:
            log = f"##[{levelname.lower()}]{prefix}: {format_json_string(log['msg'])}"

        return {"levelname": levelname, "log": log}
