# -*- coding: utf-8 -*-
"""
蓝鲸作业 job_instance 与流程/单据关联落库工具
"""
from __future__ import annotations

import logging
from typing import Any, List, Optional

from django.utils.translation import gettext as _

from backend.flow.models import FlowBkJobInstance, FlowExecIpRecord

logger = logging.getLogger("flow")


def _as_positive_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def _int_id_or_none(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _step_id_from_data_dict(data: dict) -> Optional[int]:
    s = _int_id_or_none(data.get("step_instance_id"))
    if s is not None:
        return s
    s_list = data.get("step_instance_list")
    if isinstance(s_list, list) and s_list and isinstance(s_list[0], dict):
        return _int_id_or_none(s_list[0].get("step_instance_id"))
    return None


def try_resolve_step_instance_id(ext_result: Optional[dict], job_instance_id: int) -> Optional[int]:
    """
    尝试解析 step_instance_id：先读 fast_execute 的 data，若无则再调
    get_job_instance_status（与 BkJobService 轮询时取步骤逻辑一致），失败则 None
    """
    if ext_result and isinstance(ext_result.get("data"), dict):
        sid = _step_id_from_data_dict(ext_result["data"])
        if sid is not None:
            return sid
    try:
        from backend.flow.plugins.components.collections.common.base_service import BkJobService

        st = BkJobService.__status__(str(job_instance_id))
    except Exception:
        return None
    if not (isinstance(st, dict) and st.get("result") and isinstance(st.get("data"), dict)):
        return None
    return _step_id_from_data_dict(st["data"])


def _normalize_exec_ips(value: Any) -> Optional[List[Any]]:
    """
    仅当存在非空可序列化结构时返回列表，否则 None（不强求落库空列表）
    """
    if value is None:
        return None
    if isinstance(value, list) and len(value) > 0:
        return value
    return None


def try_resolve_cluster_id(kwargs: Optional[dict], global_data: Any) -> Optional[int]:
    """
    从活动 kwargs / 全局 global_data 中尝试解析 cluster_id，仅接受正整数；无则 None。

    兼容两种常见写法：
    1) 顶层 kwargs['cluster_id'] = 123
    2) 嵌套 kwargs['cluster'] 为 dict，内含 cluster_id 或 id（如 ExecActuatorKwargs.cluster、
       template_cluster 等），与 import_sqlfile_flow 中
       cluster={"cluster_id": cluster.id, "port": ...} 一致。
    """
    g = global_data if isinstance(global_data, dict) else {}
    for src in (kwargs or {}, g):
        if not isinstance(src, dict):
            continue
        cid = _as_positive_int(src.get("cluster_id"))
        if cid is not None:
            return cid
        inner = src.get("cluster")
        if isinstance(inner, dict):
            cid = _as_positive_int(inner.get("cluster_id"))
            if cid is not None:
                return cid
            cid = _as_positive_int(inner.get("id"))
            if cid is not None:
                return cid
    return None


def resolve_ticket_id_from_global_data(global_data: Any) -> Optional[int]:
    """从 global_data['uid'] 解析单据 ID，无单据或非法值时返回 None。"""
    if not isinstance(global_data, dict):
        return None
    return _as_positive_int(global_data.get("uid"))


def _extract_ip_cloud_pairs(exec_ips: Any, default_bk_cloud_id: int) -> List[tuple]:
    """
    将 exec_ips 归一化为 (bk_cloud_id, ip) 去重列表，兼容两种格式：
    1) ["1.1.1.1", "1.1.1.2", ...]                   → 全部用 default_bk_cloud_id
    2) [{"ip": "1.1.1.1", "bk_cloud_id": 0}, ...]    → 使用条目自带 bk_cloud_id，缺失时回退 default
    其它非法形态（如 None、空、非 list）一律返回空列表
    """
    if not isinstance(exec_ips, list) or not exec_ips:
        return []
    seen = set()
    pairs: List[tuple] = []
    for item in exec_ips:
        ip: Optional[str] = None
        cloud_id = default_bk_cloud_id
        if isinstance(item, str):
            ip = item.strip() or None
        elif isinstance(item, dict):
            raw_ip = item.get("ip")
            if isinstance(raw_ip, str):
                ip = raw_ip.strip() or None
            raw_cid = item.get("bk_cloud_id")
            cid_int = _int_id_or_none(raw_cid)
            if cid_int is not None:
                cloud_id = cid_int
        if not ip:
            continue
        key = (cloud_id, ip)
        if key in seen:
            continue
        seen.add(key)
        pairs.append(key)
    return pairs


def record_flow_exec_ips(
    *,
    ticket_id: Optional[int],
    root_id: str,
    bk_cloud_id: int,
    exec_ips: Any,
) -> None:
    """
    扁平化记录 (ip, bk_cloud_id, ticket_id, root_id) 关联关系，写入 flow_exec_ip_record。

    同一流程多节点常重复写同一批 IP，使用 bulk_create(ignore_conflicts=True)（底层 INSERT IGNORE /
    ON CONFLICT DO NOTHING）：与唯一键冲突的行被数据库直接跳过，不抛 IntegrityError、不按行刷重复键错误日志。
    唯一键为 (bk_cloud_id, ip, root_id)（不含可空的 ticket_id、不含 node_id）；单次调用内另由 _extract_ip_cloud_pairs 去重。

    仅真实异常（连库失败等）才 logger.warning，不影响主流程。
    """
    try:
        if not root_id:
            return
        pairs = _extract_ip_cloud_pairs(exec_ips, default_bk_cloud_id=bk_cloud_id)
        if not pairs:
            return
        records = [
            FlowExecIpRecord(
                ticket_id=ticket_id,
                root_id=root_id,
                bk_cloud_id=cloud_id,
                ip=ip,
            )
            for cloud_id, ip in pairs
        ]
        FlowExecIpRecord.objects.bulk_create(records, ignore_conflicts=True)
    except Exception as e:
        logger.warning(_("写入流程执行IP关系失败(已忽略,不影响任务执行): {}").format(str(e)))


def record_bk_job_instance(
    *,
    ticket_id: Optional[int],
    root_id: str,
    node_id: str,
    version_id: str,
    job_instance_id: int,
    node_name: str = "",
    component_code: str = "",
    cluster_id: Optional[int] = None,
    exec_ips: Any = None,
    step_instance_id: Optional[int] = None,
) -> None:
    """
    写入一条执行记录。ticket_id 为 None 表示无单据/直接起任务，与 FlowTree 一致，不使用假值占位。
    cluster_id、exec_ips、step_instance_id 为可选，无则存库为 NULL
    """
    FlowBkJobInstance.objects.create(
        ticket_id=ticket_id,
        root_id=root_id,
        node_id=node_id,
        version_id=version_id or "",
        job_instance_id=job_instance_id,
        step_instance_id=step_instance_id,
        node_name=node_name or "",
        component_code=component_code or "",
        cluster_id=cluster_id,
        exec_ips=_normalize_exec_ips(exec_ips),
    )
