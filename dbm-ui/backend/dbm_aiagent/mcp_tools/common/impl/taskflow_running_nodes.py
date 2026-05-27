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
from typing import Dict, List, Optional, Set

from bamboo_engine import api
from django.utils import timezone
from django.utils.translation import gettext as _
from pipeline.eri.runtime import BambooDjangoRuntime

from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpInvalidPipelineNodeException
from backend.flow.consts import StateType
from backend.flow.models import FlowNode, FlowTree

logger = logging.getLogger("root")

# 入参匹配时需要排除的噪声字段（每次执行必然不同）
EXCLUDE_KWARGS_KEYS = {
    "root_id",
    "node_id",
    "node_name",
    "uid",
    "job_root_id",
    "bk_biz_id",
    "created_by",
    "ticket_type",
    "ticket",
    # clusters 字典的 key 数量取决于单据涉及的集群数，不同单据差异大，属于噪声
    "clusters",
    # job_id 每次执行必然不同，纯噪声
    "job_id",
}
# 一级key需要排除的噪声字段，固定行为
EXCLUDE_KEYS = {
    "splice_payload_var",
    "write_payload_var",
    "_inner_loop",
    "_loop",
    "trans_data",
}

# 历史对比最大基准样本数
MAX_HISTORICAL_SAMPLES = 5

# 历史 flow 最大查询数量（增大，给去重留余量）
MAX_HISTORICAL_FLOWS = 15

# 每个历史 flow 内最多检查的候选节点数
MAX_CANDIDATES_PER_FLOW = 10

# ID 类字段名后缀/关键词，这些字段的数值应该用精确匹配
_ID_FIELD_SUFFIXES = ("_id", "_ids", "id", "port", "bk_cloud_id", "db_module_id")


def _collect_activity_info(
    activities: Dict, name_map: Dict, component_map: Dict, target_node_id: Optional[str] = None
) -> None:
    """
    一次遍历递归收集活动节点的名称和 component_code。

    Args:
        activities: 当前层级的 activities 字典
        name_map: 收集结果的字典，key 为 node_id，value 为 name
        component_map: 收集结果的字典，key 为 node_id，value 为 component_code
        target_node_id: 指定目标节点ID，传入则只收集该节点相关的信息；不传则全局收集
            - 若目标是 SubProcess：收集其内部所有子节点
            - 若目标是 ServiceActivity：只收集该节点本身
            - 若目标是其他类型：抛出 ValueError

    Raises:
        DBMMcpInvalidPipelineNodeException: 当指定了 target_node_id 但未找到，或目标节点类型不支持时抛出
    """
    if not target_node_id:
        # 全量收集模式
        _collect_all_activities(activities, name_map, component_map)
        return

    # 定位目标节点
    target_activity = _find_activity_by_id(activities, target_node_id)
    if target_activity is None:
        raise DBMMcpInvalidPipelineNodeException(msg=_("未找到指定的节点ID: {}").format(target_node_id))

    activity_type = target_activity.get("type", "")

    if activity_type == "SubProcess":
        # 目标是子流程，收集其内部所有节点
        sub_activities = target_activity.get("pipeline", {}).get("activities", {})
        _collect_all_activities(sub_activities, name_map, component_map)
    elif activity_type == "ServiceActivity":
        # 目标是单个服务节点，只收集它本身
        name_map[target_node_id] = target_activity.get("name", "")
        component = target_activity.get("component")
        if component:
            component_map[target_node_id] = component.get("code", "")
    else:
        raise DBMMcpInvalidPipelineNodeException(
            msg=_("指定的节点ID: {} 类型为 {}，不是可执行的活动节点（仅支持 SubProcess 和 ServiceActivity）").format(
                target_node_id, activity_type
            )
        )


def _find_activity_by_id(activities: Dict, target_id: str) -> Optional[Dict]:
    """
    在 activities 树中递归查找指定 ID 的节点（唯一），找到立即返回。

    Args:
        activities: 当前层级的 activities 字典
        target_id: 目标节点ID

    Returns:
        找到则返回该节点的 activity 字典，否则返回 None
    """
    for node_id, activity in activities.items():
        if node_id == target_id:
            return activity
        # 仅 SubProcess 有嵌套子节点，需要递归查找
        if activity.get("type") == "SubProcess":
            found = _find_activity_by_id(activity.get("pipeline", {}).get("activities", {}), target_id)
            if found is not None:
                return found
    return None


def _collect_all_activities(activities: Dict, name_map: Dict, component_map: Dict) -> None:
    """递归收集所有活动节点的名称和 component_code"""
    for node_id, activity in activities.items():
        activity_type = activity.get("type", "")
        if activity_type == "ServiceActivity":
            name_map[node_id] = activity.get("name", "")
            component = activity.get("component")
            if component:
                component_map[node_id] = component.get("code", "")
        elif activity_type == "SubProcess":
            _collect_all_activities(activity.get("pipeline", {}).get("activities", {}), name_map, component_map)


def _find_nodes_by_component_code(activities: Dict, target_code: str) -> List[str]:
    """递归查找指定 component_code 的所有节点ID"""
    node_ids = []
    for node_id, activity in activities.items():
        activity_type = activity.get("type", "")
        if activity_type == "ServiceActivity":
            if activity.get("component") and activity["component"].get("code") == target_code:
                node_ids.append(node_id)
        elif activity_type == "SubProcess":
            node_ids.extend(
                _find_nodes_by_component_code(activity.get("pipeline", {}).get("activities", {}), target_code)
            )
    return node_ids


def _calculate_kwargs_similarity(
    current_kwargs: dict, historical_kwargs: dict, exclude_keys: Set[str] = None
) -> float:
    """
    计算两个节点入参的相似度，返回 0~1 之间的分数（-1.0 表示无法比较）。

    【整体策略】
    1. 噪声排除：通过 exclude_keys 过滤掉每次执行必然不同的字段
       - 一级排除（EXCLUDE_KEYS）：splice_payload_var, write_payload_var, _inner_loop, _loop, trans_data
       - 嵌套排除（EXCLUDE_KWARGS_KEYS）：root_id, node_id, node_name, uid, job_root_id,
         bk_biz_id, created_by, ticket_type, ticket, clusters, job_id
    2. 取两边 key 的交集逐字段打分，并集作为分母（惩罚字段缺失）

    【逐字段打分规则】
    - 值完全相等 (cv == hv)：1.0 分
    - 同类型 - 列表：Jaccard 相似度 |A∩B| / |A∪B|；不可哈希元素退化为长度比
    - 同类型 - 数值 + ID 类字段（字段名匹配 _ID_FIELD_SUFFIXES）：不同则 0 分
    - 同类型 - 数值 + 度量类字段：min(a,b) / max(a,b)
    - 同类型 - 嵌套 dict：递归调用自身（使用 EXCLUDE_KWARGS_KEYS 排除噪声）
    - 同类型 - 其他（如字符串不等）：0.3 分
    - 类型不同：0 分

    【ID 类字段判断】
    通过 _ID_FIELD_SUFFIXES 元组匹配字段名后缀：
    ("_id", "_ids", "id", "port", "bk_cloud_id", "db_module_id")

    【最终公式】
    相似度 = sum(各 common_key 得分) / len(all_keys 并集)

    Args:
        current_kwargs: 当前节点的入参字典
        historical_kwargs: 历史节点的入参字典
        exclude_keys: 需要排除的噪声字段集合

    Returns:
        0~1 之间的相似度分数；-1.0 表示无有效字段可比较
    """
    if exclude_keys is None:
        exclude_keys = set()

    # 清洗噪声字段
    current = {k: v for k, v in current_kwargs.items() if k not in exclude_keys}
    historical = {k: v for k, v in historical_kwargs.items() if k not in exclude_keys}

    all_keys = set(current.keys()) | set(historical.keys())
    if not all_keys:
        return -1.0  # 无有效字段可比较，返回 -1 表示不可比较

    common_keys = set(current.keys()) & set(historical.keys())
    if not common_keys:
        return 0.0

    match_score = 0.0
    for key in common_keys:
        cv, hv = current[key], historical[key]

        if cv == hv:
            match_score += 1.0
        elif isinstance(cv, list) and isinstance(hv, list):
            # 列表：尝试用内容交集比较（Jaccard 相似度），不可哈希元素退化为长度比较
            max_len = max(len(cv), len(hv))
            if max_len == 0:
                match_score += 1.0
            else:
                try:
                    # 可哈希元素：用交集计算内容相似度
                    set_cv, set_hv = set(cv), set(hv)
                    union = len(set_cv | set_hv)
                    match_score += len(set_cv & set_hv) / union if union > 0 else 1.0
                except TypeError:
                    # 不可哈希（如列表中嵌套 dict），退化为长度比较
                    match_score += min(len(cv), len(hv)) / max_len
        elif isinstance(cv, bool) or isinstance(hv, bool):
            # 显式拦截 bool：避免被下面的 (int, float) 分支误吞（bool 是 int 的子类）
            # 走到这里说明 cv != hv，类型相同时给部分分，类型不同不加分
            if isinstance(cv, bool) and isinstance(hv, bool):
                match_score += 0.3
        elif isinstance(cv, (int, float)) and isinstance(hv, (int, float)):
            # 数值比较：通过字段名区分 ID 类字段和度量类字段
            is_id_field = any(key.endswith(suffix) or key == suffix for suffix in _ID_FIELD_SUFFIXES)
            if is_id_field:
                # ID 类字段：不同则 0 分（已经在 cv == hv 分支处理了相等情况）
                match_score += 0.0
            else:
                # 度量类数值（如 timeout、大数值）：比较数量级
                max_val = max(abs(cv), abs(hv))
                if max_val > 0:
                    match_score += min(abs(cv), abs(hv)) / max_val
                else:
                    match_score += 1.0
        elif isinstance(cv, dict) and isinstance(hv, dict):
            # 嵌套字典：递归计算，kwargs/global_data 内部需要排除噪声字段
            match_score += _calculate_kwargs_similarity(cv, hv, exclude_keys=EXCLUDE_KWARGS_KEYS)
        elif isinstance(cv, type(hv)) and isinstance(hv, type(cv)):
            # 同类型不同值（如不等的字符串），给部分分；类型不同则不加分
            match_score += 0.3
        # 类型不同不加分

    # 用所有 key 的并集作为分母，惩罚字段缺失
    return match_score / len(all_keys)


def _get_node_inputs_safe(node_id: str) -> Optional[Dict]:
    """安全获取节点入参，失败返回 None"""
    try:
        result = api.get_execution_data_inputs(runtime=BambooDjangoRuntime(), node_id=node_id)
        if result.result:
            return result.data
    except Exception as e:
        logger.warning(_("获取节点{}入参失败: {}").format(node_id, e))
    return None


def _extract_cluster_ids_from_inputs(inputs: Dict) -> List[int]:
    """
    从节点入参中提取 cluster_id 列表

    入参结构固定为: {global_data: {}, trans_data: {}, kwargs: {}}
    cluster_id 的常见位置（按优先级）：
    1. kwargs["cluster_id"] — 最常见，单集群操作
    2. kwargs["cluster_ids"] — 多集群操作
    3. global_data["cluster_id"] — 大数据组件场景
    4. kwargs["cluster"]["id"] — 部分 Redis 场景（kwargs.cluster 是 dict）

    Returns:
        提取到的 cluster_id 列表，提取不到返回空列表
    """
    cluster_ids = []

    kwargs = inputs.get("kwargs") or {}
    global_data = inputs.get("global_data") or {}

    # 防御 kwargs 为 JSON 字符串的情况
    if isinstance(kwargs, str):
        try:
            kwargs = json.loads(kwargs)
        except (json.JSONDecodeError, TypeError):
            kwargs = {}

    # 防御 global_data 为 JSON 字符串的情况
    if isinstance(global_data, str):
        try:
            global_data = json.loads(global_data)
        except (json.JSONDecodeError, TypeError):
            global_data = {}

    # 优先从 kwargs 中提取
    if isinstance(kwargs, dict):
        # kwargs["cluster_id"]
        cid = kwargs.get("cluster_id")
        if isinstance(cid, int) and cid > 0:
            cluster_ids.append(cid)
            return cluster_ids

        # kwargs["cluster_ids"]
        cids = kwargs.get("cluster_ids")
        if isinstance(cids, list):
            valid_ids = [c for c in cids if isinstance(c, int) and c > 0]
            if valid_ids:
                return valid_ids

        # kwargs["cluster"]["id"] — 部分 Redis 等场景
        cluster_dict = kwargs.get("cluster")
        if isinstance(cluster_dict, dict):
            cid = cluster_dict.get("id")
            if isinstance(cid, int) and cid > 0:
                cluster_ids.append(cid)
                return cluster_ids

    # 从 global_data 中提取
    if isinstance(global_data, dict):
        cid = global_data.get("cluster_id")
        if isinstance(cid, int) and cid > 0:
            cluster_ids.append(cid)
            return cluster_ids

        cids = global_data.get("cluster_ids")
        if isinstance(cids, list):
            valid_ids = [c for c in cids if isinstance(c, int) and c > 0]
            if valid_ids:
                return valid_ids

    return cluster_ids


def _resolve_query_cluster_ids(current_inputs: Dict, fallback_cluster_ids: List[int]) -> List[int]:
    """
    解析用于查询历史记录的 cluster_ids。

    策略：优先从节点入参中提取（精准匹配），提取不到则退化为调用方传入的 cluster_ids。
    """
    node_cluster_ids = _extract_cluster_ids_from_inputs(current_inputs)
    if node_cluster_ids:
        return node_cluster_ids
    return fallback_cluster_ids or []


def _query_historical_records(
    query_cluster_ids: List[int],
    ticket_type: str,
    exclude_root_id: str,
):
    """
    查询同集群同 ticket_type 的历史已完成 flow 记录（按更新时间倒序，取前 N 条）。
    """
    # 延迟导入避免循环依赖
    from backend.ticket.constants import TicketFlowStatus
    from backend.ticket.models import ClusterOperateRecord

    return (
        ClusterOperateRecord.objects.select_related("flow", "ticket")
        .filter(
            cluster_id__in=query_cluster_ids,
            ticket__ticket_type=ticket_type,
            flow__status=TicketFlowStatus.SUCCEEDED,
        )
        .exclude(flow__flow_obj_id=exclude_root_id)
        .order_by("-flow__update_at")[:MAX_HISTORICAL_FLOWS]
    )


def _find_best_match_in_flow(
    historical_root_id: str,
    component_code: str,
    current_inputs: Dict,
) -> Optional[tuple]:
    """
    在指定的历史 flow 中找出与当前节点入参相似度最高的同 component_code 节点。

    Returns:
        (best_candidate_node_id, best_similarity) 元组；未找到合格节点返回 None
    """
    try:
        historical_flow_tree = FlowTree.objects.get(root_id=historical_root_id)
    except FlowTree.DoesNotExist:
        return None

    historical_activities = (historical_flow_tree.tree or {}).get("activities", {})
    candidate_node_ids = _find_nodes_by_component_code(historical_activities, component_code)
    if not candidate_node_ids:
        return None

    best_candidate = None
    best_similarity = 0.0
    for candidate_node_id in candidate_node_ids[:MAX_CANDIDATES_PER_FLOW]:
        historical_inputs = _get_node_inputs_safe(candidate_node_id)
        if not historical_inputs:
            continue

        similarity = _calculate_kwargs_similarity(current_inputs, historical_inputs, EXCLUDE_KEYS)
        if similarity < 0.8:
            continue

        if similarity > best_similarity:
            best_similarity = similarity
            best_candidate = candidate_node_id

    if not best_candidate:
        return None
    return best_candidate, best_similarity


def _build_historical_sample(
    historical_root_id: str,
    best_candidate: str,
    best_similarity: float,
    ticket_id: int,
) -> Optional[Dict]:
    """
    根据最佳匹配节点构造一条历史样本（含耗时统计）。

    取不到 FlowNode 或时间字段缺失时返回 None。
    """
    try:
        historical_node = FlowNode.objects.get(
            root_id=historical_root_id,
            node_id=best_candidate,
            status=StateType.FINISHED,
        )
    except FlowNode.DoesNotExist:
        return None

    if not historical_node.started_at or not historical_node.updated_at:
        return None

    historical_duration = int((historical_node.updated_at - historical_node.started_at).total_seconds())
    return {
        "root_id": historical_root_id,
        "node_id": best_candidate,
        "duration_seconds": historical_duration,
        "similarity": round(best_similarity, 3),
        "ticket_id": ticket_id,
    }


def _summarize_samples(matched_samples: List[Dict]) -> Dict:
    """聚合样本统计值（avg/max/min）。"""
    durations = [s["duration_seconds"] for s in matched_samples]
    return {
        "matched_sample_count": len(matched_samples),
        "avg_duration_seconds": round(sum(durations) / len(durations), 1),
        "max_duration_seconds": float(max(durations)),
        "min_duration_seconds": float(min(durations)),
        "matched_samples": matched_samples,
    }


def _get_historical_comparison(
    root_id: str,
    node_id: str,
    component_code: str,
    cluster_ids: List[int],
    ticket_type: str,
) -> Optional[Dict]:
    """
    获取单个运行节点的历史耗时对比数据（纯确定性数据，不做风险判定）

    逻辑：
    1. 通过 ClusterOperateRecord 找到同集群同 ticket_type 的历史已完成 flow
    2. 从历史 flow 的 pipeline tree 中找同 component_code 的节点
    3. 获取历史节点入参，与当前节点入参做相似度匹配（>=80%）
    4. 同一个历史 flow 只取相似度最高的节点作为样本
    5. 最多取 MAX_HISTORICAL_SAMPLES 个有效基准样本，返回统计值
    """
    if not component_code:
        return None

    current_inputs = _get_node_inputs_safe(node_id)
    if not current_inputs:
        return None

    query_cluster_ids = _resolve_query_cluster_ids(current_inputs, cluster_ids)
    # 防御：兜底校验（正常应在 view 层 serializer 拦截，这里防止 impl 被其他调用方直调）
    if not query_cluster_ids:
        return None

    historical_records = _query_historical_records(query_cluster_ids, ticket_type, exclude_root_id=root_id)
    if not historical_records:
        return None

    matched_samples: List[Dict] = []
    seen_root_ids: Set[str] = set()

    for record in historical_records:
        if len(matched_samples) >= MAX_HISTORICAL_SAMPLES:
            break

        historical_root_id = record.flow.flow_obj_id
        # 跳过空 root_id 或已处理过的 flow（多条 ClusterOperateRecord 可能指向同一个 flow）
        if not historical_root_id or historical_root_id in seen_root_ids:
            continue
        seen_root_ids.add(historical_root_id)

        match_result = _find_best_match_in_flow(historical_root_id, component_code, current_inputs)
        if not match_result:
            continue
        best_candidate, best_similarity = match_result

        sample = _build_historical_sample(historical_root_id, best_candidate, best_similarity, record.ticket_id)
        if sample:
            matched_samples.append(sample)

    if not matched_samples:
        return None

    return _summarize_samples(matched_samples)


def get_running_nodes_with_duration(
    root_id: str,
    worker_subprocess_id: Optional[str] = None,
    enable_historical_comparison: bool = False,
    cluster_ids: Optional[List[int]] = None,
) -> Dict:
    """
    获取当前flow中正在运行的节点及其耗时

    Args:
        root_id: pipeline的root_id
        worker_subprocess_id: 主任务子流程ID，传了则只查该子流程下的节点；不传则查root_id下所有节点
        enable_historical_comparison: 是否开启历史耗时对比，默认False
        cluster_ids: 集群ID列表，开启历史对比时必传（一个单据可能涉及多个集群）

    Returns:
        {
            "root_id": "xxx",
            "worker_subprocess_id": "yyy" or None,
            "flow_status": "RUNNING",
            "ticket_type": "MYSQL_HA_APPLY",
            "running_nodes": [
                {
                    "node_id": "xxx",
                    "node_name": "下发db-actuator介质",
                    "started_at": "2024-01-01T00:00:00+08:00",
                    "duration_seconds": 120,
                    "component_code": "execute_db_actuator_script",
                    "historical_comparison": {...} or None,
                    "historical_comparison_error": "xxx" or None,
                }
            ],
            "total_running_count": 2,
        }
    """
    # 0. 参数前置校验：开启历史对比但 cluster_ids 为空时，给出明确提示（兜底）
    historical_comparison_error: Optional[str] = None
    if enable_historical_comparison and not cluster_ids:
        historical_comparison_error = _("已开启历史耗时对比(enable_historical_comparison=True)，但未提供 cluster_ids，本次将跳过历史对比")
        logger.warning("[get_running_nodes_with_duration] %s, root_id=%s", historical_comparison_error, root_id)
        # 关闭历史对比开关，避免后续逻辑做无效查询
        enable_historical_comparison = False

    # 1. 获取FlowTree基本信息
    try:
        flow_tree = FlowTree.objects.get(root_id=root_id)
    except FlowTree.DoesNotExist:
        return {
            "root_id": root_id,
            "worker_subprocess_id": worker_subprocess_id,
            "flow_status": "",
            "ticket_type": "",
            "running_nodes": [],
            "total_running_count": 0,
            "error": _("未找到root_id={}对应的流程树").format(root_id),
        }

    # 2. 获取pipeline tree中的节点名称映射和component_code映射
    tree = flow_tree.tree or {}
    name_map: Dict[str, str] = {}
    component_map: Dict[str, str] = {}
    activities = tree.get("activities", {})
    _collect_activity_info(activities, name_map, component_map, worker_subprocess_id)

    # 3. 查询正在运行的FlowNode
    # name_map 的所有 key 即为目标范围内的所有 node_id
    running_nodes_qs = FlowNode.objects.filter(root_id=root_id, status=StateType.RUNNING)
    if name_map:
        running_nodes_qs = running_nodes_qs.filter(node_id__in=name_map.keys())

    running_nodes = running_nodes_qs.order_by("started_at")

    # 4. 组装结果
    now = timezone.now()
    running_node_list: List[Dict] = []
    for node in running_nodes:
        started_at = node.started_at
        duration_seconds = 0
        if started_at:
            duration_seconds = int((now - started_at).total_seconds())

        node_component_code = component_map.get(node.node_id, "")

        node_data = {
            "node_id": node.node_id,
            "node_name": name_map.get(node.node_id, ""),
            "started_at": started_at.isoformat() if started_at else None,
            "duration_seconds": duration_seconds,
            "component_code": node_component_code,
            "historical_comparison": None,
            "historical_comparison_error": historical_comparison_error,
        }

        # 5. 如果开启历史对比，获取对比数据
        if enable_historical_comparison and cluster_ids:
            node_data["historical_comparison"] = _get_historical_comparison(
                root_id=root_id,
                node_id=node.node_id,
                component_code=node_component_code,
                cluster_ids=cluster_ids,
                ticket_type=flow_tree.ticket_type,
            )

        running_node_list.append(node_data)

    return {
        "root_id": root_id,
        "worker_subprocess_id": worker_subprocess_id,
        "flow_status": flow_tree.status,
        "ticket_type": flow_tree.ticket_type,
        "running_nodes": running_node_list,
        "total_running_count": len(running_node_list),
    }
