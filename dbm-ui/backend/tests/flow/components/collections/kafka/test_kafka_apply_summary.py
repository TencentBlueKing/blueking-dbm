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
# 只测 KafkaApplySummaryService._execute() 的编排逻辑（查Cluster、拼access_entry_url、跳过写入），
# 以及 add_kafka_apply_summary_output_act() 的参数拼装，全部通过mock隔离ORM/FlowOutputHandler，无需django_db标记。
from unittest.mock import MagicMock, patch

from backend.flow.plugins.components.collections.kafka import kafka_apply_summary as mod


class FakeData:
    def __init__(self, items):
        self.inputs = {"kwargs": {"items": items}, "global_data": {}}

    def get_one_of_inputs(self, key):
        return self.inputs.get(key)


def _make_service(root_id="root123"):
    svc = mod.KafkaApplySummaryService()
    svc._runtime_attrs = {"root_pipeline_id": root_id}
    svc.log_info = MagicMock()
    svc.log_warning = MagicMock()
    svc.log_error = MagicMock()
    return svc


def _item(**overrides):
    item = {
        "bk_biz_id": 3,
        "domain_name": "kafka.test.db",
        "region": "default",
        "version": "2.4.0",
        "port": 9092,
    }
    item.update(overrides)
    return item


class TestKafkaApplySummaryServiceExecute:
    @patch.object(mod.env, "BK_SAAS_HOST", "https://dbm.example.com")
    @patch.object(mod, "FlowOutputHandler")
    @patch.object(mod, "Flow")
    @patch.object(mod, "Cluster")
    def test_writes_access_entry_url_when_cluster_exists(self, mock_cluster_cls, mock_flow_cls, mock_handler_cls):
        mock_flow_cls.objects.filter.return_value.exists.return_value = True
        mock_cluster_cls.objects.get.return_value = MagicMock(bk_biz_id=3, id=100)

        svc = _make_service()
        result = svc._execute(FakeData([_item()]), None)

        assert result is True
        mock_handler_cls.assert_called_once_with(mod.KafkaApplySummarySerializer)
        root_id, summary_list = mock_handler_cls.return_value.insert_data.call_args.args
        assert root_id == "root123"
        assert summary_list[0]["domain_name"] == "kafka.test.db"
        assert summary_list[0]["port"] == 9092
        assert (
            summary_list[0]["access_entry_url"]
            == "https://dbm.example.com/3/db-manage/kafka/detail/100?open=access_entry"
        )

    @patch.object(mod, "FlowOutputHandler")
    @patch.object(mod, "Flow")
    @patch.object(mod, "Cluster")
    def test_cluster_not_found_leaves_access_entry_url_blank(self, mock_cluster_cls, mock_flow_cls, mock_handler_cls):
        mock_flow_cls.objects.filter.return_value.exists.return_value = True
        mock_cluster_cls.DoesNotExist = Exception
        mock_cluster_cls.objects.get.side_effect = mock_cluster_cls.DoesNotExist

        svc = _make_service()
        result = svc._execute(FakeData([_item()]), None)

        assert result is True
        summary_list = mock_handler_cls.return_value.insert_data.call_args.args[1]
        assert summary_list[0]["access_entry_url"] == ""
        svc.log_error.assert_any_call("写入集群信息摘要失败，集群[kafka.test.db]不存在")

    @patch.object(mod, "FlowOutputHandler")
    @patch.object(mod, "Flow")
    def test_skips_write_when_no_flow_record(self, mock_flow_cls, mock_handler_cls):
        mock_flow_cls.objects.filter.return_value.exists.return_value = False

        svc = _make_service()
        result = svc._execute(FakeData([_item()]), None)

        assert result is True
        mock_handler_cls.assert_not_called()


class TestKafkaApplySummarySchema:
    def test_field_names_and_primary_key_are_stable(self):
        assert list(mod.KafkaApplySummarySerializer().fields) == [
            "domain_name",
            "region",
            "version",
            "port",
            "access_entry_url",
        ]
        assert mod.KafkaApplySummarySerializer.table_primary_key == "domain_name"


class TestAddKafkaApplySummaryOutputAct:
    def test_add_act_receives_expected_kwargs(self):
        pipeline = MagicMock()

        mod.add_kafka_apply_summary_output_act(
            kafka_pipeline=pipeline,
            bk_biz_id=3,
            domain_name="kafka.test.db",
            region="default",
            version="2.4.0",
            port=9092,
        )

        pipeline.add_act.assert_called_once()
        call_kwargs = pipeline.add_act.call_args.kwargs
        assert call_kwargs["act_component_code"] == mod.KafkaApplySummaryComponent.code
        items = call_kwargs["kwargs"]["items"]
        assert items == [
            {
                "bk_biz_id": 3,
                "domain_name": "kafka.test.db",
                "region": "default",
                "version": "2.4.0",
                "port": 9092,
            }
        ]
