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
from typing import Dict, Tuple

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_meta.models import Cluster
from backend.flow.utils.kafka.rebalance_throttle_util import (
    ABSOLUTE_MAX_THROTTLE_BYTES_PER_SEC,
    clear_throttle_override,
    get_rebalance_throttle_bounds,
    read_rebalance_state,
    resolve_and_validate_exec_ip,
    set_manual_throttle_rate,
)
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket

logger = logging.getLogger("root")


def _resolve_rebalance_ticket_context(ticket_id: int) -> Tuple[Ticket, Cluster, str]:
    """
    校验并解析Kafka rebalance单据的执行上下文：单据类型、关联集群、执行节点exec_ip。
    查进度/人工设限速/恢复自动调速三个工具共享同一套校验逻辑，不重复三份。
    """
    try:
        ticket = Ticket.objects.get(id=ticket_id)
    except Ticket.DoesNotExist:
        raise serializers.ValidationError(_("单据不存在: {}").format(ticket_id))

    if ticket.ticket_type != TicketType.KAFKA_REBALANCE:
        raise serializers.ValidationError(_("单据{}不是Kafka rebalance单据（类型：{}）").format(ticket_id, ticket.ticket_type))

    details = ticket.details or {}
    cluster_id = details.get("cluster_id")
    instance_list = details.get("instance_list") or []
    if not cluster_id or not instance_list:
        raise serializers.ValidationError(_("该单据缺少cluster_id或执行节点信息"))

    try:
        cluster = Cluster.objects.get(id=cluster_id)
    except Cluster.DoesNotExist:
        raise serializers.ValidationError(_("单据关联的集群不存在: {}").format(cluster_id))

    if cluster.bk_biz_id != ticket.bk_biz_id:
        raise serializers.ValidationError(_("单据业务与集群所属业务不一致，拒绝执行"))

    exec_ip = instance_list[0]["ip"]
    try:
        # 重新校验exec_ip确实属于该集群broker（不只是信任ticket.details里的字段），
        # 避免details被篡改或字段含义变化后，读取到非本集群机器上的任意文件
        resolve_and_validate_exec_ip(cluster_id, exec_ip)
    except ValueError as err:
        raise serializers.ValidationError(str(err))

    return ticket, cluster, exec_ip


def get_rebalance_progress(ticket_id: int) -> Dict:
    """
    查询 Kafka rebalance 单据的执行进度、当前限速、调速模式。
    进度/限速/调速模式由 dbactuator 写入执行节点本地的文件，通过 Job 平台远程读取。
    """
    _ticket, cluster, exec_ip = _resolve_rebalance_ticket_context(ticket_id)

    files = read_rebalance_state(exec_ip, cluster.bk_cloud_id, ticket_id)
    progress_raw = files.get("progress")
    if not progress_raw:
        return {
            "ticket_id": ticket_id,
            "status": "pending",
            "override_mode": files.get("override_mode", "auto"),
            "message": str(_("尚未开始或进度文件未生成")),
        }

    try:
        progress = json.loads(progress_raw)
    except (ValueError, TypeError):
        raise Exception(_("进度文件解析失败"))

    current_throttle_mib_s = None
    throttle_raw = files.get("throttle_rate")
    if throttle_raw:
        try:
            current_throttle_mib_s = round(int(throttle_raw.strip()) / 1024 / 1024, 1)
        except ValueError:
            pass

    return {
        "ticket_id": ticket_id,
        "current_topic": progress.get("current_topic", ""),
        "current": progress.get("current", 0),
        "total": progress.get("total", 0),
        "percent": progress.get("percent", 0),
        "status": progress.get("status", "unknown"),
        "current_throttle_mib_s": current_throttle_mib_s,
        "override_mode": files.get("override_mode", "auto"),
    }


def set_rebalance_throttle(ticket_id: int, throttle_mib_s: int) -> Dict:
    """
    人工设置Kafka rebalance单据的限速，并切换到manual模式——sidecar下一轮会跳过自动调速，
    避免刚设置的值被自动逻辑立刻覆盖回去。仍受MIN下限和（监控数据可用时）动态上限约束；
    监控数据暂不可用时退化用一个宽松的绝对值兜底，只拦截明显异常的输入。
    只允许对状态为in_progress的单据操作——单据已结束时设置限速没有意义。
    写限速和切换manual模式合并成一次远程脚本原子完成（见set_manual_throttle_rate），
    避免两次独立Job调用之间的网络往返给sidecar的自动调速留出插入窗口。
    """
    _ticket, cluster, exec_ip = _resolve_rebalance_ticket_context(ticket_id)

    files = read_rebalance_state(exec_ip, cluster.bk_cloud_id, ticket_id)
    progress_raw = files.get("progress")
    if not progress_raw:
        raise serializers.ValidationError(_("该单据rebalance尚未开始，无法设置限速"))
    try:
        progress = json.loads(progress_raw)
    except (ValueError, TypeError):
        raise Exception(_("进度文件解析失败"))
    if progress.get("status") != "in_progress":
        raise serializers.ValidationError(_("该单据当前状态为{}，只有in_progress状态才能设置限速").format(progress.get("status")))

    throttle_bytes_per_sec = int(throttle_mib_s) * 1024 * 1024

    bounds = get_rebalance_throttle_bounds(cluster.id)
    max_throttle_bytes_per_sec = (
        bounds["max_throttle_bytes_per_sec"] if bounds else ABSOLUTE_MAX_THROTTLE_BYTES_PER_SEC
    )

    try:
        set_manual_throttle_rate(
            exec_ip, cluster.bk_cloud_id, ticket_id, throttle_bytes_per_sec, max_throttle_bytes_per_sec
        )
    except ValueError as err:
        raise serializers.ValidationError(str(err))

    return {
        "ticket_id": ticket_id,
        "throttle_mib_s": round(throttle_bytes_per_sec / 1024 / 1024, 1),
        "override_mode": "manual",
        "message": str(_("已设置为人工限速模式，自动调速将暂停直到调用resume_rebalance_auto_throttle恢复")),
    }


def resume_rebalance_auto_throttle(ticket_id: int) -> Dict:
    """
    恢复Kafka rebalance单据的自动调速：删除throttle_override.txt（而不是写入"auto"内容）。
    manual模式=override文件存在，auto模式=文件不存在，语义唯一，不会有文件永久残留。
    不会立即触发一次调速计算——交回给sidecar在下一轮（最多2分钟内）按当前带宽利用率自动调整，
    避免在MCP工具里重复实现一遍调速决策逻辑。
    只允许对状态为in_progress的单据操作——单据已结束时恢复自动调速没有意义。
    """
    _ticket, cluster, exec_ip = _resolve_rebalance_ticket_context(ticket_id)

    files = read_rebalance_state(exec_ip, cluster.bk_cloud_id, ticket_id)
    progress_raw = files.get("progress")
    if not progress_raw:
        raise serializers.ValidationError(_("该单据rebalance尚未开始，无需恢复自动调速"))
    try:
        progress = json.loads(progress_raw)
    except (ValueError, TypeError):
        raise Exception(_("进度文件解析失败"))
    if progress.get("status") != "in_progress":
        raise serializers.ValidationError(_("该单据当前状态为{}，只有in_progress状态才能恢复自动调速").format(progress.get("status")))

    clear_throttle_override(exec_ip, cluster.bk_cloud_id, ticket_id)

    return {
        "ticket_id": ticket_id,
        "override_mode": "auto",
        "message": str(_("已恢复自动调速，下一轮检查（最多2分钟内）将按带宽利用率自动调整限速")),
    }
