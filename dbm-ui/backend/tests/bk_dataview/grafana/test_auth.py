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
from unittest.mock import patch

import pytest
from django.test import RequestFactory

from backend.bk_dataview.grafana.views import ProxyBaseView, ProxyView
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.iam_app.dataclass import ResourceEnum
from backend.iam_app.dataclass.actions import ActionEnum

pytestmark = pytest.mark.django_db

PROMQL_PATH = "/grafana/api/datasources/proxy/1/timeseries/graph_promql_query/"
UNIFY_QUERY_PATH = "/grafana/api/datasources/proxy/1/timeseries/time_series/unify_query/"

BIZ_ID = 100
OTHER_BIZ_ID = 200
NAMESPACE = f"qdrant01-testbiz-{BIZ_ID}"


@pytest.fixture
def qdrant_cluster():
    return Cluster.objects.create(
        name="qdrant01",
        bk_biz_id=BIZ_ID,
        cluster_type=ClusterType.K8sQdrantHa.value,
        immute_domain="qdrant01.test.db",
    )


@pytest.fixture
def pulsar_cluster():
    return Cluster.objects.create(
        name="pulsar01",
        bk_biz_id=BIZ_ID,
        cluster_type=ClusterType.Pulsar.value,
        immute_domain="pulsar01.test.db",
    )


@pytest.fixture
def iam_check():
    with patch.object(ProxyBaseView, "_ProxyBaseView__check_iam_permission", return_value=True) as mock_check:
        yield mock_check


def auth(path, body):
    request = RequestFactory().post(path, data=json.dumps(body), content_type="application/json")
    return ProxyView()._auth(request)


def auth_promql(promql):
    return auth(PROMQL_PATH, {"promql": promql})


def k8s_selector(namespace=NAMESPACE, instance="qdrant01"):
    return f'qdrant_collections_total{{namespace="{namespace}",app_kubernetes_io_instance="{instance}"}}'


class TestK8sAuth:
    def test_allowed(self, qdrant_cluster, iam_check):
        auth_promql(f"sum({k8s_selector()})")

        iam_check.assert_called_once()
        _, actions, resources, resource_meta = iam_check.call_args.args
        assert actions == [ActionEnum.K8S_QDRANT_VIEW]
        assert resources == [qdrant_cluster.id]
        assert resource_meta == ResourceEnum.K8S_QDRANT

    def test_iam_denied(self, qdrant_cluster, iam_check):
        iam_check.return_value = False
        with pytest.raises(PermissionError):
            auth_promql(k8s_selector())

    def test_cross_biz_namespace(self, qdrant_cluster, iam_check):
        """namespace 解析出的业务与集群所在业务不一致时，定位不到集群"""
        with pytest.raises(PermissionError):
            auth_promql(k8s_selector(namespace=f"qdrant01-otherbiz-{OTHER_BIZ_ID}"))
        iam_check.assert_not_called()

    def test_cluster_not_exist(self, qdrant_cluster, iam_check):
        with pytest.raises(PermissionError):
            auth_promql(k8s_selector(instance="not_exist"))
        iam_check.assert_not_called()

    def test_invalid_namespace(self, qdrant_cluster, iam_check):
        with pytest.raises(PermissionError):
            auth_promql(k8s_selector(namespace="kube-system"))

    def test_only_bcs_cluster_id_rejected(self, iam_check):
        with pytest.raises(PermissionError):
            auth_promql('container_memory_working_set_bytes{bcs_cluster_id="BCS-K8S-00001"}')
        iam_check.assert_not_called()

    def test_namespace_only_fallback_biz(self, iam_check):
        auth_promql(f'container_memory_working_set_bytes{{namespace="{NAMESPACE}"}}')

        _, actions, resources, resource_meta = iam_check.call_args.args
        assert actions == [ActionEnum.DB_MANAGE]
        assert resources == [BIZ_ID]
        assert resource_meta == ResourceEnum.BUSINESS

    def test_histogram_quantile(self, qdrant_cluster, iam_check):
        auth_promql(f"histogram_quantile(0.99, sum(rate({k8s_selector()}[5m])) by (le))")
        iam_check.assert_called_once()

    def test_binary_rhs_checked(self, qdrant_cluster, iam_check):
        """二元表达式右侧选择器越权时拒绝"""
        with pytest.raises(PermissionError):
            auth_promql(f'{k8s_selector()} / {k8s_selector(namespace=f"x-y-{OTHER_BIZ_ID}")}')

    def test_id_not_checked(self, qdrant_cluster, iam_check):
        """集合 id 不参与鉴权"""
        auth_promql(
            f'qdrant_collection_points{{namespace="{NAMESPACE}",app_kubernetes_io_instance="qdrant01",id=~"a|b"}}'
        )
        iam_check.assert_called_once()

    def test_unify_query_all_configs_checked(self, qdrant_cluster, iam_check):
        def where(namespace):
            return [
                {"key": "namespace", "method": "eq", "value": [namespace]},
                {"key": "app_kubernetes_io_instance", "method": "eq", "value": ["qdrant01"]},
            ]

        body = {"query_configs": [{"where": where(NAMESPACE)}, {"where": where(f"x-y-{OTHER_BIZ_ID}")}]}
        with pytest.raises(PermissionError):
            auth(UNIFY_QUERY_PATH, body)


class TestClusterAuth:
    def test_cluster_domain_priority(self, pulsar_cluster, iam_check):
        """带 cluster_domain 时按集群鉴权，pulsar 的 namespace 维度不进入 k8s 鉴权"""
        auth_promql(
            'pulsar_rate_in{app="test",cluster_domain="pulsar01.test.db",namespace="public/default",topic="t1"}'
        )

        _, actions, resources, _ = iam_check.call_args.args
        assert actions == [ActionEnum.PULSAR_VIEW]
        assert resources == [pulsar_cluster.id]

    def test_no_auth_key_pass(self, iam_check):
        auth_promql('up{job="test"}')
        iam_check.assert_not_called()

    def test_not_query_url(self, iam_check):
        request = RequestFactory().get("/grafana/api/dashboards/uid/xxx")
        assert ProxyView()._auth(request) is True
        iam_check.assert_not_called()
