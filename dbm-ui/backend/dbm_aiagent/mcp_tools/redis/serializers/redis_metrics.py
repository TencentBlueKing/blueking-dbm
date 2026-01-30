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
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.dbm_aiagent.mcp_tools.redis.impl.redis_metrics import MetricsInstanceRole, MetricsOutputMode


class RedisMetricsInputSerializer(serializers.Serializer):
    """Input serializer for Redis metrics queries"""

    cluster_domain = serializers.CharField(help_text=_("Redis cluster domain name"))
    start_time = serializers.DateTimeField(
        required=False,
        help_text=_(
            "Optional: Start time in ISO format (e.g., 2026-01-08T16:33:38+08:00). Defaults to 30 minutes ago."
        ),
    )
    end_time = serializers.DateTimeField(
        required=False,
        help_text=_("Optional: End time in ISO format (e.g., 2026-01-08T16:33:38+08:00). Defaults to now."),
    )
    mode = serializers.ChoiceField(
        choices=MetricsOutputMode.get_choices(),
        default=MetricsOutputMode.STATS.value,
        help_text=_(
            "Output mode: 'overall' returns only aggregated time series data, 'stats' returns only scalar statistics, "
            "'both' returns both series and statistics. Use stats as possible, unless the user ask for the raw/graph."
        ),
    )
    detailed = serializers.BooleanField(
        default=False,
        help_text=_(
            "When True, downgrades aggregation dimensions by one level. "
            "E.g., if aggregation_level is Cluster, dimensions become 'cluster_domain,ip' instead of 'cluster_domain'. "
            "If Machine level, dimensions become 'cluster_domain,ip,port' instead of 'cluster_domain,ip'. "
            "Has no effect at Instance level. If user ask for comparison between IPs, then you should turn this on."
            "CRITICAL: Some clusters may have lots of IPs, keep max_len_datapoints <= 15!"
        ),
    )
    max_len_datapoints = serializers.IntegerField(
        default=100,
        help_text=_(
            "Optional: max length of series, default=100, this would determine the interval/time window of PromQL query. "
            'If `mode!="stats"`, this should keep <=15 considering the LLM context length.'
        ),
    )
    instance_role = serializers.ChoiceField(
        choices=MetricsInstanceRole.get_choices(),
        default=MetricsInstanceRole.MASTER.value,
        help_text=_("Role of instances to query: redis_master (default), proxy, or redis_slave"),
    )
    ip = serializers.CharField(
        required=False,
        allow_null=True,
        help_text=_("Optional: Filter by specific IP address for single machine query"),
    )
    port = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text=_("Optional: Filter by specific port for single instance query (requires ip)"),
    )
    mermaid_format = serializers.BooleanField(
        default=False,
        help_text=_(
            "When True and mode != 'stats', returns a 'mermaid_code' field with pre-formatted "
            "mermaid xychart-beta code for visualization. Only active when series data is returned."
        ),
    )


class RedisMetricsOutputSerializer(serializers.Serializer):
    """Output serializer for Redis metrics queries"""

    query_params = serializers.JSONField(
        help_text=_(
            "Query parameters used for this request, useful for LLM to reference and understand the query context"
        )
    )
    series = serializers.JSONField(
        required=False,
        help_text=_(
            "Aggregated time series data (present when mode='overall' or mode='both'). "
            "Format depends on aggregation_level and detailed flag: "
            "instance={'ip:port': [[value, timestamp], ...]}, machine={'ip:port1': [...], 'ip:port2': [...]}, "
            "cluster={'cluster_domain': [...]} or with detailed=True: cluster={'ip1': [...], 'ip2': [...]}"
        ),
    )
    statistics = serializers.JSONField(
        required=False,
        help_text=_(
            "Statistics (present when mode='stats' or mode='both'). "
            "When detailed=False: Aggregated cluster-level scalar statistics: "
            "{'min': float, 'max': float, 'avg': float, 'median': float, 'p95': float, 'cv': float, 'trend': float}. "
            "When detailed=True: Per-key statistics matching series structure: "
            "{'ip1': {'min': float, 'max': float, ...}, 'ip2': {...}, ...} or "
            "{'ip:port1': {'min': float, ...}, 'ip:port2': {...}, ...}. "
            "Statistics computed: "
            "- min: minimum value, "
            "- max: maximum value, "
            "- avg: average value, "
            "- median: median value (less affected by outliers), "
            "- p95: 95th percentile (typical worst case performance), "
            "- cv: coefficient of variation across time, not across <ip> (%) - normalized variability measure, "
            "- trend: linear trend slope (positive=increasing, negative=decreasing)"
        ),
    )
    mermaid_code = serializers.CharField(
        required=False,
        help_text=_(
            "Pre-formatted mermaid xychart-beta code (present when mermaid_format=True and series data exists). "
            "This content must keep AS-IS and outputted for user."
        ),
    )
