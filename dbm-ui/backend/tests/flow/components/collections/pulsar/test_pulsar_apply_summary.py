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
# PulsarApplySummaryService._execute()的公共编排逻辑已经在
# tests/flow/components/collections/common/test_bigdata_apply_summary.py 里参数化覆盖，
# 这里只测Pulsar专属的schema稳定性和add_pulsar_apply_summary_output_act()的参数拼装。
from unittest.mock import MagicMock

from backend.flow.plugins.components.collections.pulsar import pulsar_apply_summary as mod


class TestPulsarApplySummarySchema:
    def test_field_names_and_primary_key_are_stable(self):
        assert list(mod.PulsarApplySummarySerializer().fields) == [
            "domain_name",
            "region",
            "version",
            "port",
            "access_entry_url",
        ]
        assert mod.PulsarApplySummarySerializer.table_primary_key == "domain_name"


class TestAddPulsarApplySummaryOutputAct:
    def test_add_act_receives_expected_kwargs(self):
        pipeline = MagicMock()

        mod.add_pulsar_apply_summary_output_act(
            pulsar_pipeline=pipeline,
            bk_biz_id=3,
            domain_name="pulsar.test.db",
            region="default",
            version="2.10.1",
            port=6650,
        )

        pipeline.add_act.assert_called_once()
        call_kwargs = pipeline.add_act.call_args.kwargs
        assert call_kwargs["act_component_code"] == mod.PulsarApplySummaryComponent.code
        items = call_kwargs["kwargs"]["items"]
        assert items == [
            {
                "bk_biz_id": 3,
                "domain_name": "pulsar.test.db",
                "region": "default",
                "version": "2.10.1",
                "port": 6650,
            }
        ]
