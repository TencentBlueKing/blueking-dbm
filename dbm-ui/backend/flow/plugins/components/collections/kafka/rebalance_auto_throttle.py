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

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow import StaticIntervalGenerator

from backend.flow.models import FlowTree
from backend.flow.plugins.components.collections.common.sidecar_service_abc import SidecarServiceABC
from backend.flow.utils.kafka.rebalance_throttle_util import (
    HIGH_WATERMARK_PCT,
    LOW_WATERMARK_PCT,
    MIN_THROTTLE_BYTES_PER_SEC,
    STEP_BYTES_PER_SEC,
    get_rebalance_throttle_bounds,
    read_rebalance_state,
    resolve_and_validate_exec_ip,
    write_remote_throttle_rate,
)

logger = logging.getLogger("flow")


class KafkaRebalanceAutoThrottleService(SidecarServiceABC):
    """
    Kafka rebalance期间的限速自动调节旁路服务：
    每2分钟检查一次集群带宽利用率，超过85%则降速50MB/s（下限50MB/s），
    低于80%则提速50MB/s（上限动态计算，取参与rebalance的broker实测带宽最小值的
    MAX_THROTTLE_BANDWIDTH_RATIO，留一部分给客户端流量），80%-85%之间维持不变。
    通过kafka_rebalance_control_set_throttle人工设置过限速后会切换到manual模式，本服务跳过
    自动调速，直到调用kafka_rebalance_control_resume_auto_throttle恢复。
    """

    interval = StaticIntervalGenerator(120)

    def sidecar_func(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")

        cluster_id = kwargs["cluster_id"]
        exec_ip = kwargs["exec_ip"]
        root_id = global_data["job_root_id"]

        resolved = self._resolve_ticket_and_cloud(cluster_id, exec_ip, root_id)
        if resolved is None:
            return True
        ticket_id, bk_cloud_id = resolved

        files = self._resolve_in_progress_state(exec_ip, bk_cloud_id, ticket_id)
        if files is None:
            return True

        current_rate = self._resolve_current_rate(files)
        if current_rate is None:
            return True

        bounds = self._resolve_bounds(cluster_id)
        if bounds is None:
            return True

        self._apply_throttle_decision(exec_ip, bk_cloud_id, ticket_id, current_rate, bounds)
        return True

    def _resolve_ticket_and_cloud(self, cluster_id, exec_ip, root_id):
        """
        解析单据ID，并重新校验exec_ip确实属于该集群broker（不信任kwargs里传入的bk_cloud_id），
        避免未来该Component被复用/传参出错时对任意IP执行高权限远程读写。失败时返回None（已记录日志）。
        """
        try:
            flow_tree = FlowTree.objects.get(root_id=root_id)
            ticket_id = int(flow_tree.uid)
        except (FlowTree.DoesNotExist, TypeError, ValueError) as err:
            self.log_error(_("获取单据ID失败，跳过本轮自动调速检查：{}").format(err))
            return None

        try:
            bk_cloud_id = resolve_and_validate_exec_ip(cluster_id, exec_ip)
        except Exception as err:
            self.log_error(_("exec_ip校验失败，跳过本轮自动调速检查：{}").format(err))
            return None

        return ticket_id, bk_cloud_id

    def _resolve_in_progress_state(self, exec_ip, bk_cloud_id, ticket_id):
        """
        读取rebalance进度/限速/调速模式文件，并校验当前确实处于需要自动调速的in_progress状态。
        不满足条件时返回None（已记录跳过原因），否则返回files字典供后续调速判断使用。
        """
        try:
            files = read_rebalance_state(exec_ip, bk_cloud_id, ticket_id)
        except Exception as err:
            self.log_warning(_("读取rebalance进度/限速/调速模式失败，跳过本轮检查：{}").format(err))
            return None

        progress_raw = files.get("progress")
        if not progress_raw:
            self.log_info(_("rebalance进度文件尚未生成，跳过本轮检查"))
            return None

        try:
            progress = json.loads(progress_raw)
        except (ValueError, TypeError) as err:
            self.log_warning(_("解析rebalance进度文件失败，跳过本轮检查：{}").format(err))
            return None

        # current>=total时即便status暂时仍读到in_progress（actuator写done.list和progress.json
        # 之间存在极短的时间窗口），也不再调速——避免在任务即将/刚刚结束的边界上做一次没有意义的调整
        if progress.get("status") != "in_progress" or progress.get("current", 0) >= progress.get("total", 0):
            self.log_info(_("rebalance当前状态为{}，无需自动调速").format(progress.get("status")))
            return None

        return files

    def _resolve_current_rate(self, files):
        """
        解析当前限速值。人工限速模式(manual)下跳过自动调速；限速文件缺失/内容非法/异常值也跳过。
        不满足条件时返回None（已记录跳过原因）。
        """
        if files.get("override_mode") == "manual":
            self.log_info(_("当前处于人工限速模式，跳过自动调速（调用resume_rebalance_auto_throttle可恢复自动调速）"))
            return None

        throttle_raw = files.get("throttle_rate")
        if not throttle_raw:
            self.log_warning(_("限速文件不存在，跳过本轮检查"))
            return None

        try:
            current_rate = int(throttle_raw.strip())
        except ValueError as err:
            self.log_warning(_("限速值格式非法（{}），跳过本轮检查：{}").format(throttle_raw, err))
            return None

        if current_rate <= 0:
            self.log_warning(_("当前限速值异常（{}），跳过本轮检查，避免基于脏数据继续调整").format(current_rate))
            return None

        return current_rate

    def _resolve_bounds(self, cluster_id):
        """
        查询本轮调速所需的带宽利用率与动态限速上限。监控数据不可用时返回None（已记录跳过原因）。
        """
        try:
            bounds = get_rebalance_throttle_bounds(cluster_id)
        except Exception as err:
            self.log_warning(_("查询带宽利用率失败，跳过本轮检查：{}").format(err))
            return None

        if bounds is None:
            self.log_info(_("暂无带宽监控数据，跳过本轮自动调速检查"))
            return None

        return bounds

    def _apply_throttle_decision(self, exec_ip, bk_cloud_id, ticket_id, current_rate, bounds):
        """
        根据带宽利用率水位计算新的限速值，超过高水位降速、低于低水位提速，区间内维持不变。
        """
        utilization_pct = bounds["utilization_pct"]
        max_throttle_bytes_per_sec = bounds["max_throttle_bytes_per_sec"]

        self.log_info(
            _("当前带宽利用率：{:.1f}%，当前限速：{}MB/s，动态上限：{}MB/s").format(
                utilization_pct, current_rate // (1024 * 1024), max_throttle_bytes_per_sec // (1024 * 1024)
            )
        )

        new_rate = current_rate
        if utilization_pct > HIGH_WATERMARK_PCT:
            new_rate = max(current_rate - STEP_BYTES_PER_SEC, MIN_THROTTLE_BYTES_PER_SEC)
        elif utilization_pct < LOW_WATERMARK_PCT:
            new_rate = min(current_rate + STEP_BYTES_PER_SEC, max_throttle_bytes_per_sec)

        if new_rate == current_rate:
            return

        try:
            write_remote_throttle_rate(exec_ip, bk_cloud_id, ticket_id, new_rate, max_throttle_bytes_per_sec)
            self.log_info(
                _("带宽利用率{:.1f}%触发自动调速：{}MB/s -> {}MB/s").format(
                    utilization_pct, current_rate // (1024 * 1024), new_rate // (1024 * 1024)
                )
            )
        except Exception as err:
            self.log_warning(_("更新限速失败，将在下一轮重试：{}").format(err))


class KafkaRebalanceAutoThrottleComponent(Component):
    name = __name__
    code = "sidecar_kafka_rebalance_auto_throttle"
    bound_service = KafkaRebalanceAutoThrottleService
