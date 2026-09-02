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
# 本文件只测试get_rebalance_progress()的校验/编排逻辑，Ticket/Cluster均通过mock ORM manager隔离，无需django_db标记。
from unittest.mock import MagicMock, patch

import pytest
from rest_framework import serializers

from backend.dbm_aiagent.mcp_tools.kafka.impl import kafka_rebalance_control as mod
from backend.ticket.constants import TicketType


def _make_ticket(ticket_type=TicketType.KAFKA_REBALANCE, bk_biz_id=1, details=None):
    return MagicMock(ticket_type=ticket_type, bk_biz_id=bk_biz_id, details=details or {})


def _make_cluster(bk_biz_id=1, bk_cloud_id=0):
    return MagicMock(bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id, immute_domain="kafka.test.db")


class TestGetRebalanceProgressValidation:
    @patch.object(mod, "Ticket")
    def test_ticket_not_found(self, mock_ticket_cls):
        mock_ticket_cls.DoesNotExist = Exception
        mock_ticket_cls.objects.get.side_effect = mock_ticket_cls.DoesNotExist

        with pytest.raises(serializers.ValidationError, match="单据不存在"):
            mod.get_rebalance_progress(ticket_id=999)

    @patch.object(mod, "Ticket")
    def test_wrong_ticket_type_rejected(self, mock_ticket_cls):
        mock_ticket_cls.objects.get.return_value = _make_ticket(ticket_type=TicketType.PULSAR_REPLACE)

        with pytest.raises(serializers.ValidationError, match="不是Kafka rebalance单据"):
            mod.get_rebalance_progress(ticket_id=1)

    @patch.object(mod, "Ticket")
    def test_missing_cluster_id_rejected(self, mock_ticket_cls):
        mock_ticket_cls.objects.get.return_value = _make_ticket(details={"instance_list": [{"ip": "127.0.0.1"}]})

        with pytest.raises(serializers.ValidationError, match="缺少cluster_id或执行节点信息"):
            mod.get_rebalance_progress(ticket_id=1)

    @patch.object(mod, "Ticket")
    def test_missing_instance_list_rejected(self, mock_ticket_cls):
        mock_ticket_cls.objects.get.return_value = _make_ticket(details={"cluster_id": 100})

        with pytest.raises(serializers.ValidationError, match="缺少cluster_id或执行节点信息"):
            mod.get_rebalance_progress(ticket_id=1)

    @patch.object(mod, "Cluster")
    @patch.object(mod, "Ticket")
    def test_cluster_not_found_rejected(self, mock_ticket_cls, mock_cluster_cls):
        mock_ticket_cls.objects.get.return_value = _make_ticket(
            details={"cluster_id": 100, "instance_list": [{"ip": "127.0.0.1"}]}
        )
        mock_cluster_cls.DoesNotExist = Exception
        mock_cluster_cls.objects.get.side_effect = mock_cluster_cls.DoesNotExist

        with pytest.raises(serializers.ValidationError, match="集群不存在"):
            mod.get_rebalance_progress(ticket_id=1)

    @patch.object(mod, "Cluster")
    @patch.object(mod, "Ticket")
    def test_biz_mismatch_rejected(self, mock_ticket_cls, mock_cluster_cls):
        mock_ticket_cls.objects.get.return_value = _make_ticket(
            bk_biz_id=1, details={"cluster_id": 100, "instance_list": [{"ip": "127.0.0.1"}]}
        )
        mock_cluster_cls.objects.get.return_value = _make_cluster(bk_biz_id=2)

        with pytest.raises(serializers.ValidationError, match="业务与集群所属业务不一致"):
            mod.get_rebalance_progress(ticket_id=1)

    @patch.object(mod, "resolve_and_validate_exec_ip", side_effect=ValueError("127.0.0.1不是集群kafka.test.db的broker节点"))
    @patch.object(mod, "Cluster")
    @patch.object(mod, "Ticket")
    def test_exec_ip_not_a_broker_rejected(self, mock_ticket_cls, mock_cluster_cls, mock_resolve):
        mock_ticket_cls.objects.get.return_value = _make_ticket(
            details={"cluster_id": 100, "instance_list": [{"ip": "127.0.0.1"}]}
        )
        mock_cluster_cls.objects.get.return_value = _make_cluster()

        with pytest.raises(serializers.ValidationError, match="不是集群"):
            mod.get_rebalance_progress(ticket_id=1)


class TestGetRebalanceProgressHappyPath:
    @patch.object(mod, "read_rebalance_state")
    @patch.object(mod, "resolve_and_validate_exec_ip", return_value=0)
    @patch.object(mod, "Cluster")
    @patch.object(mod, "Ticket")
    def test_returns_progress_and_throttle(self, mock_ticket_cls, mock_cluster_cls, mock_resolve, mock_read):
        mock_ticket_cls.objects.get.return_value = _make_ticket(
            details={"cluster_id": 100, "instance_list": [{"ip": "127.0.0.1"}]}
        )
        mock_cluster_cls.objects.get.return_value = _make_cluster()
        mock_read.return_value = {
            "progress": '{"status": "in_progress", "current_topic": "t1", "current": 2, "total": 5, "percent": 40.0}',
            "throttle_rate": str(100 * 1024 * 1024),
            "override_mode": "auto",
        }

        result = mod.get_rebalance_progress(ticket_id=1)

        assert result["status"] == "in_progress"
        assert result["current_topic"] == "t1"
        assert result["current"] == 2
        assert result["total"] == 5
        assert result["current_throttle_mib_s"] == 100.0
        assert result["override_mode"] == "auto"

    @patch.object(mod, "read_rebalance_state")
    @patch.object(mod, "resolve_and_validate_exec_ip", return_value=0)
    @patch.object(mod, "Cluster")
    @patch.object(mod, "Ticket")
    def test_progress_not_yet_generated_returns_pending(
        self, mock_ticket_cls, mock_cluster_cls, mock_resolve, mock_read
    ):
        mock_ticket_cls.objects.get.return_value = _make_ticket(
            details={"cluster_id": 100, "instance_list": [{"ip": "127.0.0.1"}]}
        )
        mock_cluster_cls.objects.get.return_value = _make_cluster()
        mock_read.return_value = {"progress": None, "throttle_rate": None, "override_mode": "auto"}

        result = mod.get_rebalance_progress(ticket_id=1)

        assert result == {
            "ticket_id": 1,
            "status": "pending",
            "override_mode": "auto",
            "message": "尚未开始或进度文件未生成",
        }

    @patch.object(mod, "read_rebalance_state")
    @patch.object(mod, "resolve_and_validate_exec_ip", return_value=0)
    @patch.object(mod, "Cluster")
    @patch.object(mod, "Ticket")
    def test_invalid_progress_json_raises(self, mock_ticket_cls, mock_cluster_cls, mock_resolve, mock_read):
        mock_ticket_cls.objects.get.return_value = _make_ticket(
            details={"cluster_id": 100, "instance_list": [{"ip": "127.0.0.1"}]}
        )
        mock_cluster_cls.objects.get.return_value = _make_cluster()
        mock_read.return_value = {"progress": "not-json", "throttle_rate": None}

        with pytest.raises(Exception, match="进度文件解析失败"):
            mod.get_rebalance_progress(ticket_id=1)

    @patch.object(mod, "read_rebalance_state")
    @patch.object(mod, "resolve_and_validate_exec_ip", return_value=0)
    @patch.object(mod, "Cluster")
    @patch.object(mod, "Ticket")
    def test_invalid_throttle_value_does_not_break_response(
        self, mock_ticket_cls, mock_cluster_cls, mock_resolve, mock_read
    ):
        mock_ticket_cls.objects.get.return_value = _make_ticket(
            details={"cluster_id": 100, "instance_list": [{"ip": "127.0.0.1"}]}
        )
        mock_cluster_cls.objects.get.return_value = _make_cluster()
        mock_read.return_value = {
            "progress": '{"status": "in_progress"}',
            "throttle_rate": "not-a-number",
        }

        result = mod.get_rebalance_progress(ticket_id=1)

        assert result["current_throttle_mib_s"] is None


def _resolved(mock_ticket_cls, mock_cluster_cls, mock_resolve, cluster=None):
    mock_ticket_cls.objects.get.return_value = _make_ticket(
        details={"cluster_id": 100, "instance_list": [{"ip": "127.0.0.1"}]}
    )
    mock_cluster_cls.objects.get.return_value = cluster or _make_cluster()
    mock_resolve.return_value = 0


class TestSetRebalanceThrottle:
    @patch.object(mod, "read_rebalance_state")
    @patch.object(mod, "resolve_and_validate_exec_ip")
    @patch.object(mod, "Cluster")
    @patch.object(mod, "Ticket")
    def test_rejects_when_not_started(self, mock_ticket_cls, mock_cluster_cls, mock_resolve, mock_read):
        _resolved(mock_ticket_cls, mock_cluster_cls, mock_resolve)
        mock_read.return_value = {"progress": None, "throttle_rate": None, "override_mode": "auto"}

        with pytest.raises(serializers.ValidationError, match="尚未开始"):
            mod.set_rebalance_throttle(ticket_id=1, throttle_mib_s=100)

    @patch.object(mod, "read_rebalance_state")
    @patch.object(mod, "resolve_and_validate_exec_ip")
    @patch.object(mod, "Cluster")
    @patch.object(mod, "Ticket")
    def test_rejects_when_status_not_in_progress(self, mock_ticket_cls, mock_cluster_cls, mock_resolve, mock_read):
        _resolved(mock_ticket_cls, mock_cluster_cls, mock_resolve)
        mock_read.return_value = {
            "progress": '{"status": "completed"}',
            "throttle_rate": "104857600",
            "override_mode": "auto",
        }

        with pytest.raises(serializers.ValidationError, match="只有in_progress状态才能设置限速"):
            mod.set_rebalance_throttle(ticket_id=1, throttle_mib_s=100)

    @patch.object(mod, "read_rebalance_state")
    @patch.object(mod, "resolve_and_validate_exec_ip")
    @patch.object(mod, "Cluster")
    @patch.object(mod, "Ticket")
    def test_invalid_progress_json_raises(self, mock_ticket_cls, mock_cluster_cls, mock_resolve, mock_read):
        _resolved(mock_ticket_cls, mock_cluster_cls, mock_resolve)
        mock_read.return_value = {"progress": "not-json", "throttle_rate": None, "override_mode": "auto"}

        with pytest.raises(Exception, match="进度文件解析失败"):
            mod.set_rebalance_throttle(ticket_id=1, throttle_mib_s=100)

    @patch.object(mod, "set_manual_throttle_rate")
    @patch.object(mod, "get_rebalance_throttle_bounds")
    @patch.object(mod, "read_rebalance_state")
    @patch.object(mod, "resolve_and_validate_exec_ip")
    @patch.object(mod, "Cluster")
    @patch.object(mod, "Ticket")
    def test_writes_rate_and_switches_to_manual(
        self, mock_ticket_cls, mock_cluster_cls, mock_resolve, mock_read, mock_bounds, mock_set_rate
    ):
        _resolved(mock_ticket_cls, mock_cluster_cls, mock_resolve)
        mock_read.return_value = {
            "progress": '{"status": "in_progress"}',
            "throttle_rate": "104857600",
            "override_mode": "auto",
        }
        mock_bounds.return_value = {"utilization_pct": 10.0, "max_throttle_bytes_per_sec": 300 * 1024 * 1024}

        result = mod.set_rebalance_throttle(ticket_id=1, throttle_mib_s=150)

        # 写限速和切换manual模式必须是同一次调用（set_manual_throttle_rate内部合并成一次远程脚本），
        # 不能拆成两次独立调用——那样两次写入之间会留出sidecar插入一次自动调速的窗口
        mock_set_rate.assert_called_once_with("127.0.0.1", 0, 1, 150 * 1024 * 1024, 300 * 1024 * 1024)
        assert result["throttle_mib_s"] == 150.0
        assert result["override_mode"] == "manual"

    @patch.object(mod, "set_manual_throttle_rate")
    @patch.object(mod, "get_rebalance_throttle_bounds", return_value=None)
    @patch.object(mod, "read_rebalance_state")
    @patch.object(mod, "resolve_and_validate_exec_ip")
    @patch.object(mod, "Cluster")
    @patch.object(mod, "Ticket")
    def test_falls_back_to_absolute_max_when_no_monitoring_data(
        self, mock_ticket_cls, mock_cluster_cls, mock_resolve, mock_read, mock_bounds, mock_set_rate
    ):
        _resolved(mock_ticket_cls, mock_cluster_cls, mock_resolve)
        mock_read.return_value = {
            "progress": '{"status": "in_progress"}',
            "throttle_rate": "104857600",
            "override_mode": "auto",
        }

        mod.set_rebalance_throttle(ticket_id=1, throttle_mib_s=150)

        mock_set_rate.assert_called_once_with(
            "127.0.0.1", 0, 1, 150 * 1024 * 1024, mod.ABSOLUTE_MAX_THROTTLE_BYTES_PER_SEC
        )

    @patch.object(mod, "set_manual_throttle_rate", side_effect=ValueError("throttle_rate超出合法范围"))
    @patch.object(mod, "get_rebalance_throttle_bounds")
    @patch.object(mod, "read_rebalance_state")
    @patch.object(mod, "resolve_and_validate_exec_ip")
    @patch.object(mod, "Cluster")
    @patch.object(mod, "Ticket")
    def test_out_of_range_rate_becomes_validation_error(
        self, mock_ticket_cls, mock_cluster_cls, mock_resolve, mock_read, mock_bounds, mock_set_rate
    ):
        _resolved(mock_ticket_cls, mock_cluster_cls, mock_resolve)
        mock_read.return_value = {
            "progress": '{"status": "in_progress"}',
            "throttle_rate": "104857600",
            "override_mode": "auto",
        }
        mock_bounds.return_value = {"utilization_pct": 10.0, "max_throttle_bytes_per_sec": 300 * 1024 * 1024}

        with pytest.raises(serializers.ValidationError, match="超出合法范围"):
            mod.set_rebalance_throttle(ticket_id=1, throttle_mib_s=1)


class TestResumeRebalanceAutoThrottle:
    @patch.object(mod, "read_rebalance_state")
    @patch.object(mod, "resolve_and_validate_exec_ip")
    @patch.object(mod, "Cluster")
    @patch.object(mod, "Ticket")
    def test_rejects_when_not_started(self, mock_ticket_cls, mock_cluster_cls, mock_resolve, mock_read):
        _resolved(mock_ticket_cls, mock_cluster_cls, mock_resolve)
        mock_read.return_value = {"progress": None, "throttle_rate": None, "override_mode": "manual"}

        with pytest.raises(serializers.ValidationError, match="尚未开始"):
            mod.resume_rebalance_auto_throttle(ticket_id=1)

    @patch.object(mod, "read_rebalance_state")
    @patch.object(mod, "resolve_and_validate_exec_ip")
    @patch.object(mod, "Cluster")
    @patch.object(mod, "Ticket")
    def test_rejects_when_status_not_in_progress(self, mock_ticket_cls, mock_cluster_cls, mock_resolve, mock_read):
        _resolved(mock_ticket_cls, mock_cluster_cls, mock_resolve)
        mock_read.return_value = {
            "progress": '{"status": "failed"}',
            "throttle_rate": "104857600",
            "override_mode": "manual",
        }

        with pytest.raises(serializers.ValidationError, match="只有in_progress状态才能恢复自动调速"):
            mod.resume_rebalance_auto_throttle(ticket_id=1)

    @patch.object(mod, "clear_throttle_override")
    @patch.object(mod, "read_rebalance_state")
    @patch.object(mod, "resolve_and_validate_exec_ip")
    @patch.object(mod, "Cluster")
    @patch.object(mod, "Ticket")
    def test_switches_back_to_auto(self, mock_ticket_cls, mock_cluster_cls, mock_resolve, mock_read, mock_clear):
        _resolved(mock_ticket_cls, mock_cluster_cls, mock_resolve)
        mock_read.return_value = {
            "progress": '{"status": "in_progress"}',
            "throttle_rate": "104857600",
            "override_mode": "manual",
        }

        result = mod.resume_rebalance_auto_throttle(ticket_id=1)

        mock_clear.assert_called_once_with("127.0.0.1", 0, 1)
        assert result["override_mode"] == "auto"
