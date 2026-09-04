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
# 覆盖 BigDataApplySummaryService._execute() 的公共编排逻辑(查Cluster、拼access_entry_url、跳过写入)，
# 用kafka/hdfs/doris/pulsar四种具体子类参数化跑一遍，验证公共基类对它们都生效。ES有额外的CLB/北极星逻辑，
# 单独在 tests/flow/components/collections/es/test_es_apply_summary.py 里测。
from unittest.mock import MagicMock, patch

import pytest

from backend.flow.plugins.components.collections.common import bigdata_apply_summary as base_mod
from backend.flow.plugins.components.collections.doris import doris_apply_summary
from backend.flow.plugins.components.collections.hdfs import hdfs_apply_summary
from backend.flow.plugins.components.collections.kafka import kafka_apply_summary
from backend.flow.plugins.components.collections.pulsar import pulsar_apply_summary


class FakeData:
    def __init__(self, items):
        self.inputs = {"kwargs": {"items": items}, "global_data": {}}

    def get_one_of_inputs(self, key):
        return self.inputs.get(key)


def _make_service(service_cls, root_id="root123"):
    svc = service_cls()
    svc._runtime_attrs = {"root_pipeline_id": root_id}
    svc.log_info = MagicMock()
    svc.log_warning = MagicMock()
    svc.log_error = MagicMock()
    return svc


def _item(domain_name, port_field, port_value, **overrides):
    item = {
        "bk_biz_id": 3,
        "domain_name": domain_name,
        "region": "default",
        "version": "1.0.0",
        port_field: port_value,
    }
    item.update(overrides)
    return item


CASES = [
    pytest.param(
        kafka_apply_summary.KafkaApplySummaryService,
        kafka_apply_summary.KafkaApplySummarySerializer,
        "kafka",
        "port",
        9092,
        "kafka.test.db",
        id="kafka",
    ),
    pytest.param(
        hdfs_apply_summary.HdfsApplySummaryService,
        hdfs_apply_summary.HdfsApplySummarySerializer,
        "hdfs",
        "rpc_port",
        9000,
        "hdfs.test.db",
        id="hdfs",
    ),
    pytest.param(
        doris_apply_summary.DorisApplySummaryService,
        doris_apply_summary.DorisApplySummarySerializer,
        "doris",
        "query_port",
        9030,
        "doris.test.db",
        id="doris",
    ),
    pytest.param(
        pulsar_apply_summary.PulsarApplySummaryService,
        pulsar_apply_summary.PulsarApplySummarySerializer,
        "pulsar",
        "port",
        6650,
        "pulsar.test.db",
        id="pulsar",
    ),
]


@pytest.mark.parametrize("service_cls, serializer_cls, detail_path, port_field, port_value, domain_name", CASES)
class TestBigDataApplySummaryServiceExecute:
    @patch.object(base_mod.env, "BK_SAAS_HOST", "https://dbm.example.com")
    @patch.object(base_mod, "FlowOutputHandler")
    @patch.object(base_mod, "Flow")
    @patch.object(base_mod, "Cluster")
    def test_writes_access_entry_url_when_cluster_exists(
        self,
        mock_cluster_cls,
        mock_flow_cls,
        mock_handler_cls,
        service_cls,
        serializer_cls,
        detail_path,
        port_field,
        port_value,
        domain_name,
    ):
        mock_flow_cls.objects.filter.return_value.exists.return_value = True
        mock_cluster_cls.objects.get.return_value = MagicMock(bk_biz_id=3, id=100)

        svc = _make_service(service_cls)
        result = svc._execute(FakeData([_item(domain_name, port_field, port_value)]), None)

        assert result is True
        mock_handler_cls.assert_called_once_with(serializer_cls)
        root_id, summary_list = mock_handler_cls.return_value.insert_data.call_args.args
        assert root_id == "root123"
        assert summary_list[0]["domain_name"] == domain_name
        assert summary_list[0][port_field] == port_value
        assert summary_list[0]["access_entry_url"] == (
            "https://dbm.example.com/3/db-manage/{}/detail/100?open=access_entry".format(detail_path)
        )

    @patch.object(base_mod, "FlowOutputHandler")
    @patch.object(base_mod, "Flow")
    @patch.object(base_mod, "Cluster")
    def test_cluster_not_found_row_is_skipped(
        self,
        mock_cluster_cls,
        mock_flow_cls,
        mock_handler_cls,
        service_cls,
        serializer_cls,
        detail_path,
        port_field,
        port_value,
        domain_name,
    ):
        mock_flow_cls.objects.filter.return_value.exists.return_value = True
        mock_cluster_cls.DoesNotExist = Exception
        mock_cluster_cls.objects.get.side_effect = mock_cluster_cls.DoesNotExist

        svc = _make_service(service_cls)
        result = svc._execute(FakeData([_item(domain_name, port_field, port_value)]), None)

        assert result is True
        mock_handler_cls.assert_not_called()
        svc.log_error.assert_any_call("写入集群信息摘要失败，集群[{}]不存在".format(domain_name))
        svc.log_warning.assert_any_call("没有可写入执行摘要的集群信息，跳过摘要写入")

    @patch.object(base_mod, "FlowOutputHandler")
    @patch.object(base_mod, "Flow")
    @patch.object(base_mod, "Cluster")
    def test_missing_cluster_among_multiple_items_only_skips_that_row(
        self,
        mock_cluster_cls,
        mock_flow_cls,
        mock_handler_cls,
        service_cls,
        serializer_cls,
        detail_path,
        port_field,
        port_value,
        domain_name,
    ):
        mock_flow_cls.objects.filter.return_value.exists.return_value = True
        mock_cluster_cls.DoesNotExist = Exception
        good_cluster = MagicMock(bk_biz_id=3, id=100)

        def _get_side_effect(bk_biz_id, immute_domain):
            if immute_domain == domain_name:
                return good_cluster
            raise mock_cluster_cls.DoesNotExist

        mock_cluster_cls.objects.get.side_effect = _get_side_effect

        items = [
            _item(domain_name, port_field, port_value),
            _item("missing." + domain_name, port_field, port_value),
        ]
        svc = _make_service(service_cls)
        result = svc._execute(FakeData(items), None)

        assert result is True
        mock_handler_cls.assert_called_once()
        summary_list = mock_handler_cls.return_value.insert_data.call_args.args[1]
        assert len(summary_list) == 1
        assert summary_list[0]["domain_name"] == domain_name

    @patch.object(base_mod, "FlowOutputHandler")
    @patch.object(base_mod, "Flow")
    @patch.object(base_mod, "Cluster")
    def test_skips_write_when_no_flow_record(
        self,
        mock_cluster_cls,
        mock_flow_cls,
        mock_handler_cls,
        service_cls,
        serializer_cls,
        detail_path,
        port_field,
        port_value,
        domain_name,
    ):
        mock_flow_cls.objects.filter.return_value.exists.return_value = False
        mock_cluster_cls.objects.get.return_value = MagicMock(bk_biz_id=3, id=100)

        svc = _make_service(service_cls)
        result = svc._execute(FakeData([_item(domain_name, port_field, port_value)]), None)

        assert result is True
        mock_handler_cls.assert_not_called()
