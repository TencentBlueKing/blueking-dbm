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
# 覆盖kafka_replace_flow.py全量替换场景依赖的漂移过滤逻辑：老broker缺失的配置项（比如ACL相关的
# authorizer.class.name/super.users/allow.everyone.if.no.acl.found）必须在写入新broker前被
# filter_kafka_config_by_check过滤掉，否则全量替换出来的集群会跟老集群配置不一致。
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.flow.plugins.components.collections.kafka import exec_actuator_script as mod


class FakeData:
    def __init__(self, inputs):
        self.inputs = inputs
        self.outputs = SimpleNamespace()

    def get_one_of_inputs(self, key):
        return self.inputs.get(key)


def _make_service():
    svc = mod.ExecuteDBActuatorScriptService()
    svc._runtime_attrs = {"version": "1"}
    svc.log_info = MagicMock()
    svc.log_error = MagicMock()
    return svc


def _make_kwargs(kafka_configs, filter_kafka_config_by_check=None):
    kwargs = {
        "root_id": "root123",
        "node_name": "安装broker",
        "node_id": "node1",
        "exec_ip": [{"ip": "1.1.1.1"}],
        "bk_cloud_id": 0,
        "template": {"payload": {"extend": {"kafka_configs": kafka_configs}}},
    }
    if filter_kafka_config_by_check is not None:
        kwargs["filter_kafka_config_by_check"] = filter_kafka_config_by_check
    return kwargs


def _make_data(kafka_configs, filter_kafka_config_by_check=None, existing_broker_configs=None):
    return FakeData(
        {
            "kwargs": _make_kwargs(kafka_configs, filter_kafka_config_by_check),
            "global_data": {"uid": "u1"},
            "trans_data": SimpleNamespace(existing_broker_configs=existing_broker_configs),
        }
    )


class TestFilterKafkaConfigByCheck:
    @patch.object(mod, "FlowNode")
    @patch.object(mod, "JobApi")
    def test_filters_configs_missing_on_existing_broker(self, mock_job_api, mock_flow_node):
        # 模拟全量替换：老broker上查不到这几个ACL相关配置项（比如老集群是本次ACL改动之前创建的），
        # 新broker装机时就不能再带上它们，否则新旧broker配置会漂移
        kafka_configs = {
            "broker.rack": "RACK1",
            "authorizer.class.name": "kafka.security.authorizer.AclAuthorizer",
            "super.users": "User:test_admin;User:kafka",
            "allow.everyone.if.no.acl.found": "false",
        }
        data = _make_data(
            kafka_configs,
            filter_kafka_config_by_check=True,
            existing_broker_configs={
                "missing_configs": ["authorizer.class.name", "super.users", "allow.everyone.if.no.acl.found"]
            },
        )

        svc = _make_service()
        assert svc._execute(data, None) is True

        assert kafka_configs == {"broker.rack": "RACK1"}
        mock_job_api.fast_execute_script.assert_called_once()

    @patch.object(mod, "FlowNode")
    @patch.object(mod, "JobApi")
    def test_no_missing_configs_leaves_kafka_configs_untouched(self, mock_job_api, mock_flow_node):
        kafka_configs = {"broker.rack": "RACK1", "authorizer.class.name": "kafka.security.authorizer.AclAuthorizer"}
        data = _make_data(
            kafka_configs,
            filter_kafka_config_by_check=True,
            existing_broker_configs={"missing_configs": []},
        )

        svc = _make_service()
        svc._execute(data, None)

        assert kafka_configs == {
            "broker.rack": "RACK1",
            "authorizer.class.name": "kafka.security.authorizer.AclAuthorizer",
        }

    @patch.object(mod, "FlowNode")
    @patch.object(mod, "JobApi")
    def test_flag_not_set_skips_filtering_entirely(self, mock_job_api, mock_flow_node):
        # 即便trans_data里恰好挂着existing_broker_configs，只要调用方没有设置
        # filter_kafka_config_by_check也不应该触发过滤（该flag目前在扩容/部分替换/全量替换里
        # 都会设为True，这里单测的是flag本身缺失时的兜底行为，不代表现网哪个场景不设置它）
        kafka_configs = {"broker.rack": "RACK1", "authorizer.class.name": "kafka.security.authorizer.AclAuthorizer"}
        data = _make_data(
            kafka_configs,
            filter_kafka_config_by_check=None,
            existing_broker_configs={"missing_configs": ["authorizer.class.name"]},
        )

        svc = _make_service()
        svc._execute(data, None)

        assert kafka_configs == {
            "broker.rack": "RACK1",
            "authorizer.class.name": "kafka.security.authorizer.AclAuthorizer",
        }
