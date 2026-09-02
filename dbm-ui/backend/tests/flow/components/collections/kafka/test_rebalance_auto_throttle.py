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
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.flow.plugins.components.collections.kafka import rebalance_auto_throttle as mod

# 测试里代表"本轮动态算出来的上限"，跟真实带宽无关，只是给clamp逻辑一个具体数值
_GENERIC_MAX_THROTTLE = 1000 * 1024 * 1024


class FakeData:
    def __init__(self, inputs):
        self.inputs = inputs
        self.outputs = SimpleNamespace()

    def get_one_of_inputs(self, key):
        return self.inputs.get(key)


def _make_data(cluster_id=100, exec_ip="127.0.0.1", root_id="root123"):
    return FakeData(
        {
            "kwargs": {"cluster_id": cluster_id, "exec_ip": exec_ip},
            "global_data": {"job_root_id": root_id},
        }
    )


def _make_service():
    svc = mod.KafkaRebalanceAutoThrottleService()
    svc.log_info = MagicMock()
    svc.log_warning = MagicMock()
    svc.log_error = MagicMock()
    return svc


def _progress(status="in_progress", current_topic="t1", current=1, total=3, percent=33.3):
    return json.dumps(
        {"status": status, "current_topic": current_topic, "current": current, "total": total, "percent": percent}
    )


def _bounds(utilization_pct, max_throttle_bytes_per_sec=_GENERIC_MAX_THROTTLE):
    return {"utilization_pct": utilization_pct, "max_throttle_bytes_per_sec": max_throttle_bytes_per_sec}


class TestSidecarFuncStrategy:
    @patch.object(mod, "write_remote_throttle_rate")
    @patch.object(mod, "get_rebalance_throttle_bounds", return_value=_bounds(90.0))
    @patch.object(mod, "read_rebalance_state")
    @patch.object(mod, "resolve_and_validate_exec_ip", return_value=0)
    @patch.object(mod, "FlowTree")
    def test_high_utilization_decreases_rate(self, mock_flow_tree, mock_resolve, mock_read, mock_bounds, mock_write):
        mock_flow_tree.objects.get.return_value = MagicMock(uid="267")
        mock_read.return_value = {"progress": _progress(), "throttle_rate": str(150 * 1024 * 1024)}

        svc = _make_service()
        assert svc.sidecar_func(_make_data(), None) is True

        mock_write.assert_called_once_with("127.0.0.1", 0, 267, 100 * 1024 * 1024, _GENERIC_MAX_THROTTLE)

    @patch.object(mod, "write_remote_throttle_rate")
    @patch.object(mod, "get_rebalance_throttle_bounds", return_value=_bounds(90.0))
    @patch.object(mod, "read_rebalance_state")
    @patch.object(mod, "resolve_and_validate_exec_ip", return_value=0)
    @patch.object(mod, "FlowTree")
    def test_decrease_is_clamped_to_min(self, mock_flow_tree, mock_resolve, mock_read, mock_bounds, mock_write):
        mock_flow_tree.objects.get.return_value = MagicMock(uid="267")
        # 起始值比MIN高一点但不够一个完整STEP：MIN(50MB)+30MB=80MB，直接减STEP会变成30MB(<MIN)，
        # 必须验证被钳制到MIN而不是30MB。若从MIN本身开始，new_rate会等于current_rate，
        # 命中sidecar的"未变化则不写"早退路径，测不出钳制生效。
        starting_rate = mod.MIN_THROTTLE_BYTES_PER_SEC + 30 * 1024 * 1024
        mock_read.return_value = {"progress": _progress(), "throttle_rate": str(starting_rate)}

        svc = _make_service()
        svc.sidecar_func(_make_data(), None)

        mock_write.assert_called_once_with("127.0.0.1", 0, 267, mod.MIN_THROTTLE_BYTES_PER_SEC, _GENERIC_MAX_THROTTLE)

    @patch.object(mod, "write_remote_throttle_rate")
    @patch.object(mod, "get_rebalance_throttle_bounds", return_value=_bounds(50.0, 300 * 1024 * 1024))
    @patch.object(mod, "read_rebalance_state")
    @patch.object(mod, "resolve_and_validate_exec_ip", return_value=0)
    @patch.object(mod, "FlowTree")
    def test_low_utilization_increases_rate(self, mock_flow_tree, mock_resolve, mock_read, mock_bounds, mock_write):
        mock_flow_tree.objects.get.return_value = MagicMock(uid="267")
        mock_read.return_value = {"progress": _progress(), "throttle_rate": str(150 * 1024 * 1024)}

        svc = _make_service()
        svc.sidecar_func(_make_data(), None)

        mock_write.assert_called_once_with("127.0.0.1", 0, 267, 200 * 1024 * 1024, 300 * 1024 * 1024)

    @patch.object(mod, "write_remote_throttle_rate")
    @patch.object(mod, "read_rebalance_state")
    @patch.object(mod, "resolve_and_validate_exec_ip", return_value=0)
    @patch.object(mod, "FlowTree")
    def test_increase_is_clamped_to_dynamic_max(self, mock_flow_tree, mock_resolve, mock_read, mock_write):
        mock_flow_tree.objects.get.return_value = MagicMock(uid="267")
        # 动态上限本轮算出来是220MB/s；起始值比它低一点但不够一个完整STEP，直接加STEP会超过这个上限，
        # 必须验证被钳制到动态上限而不是MIN_THROTTLE~MAX这种写死区间。从上限本身开始会命中
        # "未变化则不写"早退路径，测不出钳制生效。
        dynamic_max = 220 * 1024 * 1024
        starting_rate = dynamic_max - 30 * 1024 * 1024
        with patch.object(mod, "get_rebalance_throttle_bounds", return_value=_bounds(50.0, dynamic_max)):
            mock_read.return_value = {"progress": _progress(), "throttle_rate": str(starting_rate)}

            svc = _make_service()
            svc.sidecar_func(_make_data(), None)

        mock_write.assert_called_once_with("127.0.0.1", 0, 267, dynamic_max, dynamic_max)

    @patch.object(mod, "write_remote_throttle_rate")
    @patch.object(mod, "get_rebalance_throttle_bounds", return_value=_bounds(82.0))
    @patch.object(mod, "read_rebalance_state")
    @patch.object(mod, "resolve_and_validate_exec_ip", return_value=0)
    @patch.object(mod, "FlowTree")
    def test_within_watermark_band_does_not_write(
        self, mock_flow_tree, mock_resolve, mock_read, mock_bounds, mock_write
    ):
        mock_flow_tree.objects.get.return_value = MagicMock(uid="267")
        mock_read.return_value = {"progress": _progress(), "throttle_rate": str(150 * 1024 * 1024)}

        svc = _make_service()
        svc.sidecar_func(_make_data(), None)

        mock_write.assert_not_called()


class TestSidecarFuncOverrideMode:
    @patch.object(mod, "write_remote_throttle_rate")
    @patch.object(mod, "get_rebalance_throttle_bounds")
    @patch.object(mod, "read_rebalance_state")
    @patch.object(mod, "resolve_and_validate_exec_ip", return_value=0)
    @patch.object(mod, "FlowTree")
    def test_manual_override_skips_auto_adjustment(
        self, mock_flow_tree, mock_resolve, mock_read, mock_bounds, mock_write
    ):
        # 人工通过kafka_rebalance_control_set_throttle设置过限速后，override_mode会是"manual"，
        # sidecar必须跳过本轮调速，不能让自动逻辑立刻把刚设置的值覆盖回去
        mock_flow_tree.objects.get.return_value = MagicMock(uid="267")
        mock_read.return_value = {
            "progress": _progress(),
            "throttle_rate": str(150 * 1024 * 1024),
            "override_mode": "manual",
        }

        svc = _make_service()
        result = svc.sidecar_func(_make_data(), None)

        assert result is True
        mock_bounds.assert_not_called()
        mock_write.assert_not_called()

    @patch.object(mod, "write_remote_throttle_rate")
    @patch.object(mod, "get_rebalance_throttle_bounds", return_value=_bounds(90.0))
    @patch.object(mod, "read_rebalance_state")
    @patch.object(mod, "resolve_and_validate_exec_ip", return_value=0)
    @patch.object(mod, "FlowTree")
    def test_auto_mode_still_adjusts(self, mock_flow_tree, mock_resolve, mock_read, mock_bounds, mock_write):
        mock_flow_tree.objects.get.return_value = MagicMock(uid="267")
        mock_read.return_value = {
            "progress": _progress(),
            "throttle_rate": str(150 * 1024 * 1024),
            "override_mode": "auto",
        }

        svc = _make_service()
        svc.sidecar_func(_make_data(), None)

        mock_write.assert_called_once_with("127.0.0.1", 0, 267, 100 * 1024 * 1024, _GENERIC_MAX_THROTTLE)


class TestSidecarFuncGuards:
    @patch.object(mod, "write_remote_throttle_rate")
    @patch.object(mod, "get_rebalance_throttle_bounds")
    @patch.object(mod, "read_rebalance_state")
    @patch.object(mod, "resolve_and_validate_exec_ip", return_value=0)
    @patch.object(mod, "FlowTree")
    def test_non_positive_current_rate_skips(self, mock_flow_tree, mock_resolve, mock_read, mock_bounds, mock_write):
        mock_flow_tree.objects.get.return_value = MagicMock(uid="267")
        mock_read.return_value = {"progress": _progress(), "throttle_rate": "0"}

        svc = _make_service()
        svc.sidecar_func(_make_data(), None)

        mock_bounds.assert_not_called()
        mock_write.assert_not_called()

    @patch.object(mod, "get_rebalance_throttle_bounds")
    @patch.object(mod, "read_rebalance_state")
    @patch.object(mod, "resolve_and_validate_exec_ip", return_value=0)
    @patch.object(mod, "FlowTree")
    def test_status_not_in_progress_skips(self, mock_flow_tree, mock_resolve, mock_read, mock_bounds):
        mock_flow_tree.objects.get.return_value = MagicMock(uid="267")
        mock_read.return_value = {"progress": _progress(status="completed"), "throttle_rate": "104857600"}

        svc = _make_service()
        svc.sidecar_func(_make_data(), None)

        mock_bounds.assert_not_called()

    @patch.object(mod, "get_rebalance_throttle_bounds")
    @patch.object(mod, "read_rebalance_state")
    @patch.object(mod, "resolve_and_validate_exec_ip", return_value=0)
    @patch.object(mod, "FlowTree")
    def test_current_reaches_total_skips_even_if_status_still_in_progress(
        self, mock_flow_tree, mock_resolve, mock_read, mock_bounds
    ):
        # actuator写done.list和progress.json之间存在极短时间窗口，可能读到current>=total但
        # status仍是in_progress的瞬时状态，这种边界情况也不该再调速
        mock_flow_tree.objects.get.return_value = MagicMock(uid="267")
        mock_read.return_value = {
            "progress": _progress(status="in_progress", current=3, total=3),
            "throttle_rate": "104857600",
        }

        svc = _make_service()
        svc.sidecar_func(_make_data(), None)

        mock_bounds.assert_not_called()

    @patch.object(mod, "get_rebalance_throttle_bounds")
    @patch.object(mod, "read_rebalance_state")
    @patch.object(mod, "resolve_and_validate_exec_ip", return_value=0)
    @patch.object(mod, "FlowTree")
    def test_progress_missing_skips(self, mock_flow_tree, mock_resolve, mock_read, mock_bounds):
        mock_flow_tree.objects.get.return_value = MagicMock(uid="267")
        mock_read.return_value = {"progress": None, "throttle_rate": None}

        svc = _make_service()
        svc.sidecar_func(_make_data(), None)

        mock_read.assert_called_once()
        mock_bounds.assert_not_called()

    @patch.object(mod, "read_rebalance_state")
    def test_invalid_progress_json_skips(self, mock_read):
        mock_read.return_value = {"progress": "not-json", "throttle_rate": "104857600"}

        with patch.object(mod, "FlowTree") as mock_flow_tree, patch.object(
            mod, "resolve_and_validate_exec_ip", return_value=0
        ):
            mock_flow_tree.objects.get.return_value = MagicMock(uid="267")
            svc = _make_service()
            result = svc.sidecar_func(_make_data(), None)

        assert result is True

    @patch.object(mod, "write_remote_throttle_rate")
    @patch.object(mod, "get_rebalance_throttle_bounds", return_value=None)
    @patch.object(mod, "read_rebalance_state")
    @patch.object(mod, "resolve_and_validate_exec_ip", return_value=0)
    @patch.object(mod, "FlowTree")
    def test_no_monitoring_data_skips(self, mock_flow_tree, mock_resolve, mock_read, mock_bounds, mock_write):
        mock_flow_tree.objects.get.return_value = MagicMock(uid="267")
        mock_read.return_value = {"progress": _progress(), "throttle_rate": "104857600"}

        svc = _make_service()
        svc.sidecar_func(_make_data(), None)

        mock_write.assert_not_called()

    @patch.object(mod, "read_rebalance_state")
    @patch.object(mod, "resolve_and_validate_exec_ip", side_effect=ValueError("127.0.0.1不是集群kafka.test.db的broker节点"))
    @patch.object(mod, "FlowTree")
    def test_exec_ip_validation_failure_skips_before_any_remote_read(self, mock_flow_tree, mock_resolve, mock_read):
        mock_flow_tree.objects.get.return_value = MagicMock(uid="267")

        svc = _make_service()
        result = svc.sidecar_func(_make_data(), None)

        assert result is True
        mock_read.assert_not_called()

    @patch.object(mod, "resolve_and_validate_exec_ip")
    @patch.object(mod, "FlowTree")
    def test_flow_tree_missing_skips(self, mock_flow_tree, mock_resolve):
        mock_flow_tree.DoesNotExist = Exception
        mock_flow_tree.objects.get.side_effect = mock_flow_tree.DoesNotExist

        svc = _make_service()
        result = svc.sidecar_func(_make_data(), None)

        assert result is True
        mock_resolve.assert_not_called()
