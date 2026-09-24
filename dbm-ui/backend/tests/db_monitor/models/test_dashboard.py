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
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import pytest
from django.conf import settings
from rest_framework.test import APIClient

from backend.bk_dataview.grafana.constants import DEFAULT_ORG_ID, DEFAULT_ORG_NAME
from backend.components import KubernetesApi
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import AppCache, Cluster
from backend.db_monitor.constants import DashboardType
from backend.db_monitor.exceptions import DashboardException
from backend.db_monitor.models import Dashboard
from backend.iam_app.handlers.drf_perm.cluster import ClusterDetailPermission
from backend.tests.conftest import mock_bk_user

pytestmark = pytest.mark.django_db

BIZ_ID = 100
CLUSTER_DETAIL = {
    "namespace": f"qdrant01-testbiz-{BIZ_ID}",
    "clusterName": "qdrant01",
    "k8sClusterConfig": {"clusterName": "BCS-K8S-00001"},
}


@pytest.fixture
def qdrant_cluster():
    return Cluster.objects.create(
        name="qdrant01",
        bk_biz_id=BIZ_ID,
        cluster_type=ClusterType.K8sQdrantHa.value,
        immute_domain="qdrant01.test.db",
    )


@pytest.fixture
def qdrant_dashboard():
    return Dashboard.objects.create(
        name="Qdrant",
        cluster_type=ClusterType.K8sQdrantHa.value,
        type=DashboardType.CLUSTER,
        org_id=DEFAULT_ORG_ID,
        org_name=DEFAULT_ORG_NAME,
        uid="qdrant",
        url="/grafana/d/qdrant/qdrant",
    )


def query_of(url):
    return {key: values[0] for key, values in parse_qs(urlparse(url).query).items()}


class TestK8sDashboardUrl:
    def test_get_k8s_url(self, qdrant_cluster, qdrant_dashboard):
        with patch.object(KubernetesApi, "cluster_detail", return_value=CLUSTER_DETAIL) as mock_detail:
            url = qdrant_dashboard.get_k8s_url(qdrant_cluster.id)

        mock_detail.assert_called_once_with({"cluster_id": qdrant_cluster.id}, use_admin=True)
        assert query_of(url) == {
            "orgId": str(DEFAULT_ORG_ID),
            "orgName": DEFAULT_ORG_NAME,
            "var-namespace": f"qdrant01-testbiz-{BIZ_ID}",
            "var-cluster": "qdrant01",
            "var-bcs_cluster_id": "BCS-K8S-00001",
        }

    def test_get_k8s_url_missing_detail(self, qdrant_cluster, qdrant_dashboard):
        with patch.object(KubernetesApi, "cluster_detail", return_value={"namespace": "ns-a-1"}):
            with pytest.raises(DashboardException):
                qdrant_dashboard.get_k8s_url(qdrant_cluster.id)

    @staticmethod
    def request_get_dashboard(cluster):
        client = APIClient()
        client.force_authenticate(user=mock_bk_user("admin"))
        with patch.object(settings, "MIDDLEWARE", []), patch.object(
            ClusterDetailPermission, "has_permission", return_value=True
        ), patch.object(KubernetesApi, "cluster_detail", return_value=CLUSTER_DETAIL) as mock_detail:
            response = client.get(
                "/apis/monitor/grafana/get_dashboard/",
                {"bk_biz_id": BIZ_ID, "cluster_id": cluster.id, "cluster_type": cluster.cluster_type},
            )
        return response, mock_detail

    def test_get_dashboard_k8s(self, qdrant_cluster, qdrant_dashboard):
        response, _ = self.request_get_dashboard(qdrant_cluster)

        (dash_url,) = response.data["urls"]
        params = query_of(dash_url["url"])
        assert params["var-namespace"] == f"qdrant01-testbiz-{BIZ_ID}"
        assert params["var-cluster"] == "qdrant01"
        assert params["var-bcs_cluster_id"] == "BCS-K8S-00001"
        assert "var-cluster_domain" not in params

    def test_get_dashboard_not_k8s(self):
        cluster = Cluster.objects.create(
            name="pulsar01", bk_biz_id=BIZ_ID, cluster_type=ClusterType.Pulsar.value, immute_domain="pulsar01.test.db"
        )
        Dashboard.objects.create(
            name="Pulsar",
            cluster_type=ClusterType.Pulsar.value,
            type=DashboardType.CLUSTER,
            org_id=DEFAULT_ORG_ID,
            org_name=DEFAULT_ORG_NAME,
            uid="pulsar",
            url="/grafana/d/pulsar/pulsar",
        )
        with patch.object(AppCache, "get_app_attr", return_value="testbiz"):
            response, mock_detail = self.request_get_dashboard(cluster)

        (dash_url,) = response.data["urls"]
        assert query_of(dash_url["url"])["var-cluster_domain"] == "pulsar01.test.db"
        mock_detail.assert_not_called()
