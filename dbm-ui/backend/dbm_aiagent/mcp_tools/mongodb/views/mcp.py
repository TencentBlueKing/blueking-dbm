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
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import auth_default, auth_parse_clusters, auth_parse_hosts
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.mongodb.auth_parser import auth_parse_meta_value, auth_parse_slowlog_target
from backend.dbm_aiagent.mcp_tools.mongodb.auth_parser.permissions import (
    McpMongoAlarmPermission,
    McpMongoMetaPermission,
)
from backend.dbm_aiagent.mcp_tools.mongodb.impl.cluster_meta import (
    cluster_mongos,
    cluster_overview,
    cluster_shards,
    list_clusters_by_hosts,
    meta_info,
    mongodb_list_clusters,
)
from backend.dbm_aiagent.mcp_tools.mongodb.impl.mongodb_alarms import get_alarms_flat, get_cluster_alarms
from backend.dbm_aiagent.mcp_tools.mongodb.impl.mongodb_metrics import (
    get_mongodb_connections,
    get_mongodb_cpu_usage,
    get_mongodb_locks,
    get_mongodb_qps,
)
from backend.dbm_aiagent.mcp_tools.mongodb.impl.mongodb_slowlog import (
    get_mongodb_slowlog_list,
    get_mongodb_slowlog_overview,
)
from backend.dbm_aiagent.mcp_tools.mongodb.impl.response_format import (
    format_biz_alarms,
    format_cluster_alarms,
    format_results,
    format_slowlog_list,
    format_slowlog_overview,
)
from backend.dbm_aiagent.mcp_tools.mongodb.serializers.mcp import (
    META_ACTION_CLUSTER_OVERVIEW,
    META_ACTION_LIST_CLUSTERS,
    META_ACTION_LIST_MONGOS,
    META_ACTION_LIST_SHARDS,
    METRIC_CONNECTIONS,
    METRIC_CPU_USAGE,
    METRIC_LOCKS,
    METRIC_QPS,
    SLOWLOG_MODE_LIST,
    MongoFlexibleOutputSerializer,
    MongoGetMetaInfoInputSerializer,
    MongoListByHostsInputSerializer,
    MongoQueryAlarmInputSerializer,
    MongoQueryMetaInputSerializer,
    MongoQueryMetricInputSerializer,
    MongoQueryMetricOutputSerializer,
    MongoQuerySlowlogInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mongodb.tools.comm_tools import estimate_token_count
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.mcp import McpClusterDetailPermission

_METRIC_DISPATCH = {
    METRIC_QPS: get_mongodb_qps,
    METRIC_CONNECTIONS: get_mongodb_connections,
    METRIC_LOCKS: get_mongodb_locks,
    METRIC_CPU_USAGE: get_mongodb_cpu_usage,
}

_DECORATOR_COMMON = {
    "tags": [DBMMCPTags.READ],
    "mcp": [DBMMcpTools.MONGODB_MCP, DBMMcpTools.DBM_PUBLIC_MARKET],
    "name_prefix": "mongodb",
}


class MongoMcpToolsViewSet(McpToolsViewSet):
    """MongoDB MCP 精简入口：DBM 元数据 + TS 发现 + 告警/慢日志/指标。"""

    default_permission_class = [DBManagePermission()]

    @mcp_tools_api_decorator(
        description=str(
            _(
                "查询 DBM 平台登记的业务/集群/拓扑元数据（ORM）。"
                "action=list_clusters|cluster_overview|list_mongos|list_shards；"
                "list_clusters 需 bk_biz_id；拓扑类需 cluster_domain。"
                "按 IP 反查集群请用 list_by_hosts；监控侧按域名/IP 反查实例请用 get_meta_info"
            )
        ),
        request_slz=MongoQueryMetaInputSerializer,
        response_slz=MongoFlexibleOutputSerializer,
        permission_classes=[McpMongoMetaPermission],
        # 鉴权由 McpMongoMetaPermission 按 action 内部动态设置 parser；
        # 装饰器 mcp_auth_parser 对本端点不参与鉴权，仅满足装饰器签名占位。
        mcp_auth_parser=auth_default,
        **_DECORATOR_COMMON,
    )
    def query_meta(self, request, *args, **kwargs):
        action = self.get_param("action")
        if action == META_ACTION_LIST_CLUSTERS:
            return Response(format_results(mongodb_list_clusters(bk_biz_id=self.get_param("bk_biz_id"))))
        if action == META_ACTION_CLUSTER_OVERVIEW:
            return Response(format_results(cluster_overview(immute_domain=self.get_param("cluster_domain"))))
        if action == META_ACTION_LIST_MONGOS:
            return Response(format_results({"mongos": cluster_mongos(immute_domain=self.get_param("cluster_domain"))}))
        if action == META_ACTION_LIST_SHARDS:
            return Response(format_results({"shards": cluster_shards(immute_domain=self.get_param("cluster_domain"))}))
        raise ValidationError(_("unknown action: {}").format(action))

    @mcp_tools_api_decorator(
        description=str(
            _(
                "按主机 IP 反查 DBM 登记的所属集群及实例角色（ORM），返回 immute_domain/host/instance_role。"
                "仅查集群基信息请优先用通用 dbmeta_query_list_clusters_base_info；"
                "监控侧发现请用 get_meta_info"
            )
        ),
        request_slz=MongoListByHostsInputSerializer,
        response_slz=MongoFlexibleOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_hosts,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MONGODB_MCP],
        name_prefix="mongodb",
    )
    def list_by_hosts(self, request, *args, **kwargs):
        return Response(format_results(list_clusters_by_hosts(hosts=self.get_param("ips"))))

    @mcp_tools_api_decorator(
        description=str(
            _(
                "从监控时序（TSDB）label 发现正在上报的 MongoDB 实例元信息"
                "（cluster_domain、instance_role、shard 等）。"
                "target=集群域名 / IP / IP:PORT。"
                "不是 DBM 配置库；无指标或超保留期可能为空。"
                "拓扑/分片清单请用 query_meta"
            )
        ),
        request_slz=MongoGetMetaInfoInputSerializer,
        response_slz=MongoFlexibleOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_meta_value,
        **_DECORATOR_COMMON,
    )
    def get_meta_info(self, request, *args, **kwargs):
        return Response(format_results(meta_info(self.get_param("target"))))

    @mcp_tools_api_decorator(
        description=str(_("统一告警查询。cluster_domain 与 bk_biz_id 二选一：传域名查集群告警，传业务 ID 按集群汇总该业务告警")),
        request_slz=MongoQueryAlarmInputSerializer,
        response_slz=MongoFlexibleOutputSerializer,
        permission_classes=[McpMongoAlarmPermission],
        # 鉴权由 McpMongoAlarmPermission 按入参内部动态设置 parser；
        # 装饰器 mcp_auth_parser 对本端点不参与鉴权，仅满足装饰器签名占位。
        mcp_auth_parser=auth_default,
        **_DECORATOR_COMMON,
    )
    def query_alarm(self, request, *args, **kwargs):
        start_time = self.get_param("start_time")
        end_time = self.get_param("end_time")
        cluster_domain = (self.get_param("cluster_domain") or "").strip()
        if cluster_domain:
            raw = get_cluster_alarms(immute_domain=cluster_domain, start_time=start_time, end_time=end_time)
            return Response(format_cluster_alarms(raw))
        raw = get_alarms_flat(appid=self.get_param("bk_biz_id"), start_time=start_time, end_time=end_time)
        return Response(format_biz_alarms(raw))

    @mcp_tools_api_decorator(
        description=str(
            _(
                "统一慢查询日志。"
                "mode=overview（默认）按 ns/queryHash 与 shard/instance 返回精简聚合桶；"
                "mode=list 返回明细，支持 ns/queryHash 过滤。"
                "cluster_domain / instance / instance_host 至少填其一（list 模式需 cluster_domain 或 instance）"
            )
        ),
        request_slz=MongoQuerySlowlogInputSerializer,
        response_slz=MongoFlexibleOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_slowlog_target,
        **_DECORATOR_COMMON,
    )
    def query_slowlog(self, request, *args, **kwargs):
        mode = self.get_param("mode")
        cluster_domain = self.get_param("cluster_domain") or None
        instance_host = self.get_param("instance_host") or None
        instance = self.get_param("instance") or None
        start_time = self.get_param("start_time")
        end_time = self.get_param("end_time")
        if mode == SLOWLOG_MODE_LIST:
            raw = get_mongodb_slowlog_list(
                cluster_domain=cluster_domain,
                instance=instance,
                start_time=start_time,
                end_time=end_time,
                ns=self.get_param("ns") or None,
                query_hash=self.get_param("queryHash") or None,
            )
            return Response(format_slowlog_list(raw if isinstance(raw, dict) else {}))
        raw = get_mongodb_slowlog_overview(
            cluster_domain=cluster_domain,
            instance_host=instance_host,
            instance=instance,
            start_time=start_time,
            end_time=end_time,
        )
        if not isinstance(raw, dict):
            raw = {}
        out = format_slowlog_overview(raw)
        out["token_count"] = estimate_token_count(out)
        return Response(out)

    @mcp_tools_api_decorator(
        description=str(
            _("统一指标查询。metric=qps|connections|locks|cpu_usage；需 cluster_domain、start_time、end_time，可选 instance_host")
        ),
        request_slz=MongoQueryMetricInputSerializer,
        response_slz=MongoQueryMetricOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        **_DECORATOR_COMMON,
    )
    def query_metric(self, request, *args, **kwargs):
        metric = self.get_param("metric")
        fetcher = _METRIC_DISPATCH.get(metric)
        if not fetcher:
            raise ValidationError(_("unknown metric: {}").format(metric))
        out = fetcher(
            cluster_domain=self.get_param("cluster_domain"),
            start_time=self.get_param("start_time"),
            end_time=self.get_param("end_time"),
            instance_host=self.get_param("instance_host") or None,
        )
        if isinstance(out, dict):
            out["token_count"] = estimate_token_count(out)
        return Response(out)
