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
import logging

from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import auth_parse_clusters
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.es.impl.es_readonly_api import query_es_readonly_api
from backend.dbm_aiagent.mcp_tools.es.serializers.es_readonly_api import (
    EsReadonlyApiInputSerializer,
    EsReadonlyApiOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import RejectPermission
from backend.iam_app.handlers.drf_perm.mcp import McpClusterDetailPermission

logger = logging.getLogger("flow")

"""
ES 只读 API 查询 MCP
- 通过 bkjob 下发 curl 请求
- 远端固定使用 curl GET
- 从 bkjob 进程环境变量 ES_USERNAME/ES_PASSWORD 读取 Basic Auth
- 仅允许 ES _cat、_cluster 读接口、_stats、_nodes 以及诊断类 GET 接口
"""


class EsReadonlyApiMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(
            _(
                "通过 DBM MCP 查询 ES 集群只读接口。"
                "实现方式：DBM 选择集群内 running 的 ES 节点，通过 bkjob 下发脚本，脚本使用 curl --request GET 请求 ES。"
                "ES 鉴权方式：脚本直接读取 bkjob 进程环境变量 ES_USERNAME/ES_PASSWORD，并使用 Basic Auth；变量缺失时直接报错。"
                "安全限制：只允许 GET 类只读接口，不支持也不会下发 POST、PUT、DELETE 等写操作方法；调用方无需也不能传入 ES 用户名密码。"
                "支持接口范围：1) 基础信息：/、/_license、/_remote/info；"
                "2) _cat 所有接口：/_cat、/_cat/*，如 /_cat/health、/_cat/indices、/_cat/nodes；"
                "3) 集群读接口：/_cluster/stats、/_cluster/stats/*、/_cluster/health、/_cluster/state、"
                "/_cluster/settings、/_cluster/pending_tasks、/_cluster/allocation/explain；"
                "4) 索引统计：/_stats、/_stats/*、/{index}/_stats、/{index}/_stats/*；"
                "5) 节点接口：/_nodes、/_nodes/*，如 /_nodes/stats、/_nodes/http；"
                "6) 诊断接口：/_tasks、/_tasks/{task_id}、/_recovery、/{index}/_recovery、"
                "/_segments、/{index}/_segments、/_shard_stores、/{index}/_shard_stores、"
                "/_settings、/{index}/_settings、/_mapping、/{index}/_mapping、/_alias、/{index}/_alias。"
                "_cat 接口未显式指定 format 时会默认追加 format=json，便于外部系统解析。"
            )
        ),
        request_slz=EsReadonlyApiInputSerializer,
        response_slz=EsReadonlyApiOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.ES_READONLY_API],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        name_prefix="es_readonly_api",
    )
    def query_readonly_api(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = query_es_readonly_api(
            bk_biz_id=validated_params["bk_biz_id"],
            cluster_domain=validated_params["cluster_domain"],
            path=validated_params["path"],
            query_params=validated_params.get("query_params"),
            scheme=validated_params.get("scheme", "http"),
            execute_role=validated_params.get("execute_role", "auto"),
            timeout=validated_params.get("timeout", 30),
            connect_timeout=validated_params.get("connect_timeout", 5),
            max_response_bytes=validated_params.get("max_response_bytes", 1024 * 1024),
        )
        return Response(result)
