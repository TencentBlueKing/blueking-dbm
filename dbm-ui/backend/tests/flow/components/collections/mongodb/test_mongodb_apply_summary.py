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
from unittest.mock import MagicMock, patch

from backend.db_meta.models import Cluster
from backend.flow.plugins.components.collections.mongodb import mongodb_apply_summary as mod


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


class TestMongoApplySummarySchema:
    def test_replicaset_field_names_and_primary_key_are_stable(self):
        assert list(mod.MongoReplicaSetApplySummarySerializer().fields) == [
            "domain_name",
            "region",
            "port",
            "password_url",
        ]
        assert mod.MongoReplicaSetApplySummarySerializer.table_primary_key == "domain_name"

    def test_shard_field_names_and_primary_key_are_stable(self):
        assert list(mod.MongoShardApplySummarySerializer().fields) == [
            "domain_name",
            "region",
            "port",
            "password_url",
        ]
        assert mod.MongoShardApplySummarySerializer.table_primary_key == "domain_name"


class TestAddMongoApplySummaryOutputAct:
    def test_single_add_act_receives_expected_kwargs(self):
        pipeline = MagicMock()

        mod.add_mongodb_apply_summary_output_act(
            pipeline=pipeline,
            bk_biz_id=3,
            domain_name="mongos.cluster.app.db",
            region="sz",
            port=27021,
            component_code=mod.MongoShardApplySummaryComponent.code,
        )

        pipeline.add_act.assert_called_once()
        call_kwargs = pipeline.add_act.call_args.kwargs
        assert call_kwargs["act_component_code"] == mod.MongoShardApplySummaryComponent.code
        assert call_kwargs["kwargs"]["items"] == [
            {
                "bk_biz_id": 3,
                "domain_name": "mongos.cluster.app.db",
                "region": "sz",
                "port": 27021,
            }
        ]

    def test_batch_add_act_skips_empty_items(self):
        pipeline = MagicMock()
        mod.add_mongodb_batch_apply_summary_output_act(
            pipeline=pipeline,
            items=[],
            component_code=mod.MongoReplicaSetApplySummaryComponent.code,
        )
        pipeline.add_act.assert_not_called()


class TestMongoApplySummaryServiceExecute:
    @patch.object(mod.env, "BK_SAAS_HOST", "https://dbm.example.com")
    @patch.object(mod, "FlowOutputHandler")
    @patch.object(mod, "Flow")
    @patch.object(mod, "Cluster")
    def test_replicaset_writes_password_url_when_cluster_exists(
        self, mock_cluster_cls, mock_flow_cls, mock_handler_cls
    ):
        mock_flow_cls.objects.filter.return_value.exists.return_value = True
        mock_cluster_cls.DoesNotExist = Cluster.DoesNotExist
        mock_cluster_cls.objects.get.return_value = MagicMock(bk_biz_id=3, id=100)

        svc = _make_service(mod.MongoReplicaSetApplySummaryService)
        result = svc._execute(
            FakeData(
                [
                    {
                        "bk_biz_id": 3,
                        "domain_name": "m1.rs1.app.db",
                        "region": "sz",
                        "port": 27001,
                    }
                ]
            ),
            None,
        )

        assert result is True
        mock_handler_cls.assert_called_once_with(mod.MongoReplicaSetApplySummarySerializer)
        _, summary_list = mock_handler_cls.return_value.insert_data.call_args.args
        assert summary_list == [
            {
                "region": "sz",
                "domain_name": "m1.rs1.app.db",
                "port": 27001,
                "password_url": "https://dbm.example.com/3/db-manage/mongodb/replica-set/list/100?open=access_entry",
            }
        ]

    @patch.object(mod.env, "BK_SAAS_HOST", "https://dbm.example.com")
    @patch.object(mod, "FlowOutputHandler")
    @patch.object(mod, "Flow")
    @patch.object(mod, "Cluster")
    def test_shard_writes_password_url_when_cluster_exists(self, mock_cluster_cls, mock_flow_cls, mock_handler_cls):
        mock_flow_cls.objects.filter.return_value.exists.return_value = True
        mock_cluster_cls.DoesNotExist = Cluster.DoesNotExist
        mock_cluster_cls.objects.get.return_value = MagicMock(bk_biz_id=3, id=200)

        svc = _make_service(mod.MongoShardApplySummaryService)
        result = svc._execute(
            FakeData(
                [
                    {
                        "bk_biz_id": 3,
                        "domain_name": "mongos.cluster.app.db",
                        "region": "sz",
                        "port": 27021,
                    }
                ]
            ),
            None,
        )

        assert result is True
        _, summary_list = mock_handler_cls.return_value.insert_data.call_args.args
        assert summary_list[0]["password_url"] == (
            "https://dbm.example.com/3/db-manage/mongodb/shared-cluster/list/200?open=access_entry"
        )

    @patch.object(mod, "FlowOutputHandler")
    @patch.object(mod, "Flow")
    @patch.object(mod, "Cluster")
    def test_skips_insert_when_flow_not_associated(self, mock_cluster_cls, mock_flow_cls, mock_handler_cls):
        mock_cluster_cls.DoesNotExist = Cluster.DoesNotExist
        mock_cluster_cls.objects.get.return_value = MagicMock(bk_biz_id=3, id=200)
        mock_flow_cls.objects.filter.return_value.exists.return_value = False

        svc = _make_service(mod.MongoShardApplySummaryService)
        result = svc._execute(
            FakeData(
                [
                    {
                        "bk_biz_id": 3,
                        "domain_name": "mongos.cluster.app.db",
                        "region": "sz",
                        "port": 27021,
                    }
                ]
            ),
            None,
        )

        assert result is True
        mock_handler_cls.assert_not_called()
