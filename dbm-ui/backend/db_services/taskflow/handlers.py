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
import zlib
from datetime import timedelta
from json import JSONDecodeError
from operator import itemgetter
from typing import Any, Callable, Dict, List, Optional

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
    GetNodeDataException,
    OperateNodeException,
    RevokePipelineException,
    SkipNodeException,
)
from backend.flow.consts import PENDING_STATES, FlowNodeOperateType, StateType
from backend.flow.engine.bamboo.engine import BambooEngine
from backend.flow.models import FlowNode, FlowNodeOperateRecord, FlowTree
from backend.utils.string import format_json_string
from backend.utils.time import calculate_cost_time, datetime2str

logger = logging.getLogger("root")

# 日志按页拉取的页大小
LOG_DOWNLOAD_PAGE_SIZE = 2000
# 错误日志的额外过滤条件
ERROR_LOG_FILTER = 'AND "levelname: error"'


class TaskFlowHandler:
    def __init__(self, root_id: str):
        self.root_id = root_id

    def revoke_pipeline(self, operator: str, remark: str = ""):
        """撤销当前流程"""

        # 不管是否成功，优先插入操作记录
        FlowNodeOperateRecord.insert_root_record(self.root_id, operator, FlowNodeOperateType.PIPELINE_TERMINATE)

        tree = FlowTree.objects.get(root_id=self.root_id)
        if tree.status == StateType.REVOKED:
            return EngineAPIResult(result=True, message=_("pipeline已撤销"))

        # 如果当前的pipeline未被创建，则直接更新FlowTree的状态为撤销态
        if tree.status in PENDING_STATES:
            tree.status = StateType.REVOKED
            tree.save()
            result = EngineAPIResult(result=True, message=_("pipeline未创建，仅更新FlowTree"))
        # 撤销pipeline
        else:
            bamboo_engine = BambooEngine(root_id=self.root_id)
            result = bamboo_engine.revoke_pipeline()
            if not result.result:
                raise RevokePipelineException(",".join(result.exc.args))
            # 终止正在运行的节点，并将节点状态设置为revoke
            running_nodes = FlowNode.objects.filter(root_id=self.root_id, status=StateType.RUNNING)
            running_node_ids = list(running_nodes.values_list("node_id", flat=True))
            for node_id in running_node_ids:
                bamboo_engine.runtime.set_state(node_id=node_id, to_state=StateType.REVOKED)

        return result

    def retry_node(self, node_id: str, operator: str, remark: str = "", is_force: bool = False):
        """重试节点"""
        operate_type = FlowNodeOperateType.FORCE_RETRY if is_force else FlowNodeOperateType.RETRY
        flow = FlowNodeOperateRecord.insert_record(node_id, operator, operate_type, remark, root_id=self.root_id)
        return task.retry_node(root_id=self.root_id, flow_node=flow, retry_times=1, is_force=is_force)

    def skip_node(self, node_id: str, operator: str, remark: str = "", is_force: bool = False):
        """跳过节点"""
        operate_type = FlowNodeOperateType.FORCE_SKIP if is_force else FlowNodeOperateType.SKIP
        FlowNodeOperateRecord.insert_record(node_id, operator, operate_type, remark, root_id=self.root_id)

        result = BambooEngine(root_id=self.root_id).skip_node(node_id=node_id, is_force=is_force)
        if not result.result:
            raise SkipNodeException(",".join(result.exc.args))

        return result

    def force_fail_node(self, node_id: str, operator: str):
        """强制失败节点"""
        FlowNodeOperateRecord.insert_record(node_id, operator, FlowNodeOperateType.FORCE_FAIL, root_id=self.root_id)

        result = BambooEngine(root_id=self.root_id).force_fail_node(node_id=node_id, ex_data=_("人工强制失败"))
        if not result.result:
            raise ForceFailNodeException(",".join(result.exc.args))

        return result

    def batch_operate_nodes(
        self,
        func: Callable,
        node_status: StateType,
        operator: str,
        some_nodes: List[str] = None,
        is_force: bool = False,
        remark: str = "",
    ):
        """批量操作节点"""
        node_ids = self.get_specific_node_ids(status=node_status)
        # 支持部分节点重试
        if some_nodes:
            node_ids = list(set(node_ids) & set(some_nodes))

        errors = []
        for node_id in node_ids:
            try:
                if is_force:
                    func(node_id, operator, is_force=is_force, remark=remark)
                else:
                    func(node_id, operator)
            except Exception as err:
                errors.append(f"{node_id} operate failed, err is {err}")

        if errors:
            success, fail = len(node_ids) - len(errors), len(errors)
            raise OperateNodeException(_("成功{}个节点, 失败{}个节点, 错误信息:{}").format(success, fail, errors))

    def batch_retry_nodes(self, operator: str, some_nodes: List[str] = None, is_force: bool = False, remark: str = ""):
        """批量重试节点"""
        self.batch_operate_nodes(self.retry_node, StateType.FAILED, operator, some_nodes, is_force, remark)

    def batch_force_fail_nodes(self, operator: str, some_nodes: List[str] = None):
        """批量强制失败节点"""
        self.batch_operate_nodes(self.force_fail_node, StateType.RUNNING, operator, some_nodes)

    def batch_skip_nodes(self, operator: str, some_nodes: List[str] = None, is_force: bool = False, remark: str = ""):
        """批量强制失败节点"""
        self.batch_operate_nodes(self.skip_node, StateType.FAILED, operator, some_nodes, is_force, remark)

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

    def get_specific_node_ids(self, status: StateType) -> List[str]:
        """
        获取特定状态节点ID列表
        """
        node_ids = []
        tree_states = BambooEngine(root_id=self.root_id).get_pipeline_tree_states() or {}
        activities = tree_states.get("activities", {})

        def recurse_activities(current_activities):
            for act_id, activity in current_activities.items():
                # 如果有子流程，递归检查子流程内的活动
                if "pipeline" in activity:
                    pipeline_activities = activity["pipeline"].get("activities", {})
                    recurse_activities(pipeline_activities)
                if activity.get("status") == status and activity.get("type") == NodeType.ServiceActivity.value:
                    node_ids.append(act_id)

        recurse_activities(activities)
        return node_ids

    def get_specific_nodes(self, status: StateType, with_node_name: bool = False) -> List[Dict[str, str]]:
        """
        获取特定状态节点详情（节点ID、版本ID、可选节点名称）
        """
        # 获取特定状态节点ID列表
        node_ids = self.get_specific_node_ids(status=status)
        if not node_ids:
            return []

        # 获取节点版本ID映射
        nodes = FlowNode.objects.filter(root_id=self.root_id, node_id__in=node_ids)
        version_map = {node.node_id: node.version_id for node in nodes}

        # 获取节点名称映射
        name_map = {}
        if with_node_name:
            engine = BambooEngine(root_id=self.root_id)
            engine.recursion_activity_name(engine.get_pipeline_tree()["activities"], name_map)

        return [
            {"node_id": node_id, "version_id": version_map.get(node_id), "node_name": name_map.get(node_id, "")}
            for node_id in node_ids
        ]

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

    def get_node_execution_data(self, node_id: str) -> Dict[str, Any]:
        """获取节点执行数据"""
        result = BambooEngine(root_id=self.root_id).get_node_execution_data(node_id=node_id)
        if not result.result:
            raise GetNodeDataException(",".join(result.exc.args))
        return result.data

    def get_node_operate_records(self, node_id: str = None) -> List[Dict[str, Any]]:
        """获取节点历史记录"""
        node_records = FlowNodeOperateRecord.objects.filter(root_id=self.root_id)
        if node_id:
            node_records = node_records.filter(node_id=node_id)
        node_records = list(node_records.order_by("-operate_date").values())
        # 补充节点名称
        node_name_map = {}
        engine = BambooEngine(root_id=self.root_id)
        engine.recursion_activity_name(engine.get_pipeline_tree()["activities"], node_name_map)
        for record in node_records:
            record.update(node_name=node_name_map.get(record["node_id"], ""))
        return node_records

    @classmethod
    def get_node_id_by_component(cls, tree: Dict, component_code: str) -> List[str]:
        """
        根据component获取node id id
        :param tree: 流程树对象
        :param component_code: 组件code名称
        """
        node_ids: List = []

        def component_search(_tree):
            activities: Dict = _tree["activities"]
            for node_id, activity in activities.items():
                if activity.get("component") and activity["component"]["code"] == component_code:
                    node_ids.append(node_id)
                if activity.get("pipeline"):
                    component_search(activity["pipeline"])

        component_search(tree)
        return node_ids

    @staticmethod
    def bklog_esquery_search(
        indices,
        query_string,
        start_time,
        end_time,
        offset: int = 0,
        limit: int = 10000,
        search_after: list = None,
        sort_list: list = None,
    ):
        """esquery搜索"""
        params = {
            "indices": indices,
            "start_time": start_time,
            "end_time": end_time,
            "query_string": query_string,
            "start": offset,
            "size": limit,
        }
        # 空游标/排序不下发，避免被日志平台当成有效查询条件
        if search_after:
            params["search_after"] = search_after
        if sort_list:
            params["sort_list"] = sort_list
        return BKLogApi.esquery_search(params)["hits"]["hits"]

    def _version_log_window(self, node_id: str, version_id: str):
        """校验节点日志是否可查，返回 (提示文案, 开始时间, 结束时间)。"""
        if not FlowNode.objects.filter(root_id=self.root_id, node_id=node_id).count():
            return _("节点尚未运行，请稍后查看"), None, None
        try:
            history = {h["version"]: h for h in self.get_node_histories(node_id)}[version_id]
        except KeyError:
            return _("无法找到当前版本{}的节点日志").format(version_id), None, None
        if history["finished_time"] < timezone.now() - timedelta(days=env.BKLOG_DEFAULT_RETENTION):
            return _("节点日志仅保留{}天").format(env.BKLOG_DEFAULT_RETENTION), None, None
        return (
            None,
            datetime2str(history["started_time"]),
            datetime2str(history["finished_time"] + timedelta(days=1)),
        )

    def _version_log_collectors(self, node_id: str, version_id: str, extra_filter: str = ""):
        """节点日志的两个采集源，返回 [(索引, 查询DSL)]。extra_filter 用于追加过滤条件(如错误日志)。"""
        pods = " OR ".join(
            f"__ext.io_kubernetes_pod:*{pod}*" for pod in ("schedule", "worker", "dbsimulation", "dbpriv")
        )
        biz = env.DBA_APP_BK_BIZ_ID
        base_query = f'"{self.root_id}" AND "{node_id}" AND {version_id}'
        return [
            (f"{biz}_bklog.dbm_log", f"({base_query}) AND ({pods}) {extra_filter}".strip()),
            (f"{biz}_bklog.dbm_dbactuator,{biz}_bklog.dbm_win_dbactuator,", f"{base_query} {extra_filter}".strip()),
        ]

    def _iter_merged_hits(self, collectors, start_time, end_time, desc: bool, page_size: int):
        """两个采集源各自 search_after 后按时间归并，避免共用游标漏日志。"""
        order = "desc" if desc else "asc"
        sort_list = [["dtEventTimeStamp", order], ["gseIndex", order], ["iterationIndex", order]]
        cursors = [{"buf": [], "i": 0, "after": None, "done": False} for _ in collectors]

        def peek(cursor, indices, query_string):
            if cursor["done"]:
                return None
            if cursor["i"] >= len(cursor["buf"]):
                hits = (
                    self.bklog_esquery_search(
                        indices=indices,
                        query_string=query_string,
                        start_time=start_time,
                        end_time=end_time,
                        offset=0,
                        limit=page_size,
                        search_after=cursor["after"],
                        sort_list=sort_list,
                    )
                    or []
                )
                if not hits:
                    cursor["done"] = True
                    return None
                last = hits[-1]
                source = last.get("_source") or {}
                cursor.update(
                    buf=hits,
                    i=0,
                    after=last.get("sort")
                    or [source.get("dtEventTimeStamp"), source.get("gseIndex"), source.get("iterationIndex")],
                )
            hit = cursor["buf"][cursor["i"]]
            return self._hit_sort_key(hit), hit

        while True:
            ranked = []
            for seq, (cursor, (indices, query_string)) in enumerate(zip(cursors, collectors)):
                item = peek(cursor, indices, query_string)
                if item:
                    ranked.append((item[0], seq, cursor))
            if not ranked:
                return
            cursor = (max(ranked) if desc else min(ranked))[2]
            yield cursor["buf"][cursor["i"]]
            cursor["i"] += 1

    @staticmethod
    def _hit_sort_key(hit: Dict):
        """命中记录的排序键，归并多个采集源时与 ES 的排序保持一致。"""
        source = hit.get("_source") or {}
        return (
            int(source.get("dtEventTimeStamp") or 0),
            int(source.get("gseIndex") or 0),
            int(source.get("iterationIndex") or 0),
        )

    def _hit_to_record(self, hit: Dict, label_filters: list = None):
        source = hit.get("_source") or {}
        log = self._format_log(source.get("log", ""), source.get("serverIp", ""), hit.get("_index", ""))
        if not log or (label_filters and log.get("label") in label_filters):
            return None
        return self.generate_log_record(timestamp=source.get("time"), levelname=log["levelname"], message=log["log"])

    def _collect_version_logs(self, node_id: str, version_id: str, extra_filter: str = ""):
        """拉齐两个采集源的命中并按时间正序合并。窗口校验不通过时返回 (None, 提示文案)。"""
        reason, start_time, end_time = self._version_log_window(node_id, version_id)
        if reason:
            return None, reason
        hits = []
        for indices, query_string in self._version_log_collectors(node_id, version_id, extra_filter):
            logger.info(_("BKLog 查询DSL: {} {}").format(indices, query_string))
            hits.extend(
                self.bklog_esquery_search(
                    indices=indices, query_string=query_string, start_time=start_time, end_time=end_time
                )
                or []
            )
        return sorted(hits, key=self._hit_sort_key), None

    def _iter_version_records(self, node_id: str, version_id: str, label_filters: list, desc: bool):
        reason, start_time, end_time = self._version_log_window(node_id, version_id)
        if reason:
            yield self.generate_log_record(message=reason)
            return
        produced = False
        hits = self._iter_merged_hits(
            self._version_log_collectors(node_id, version_id), start_time, end_time, desc, LOG_DOWNLOAD_PAGE_SIZE
        )
        for hit in hits:
            record = self._hit_to_record(hit, label_filters)
            if not record:
                continue
            produced = True
            yield record
        if not produced:
            yield self.generate_log_record(message=_("日志上报中，请稍后查看"))

    def get_version_logs_with_search_after(self, node_id: str, version_id: str, label_filters: list = None):
        """节点日志预览：按时间正序（从旧到新）分页拉取，累计超过大小阈值后停止。"""
        max_size = int(env.MAX_LOG_SIZE_MB * 1024 * 1024)
        logs, total, too_large = [], 0, False
        for record in self._iter_version_records(node_id, version_id, label_filters, False):
            size = len(str(record).encode("utf-8"))
            if total + size > max_size:
                too_large = True
                break
            logs.append(record)
            total += size
        return {"logs": logs, "too_large": too_large}

    def validate_version_log_download(self, node_id: str, version_id: str):
        """下载前校验。有提示文案时调用方返回 400 + JSON，不要进入 gzip 生成器。"""
        return self._version_log_window(node_id, version_id)[0]

    def iter_gzip_version_logs(self, node_id: str, version_id: str, label_filters: list = None):
        """按时间正序增量压缩。无论中途是否出错都必须 flush，否则 gzip 没有合法结尾。"""
        compressor = zlib.compressobj(wbits=16 + zlib.MAX_WBITS)

        def compress(record: Dict) -> bytes:
            line = f"[{record['timestamp']} {record['levelname']}] {record['message']}\n"
            return compressor.compress(line.encode("utf-8")) or b""

        try:
            for record in self._iter_version_records(node_id, version_id, label_filters, False):
                chunk = compress(record)
                if chunk:
                    yield chunk
        except Exception as err:
            # 响应头(200 + Content-Disposition)已经发出，状态码改不了，只能把中断原因写进文件，
            # 否则用户拿到的是一个解压才报错、且查不到原因的截断包
            logger.exception("node log download interrupted: root_id=%s, node_id=%s", self.root_id, node_id)
            yield compress(
                self.generate_log_record(
                    levelname=LogLevelName.ERROR.value,
                    message=_("日志拉取中断，文件可能不完整：{}").format(err),
                )
            )
        tail = compressor.flush()
        if tail:
            yield tail

    def get_version_logs(self, node_id: str, version_id: str, label_filters: list = None) -> List[Dict[str, Dict]]:
        """获取节点的日志信息"""
        hits, reason = self._collect_version_logs(node_id, version_id)
        if reason:
            return [self.generate_log_record(message=reason)]
        logs = [record for record in (self._hit_to_record(hit, label_filters) for hit in hits) if record]
        if not logs:
            return [self.generate_log_record(message=_("日志上报中，请稍后查看"))]
        return logs

    def get_version_error_logs(self, node_id: str, version_id: str) -> List[Dict[str, Dict[str, str]]]:
        """获取指定节点版本的错误级别日志。

        默认同时查询 dbm_log（pod 采集）与 dbactuator 采集日志，按时间合并后返回。
        """
        hits, reason = self._collect_version_logs(node_id, version_id, extra_filter=ERROR_LOG_FILTER)
        if reason:
            return [self.generate_log_record(message=reason)]
        return [record for record in (self._hit_to_record(hit) for hit in hits) if record]

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
        if levelname in [LogLevelName.INFO.value]:
            # 目前前端组件不支持自定义配色，暂时由后端处理INFO日志，不添加 ## 标签则展示白色
            # TODO 待前端组件优化后可去掉此段处理
            log = f"{prefix}: {format_json_string(log['msg'])}"
        else:
            log = f"##[{levelname.lower()}]{prefix}: {format_json_string(log['msg'])}"

        return {"levelname": levelname, "log": log}
