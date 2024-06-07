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
from backend.bk_dataview.grafana.promsql import extract_condition_from_promql


class TestGrafanaPromql:
    @staticmethod
    def test_grafana_promql():
        result = extract_condition_from_promql(
            "min(min_over_time(bkmonitor:exporter_dbm_redis_exporter:__default__:"
            'redis_config_maxmemory{cluster_domain="example.domain.db",instance_role="redis_master"}[1m]))'
        )
        assert result["cluster_domain"] == "example.domain.db"
        assert result["instance_role"] == "redis_master"

    @staticmethod
    def test_with_lhs():
        result = extract_condition_from_promql(
            "sum by(command) (rate(bkmonitor:exporter_dbm_mysqld_exporter:__default__:"
            'mysql_global_status_commands_total{cluster_domain="example.domain.db",'
            'command=~"select|insert|update|delete|replace|commit",instance_role="backend_master"}[2m])) >0'
        )
        assert result["cluster_domain"] == "example.domain.db"
        assert result["instance_role"] == "backend_master"

    @staticmethod
    def test_redis():
        result = extract_condition_from_promql(
            "max by(version) (bkmonitor:exporter_dbm_twemproxy_exporter:__default__:twemproxy_version"
            '{cluster_domain="example.domain.db"})'
        )
        assert result["cluster_domain"] == "example.domain.db"

    @staticmethod
    def test_pulsar():
        result = extract_condition_from_promql(
            "sum by (topic) (sum_over_time(bkmonitor:pushgateway_dbm_pulsarbroker_bkpull:"
            'pulsar_throughput_in{app="test_app",cluster_domain="example.domain.db",'
            'namespace="test_namespace",topic="test_topic"}[1m]))'
        )
        assert result["cluster_domain"] == "example.domain.db"
        assert result["app"] == "test_app"
        assert result["topic"] == "test_topic"
        assert result["namespace"] == "test_namespace"

    @staticmethod
    def test_kafka_count():
        result = extract_condition_from_promql(
            'count(bkmonitor:dbm_system:cpu_summary:usage{app="es",'
            'cluster_domain="example.domain.db",instance_role="broker"})'
        )
        assert result["cluster_domain"] == "example.domain.db"
        assert result["app"] == "es"
        assert result["instance_role"] == "broker"

    def test_kafka_avg(self):
        result = extract_condition_from_promql(
            'avg(bkmonitor:pushgateway_dbm_kafka_bkpull:kafka_network_requestmetrics_remotetimems{app="es",'
            'cluster_domain="example.domain.db",quantile="0.95",request="Produce"})'
        )
        assert result["cluster_domain"] == "example.domain.db"
        assert result["app"] == "es"
        assert result["quantile"] == "0.95"
        assert result["request"] == "Produce"

    def test_kafka_count_topic(self):
        result = extract_condition_from_promql(
            "count(count by (topic) (bkmonitor:pushgateway_dbm_kafka_bkpull:kafka_cluster_partition_replicascount"
            '{app="es",cluster_domain="example.domain.db",partition="0"}))'
        )
        assert result["cluster_domain"] == "example.domain.db"
        assert result["app"] == "es"
        assert result["partition"] == "0"

    def test_redis_cpu(self):
        result = extract_condition_from_promql(
            "max(max by (instance) (irate(bkmonitor:exporter_dbm_redis_exporter:__default__:"
            'redis_cpu_user_seconds_total{cluster_domain="example.domain.db",'
            'instance_role="redis_master"}[2m]) + irate(bkmonitor:exporter_dbm_redis_exporter:'
            '__default__:redis_cpu_sys_seconds_total{cluster_domain="example.domain.db",'
            'instance_role="redis_master"}[2m])))'
        )
        assert result["cluster_domain"] == "example.domain.db"
        assert result["instance_role"] == "redis_master"
