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

from contextlib import contextmanager
from unittest.mock import patch

import pytest

from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import auth_parse_hosts, auth_parse_instances


def _request(data, method="POST"):
    class _Req:
        pass

    request = _Req()
    request.method = method
    request.data = data
    request.query_params = data
    return request


@contextmanager
def _patched_models():
    with patch("backend.db_meta.models.Machine") as machine, patch(
        "backend.db_meta.models.StorageInstance"
    ) as storage, patch("backend.db_meta.models.ProxyInstance") as proxy, patch(
        "backend.db_meta.models.Cluster"
    ) as cluster:
        yield machine, storage, proxy, cluster


class TestAuthParseHosts:
    def test_ip_queries_machine_then_storage_and_proxy(self):
        with _patched_models() as (machine, storage, proxy, cluster):
            machine.objects.filter.return_value.values_list.return_value = [101]
            storage.objects.filter.return_value.values_list.return_value = [1, None]
            proxy.objects.filter.return_value.values_list.return_value = [2, 1]

            result = auth_parse_hosts(_request({"ip": "1.0.0.43"}))

        assert set(result) == {1, 2}
        machine.objects.filter.assert_called_once_with(ip="1.0.0.43")
        storage.objects.filter.assert_called_once_with(machine_id__in=[101])
        proxy.objects.filter.assert_called_once_with(machine_id__in=[101])
        cluster.objects.filter.assert_not_called()

    def test_bk_host_id_skips_machine_lookup(self):
        with _patched_models() as (machine, storage, proxy, cluster):
            storage.objects.filter.return_value.values_list.return_value = [7]
            proxy.objects.filter.return_value.values_list.return_value = []

            result = auth_parse_hosts(_request({"bk_host_id": 88}))

        assert result == [7]
        machine.objects.filter.assert_not_called()
        storage.objects.filter.assert_called_once_with(machine_id__in=[88])
        proxy.objects.filter.assert_called_once_with(machine_id__in=[88])
        cluster.objects.filter.assert_not_called()

    def test_unknown_ip_does_not_scan_instances(self):
        with _patched_models() as (machine, storage, proxy, _cluster):
            machine.objects.filter.return_value.values_list.return_value = []

            with pytest.raises(ValueError, match="no clusters found"):
                auth_parse_hosts(_request({"ips": ["1.0.0.1"]}))

        machine.objects.filter.assert_called_once_with(ip__in=["1.0.0.1"])
        storage.objects.filter.assert_not_called()
        proxy.objects.filter.assert_not_called()

    def test_missing_param(self):
        with pytest.raises(ValueError, match="ip or bk_host_id is required"):
            auth_parse_hosts(_request({}))


class TestAuthParseInstances:
    def test_keeps_exact_machine_port_pairs(self):
        with _patched_models() as (machine, storage, proxy, cluster):
            machine.objects.filter.return_value.values_list.return_value = [
                (101, "1.0.0.1"),
                (102, "1.0.0.1"),
                (201, "1.0.0.2"),
            ]
            # (101, 3307) 与请求的 (101, 3306) / (201, 3307) 不是同一对，不能命中
            storage.objects.filter.return_value.values_list.return_value = [
                (101, 3306, 11),
                (101, 3307, 99),
                (201, 3307, None),
            ]
            proxy.objects.filter.return_value.values_list.return_value = [(201, 3307, 22)]

            result = auth_parse_instances(_request({"instances": ["1.0.0.1:3306", "1.0.0.2:3307"]}))

        assert set(result) == {11, 22}
        assert set(machine.objects.filter.call_args.kwargs["ip__in"]) == {"1.0.0.1", "1.0.0.2"}
        storage_kwargs = storage.objects.filter.call_args.kwargs
        assert storage_kwargs["machine_id__in"] == {101, 102, 201}
        assert storage_kwargs["port__in"] == {3306, 3307}
        cluster.objects.filter.assert_not_called()

    def test_unknown_ip_does_not_query_instances(self):
        with _patched_models() as (machine, storage, proxy, _cluster):
            machine.objects.filter.return_value.values_list.return_value = []

            with pytest.raises(ValueError, match="no clusters found"):
                auth_parse_instances(_request({"ip": "1.0.0.9", "port": 3306}))

        storage.objects.filter.assert_not_called()
        proxy.objects.filter.assert_not_called()
