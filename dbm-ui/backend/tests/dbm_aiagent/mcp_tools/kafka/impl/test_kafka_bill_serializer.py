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
# 只测 LenientJSONField 对 MCP 调用侧把嵌套对象序列化成 JSON 字符串输入的兜底解析，无需 django_db。
import json

from backend.dbm_aiagent.mcp_tools.kafka.serializers.kafka_bill import (
    SubmitBillKafkaApplyInputSerializer,
    SubmitBillKafkaScaleUpInputSerializer,
)


def _scale_up_data(resource_spec):
    return {
        "bk_biz_id": 3,
        "cluster_domain": "kafka.sintest0901a.dba.db",
        "ip_source": "resource_pool",
        "resource_spec": resource_spec,
    }


class TestLenientJSONFieldParsesStringInput:
    def test_resource_spec_as_string_parses_to_dict(self):
        raw = {"broker": {"count": 1, "spec_id": 576}}
        slz = SubmitBillKafkaScaleUpInputSerializer(data=_scale_up_data(json.dumps(raw)))

        assert slz.is_valid(), slz.errors
        assert slz.validated_data["resource_spec"] == raw

    def test_resource_spec_as_dict_still_works(self):
        raw = {"broker": {"count": 1, "spec_id": 576}}
        slz = SubmitBillKafkaScaleUpInputSerializer(data=_scale_up_data(raw))

        assert slz.is_valid(), slz.errors
        assert slz.validated_data["resource_spec"] == raw

    def test_resource_spec_as_invalid_string_fails_validation(self):
        slz = SubmitBillKafkaScaleUpInputSerializer(data=_scale_up_data("{not-json"))

        assert not slz.is_valid()

    def test_apply_resource_spec_as_string_parses_to_dict(self):
        raw = {"zookeeper": {"count": 3, "spec_id": 1}, "broker": {"count": 3, "spec_id": 1}}
        data = {
            "bk_biz_id": 3,
            "cluster_name": "test0901",
            "db_app_abbr": "dba",
            "city_code": "default",
            "ip_source": "resource_pool",
            "resource_spec": json.dumps(raw),
        }
        slz = SubmitBillKafkaApplyInputSerializer(data=data)

        assert slz.is_valid(), slz.errors
        assert slz.validated_data["resource_spec"] == raw
