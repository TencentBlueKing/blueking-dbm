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
from rest_framework.response import Response

from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import auth_default, auth_parse_bizs
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.mongodb.auth_parser.permissions import McpMongoApplyPermission
from backend.dbm_aiagent.mcp_tools.mongodb.impl.mongodb_bill import (
    list_mongodb_specs,
    submit_mongodb_replicaset_apply_bill,
    submit_mongodb_shard_apply_bill,
)
from backend.dbm_aiagent.mcp_tools.mongodb.serializers.mongodb_bill import (
    ListMongoDBSpecsInputSerializer,
    ListMongoDBSpecsOutputSerializer,
    SubmitBillMongoReplicaSetApplyInputSerializer,
    SubmitBillMongoShardApplyInputSerializer,
    SubmitBillOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.mcp import McpSkipPermission

_BILL_DECORATOR_COMMON = {
    "tags": [DBMMCPTags.READ, DBMMCPTags.WRITE],
    "mcp": [DBMMcpTools.MONGODB_BILL],
    "name_prefix": "mongodb_bill",
    "permission_classes": [McpMongoApplyPermission],
    "mcp_auth_parser": auth_parse_bizs,
}


class MongoBillMcpToolsViewSet(McpToolsViewSet):
    """MongoDB 单据 MCP：规格查询 + 部署副本集 / 分片集群。挂载 server：mongodb-bill。"""

    default_permission_class = [DBManagePermission()]

    @mcp_tools_api_decorator(
        description=str(
            _(
                "列出 MongoDB 资源规格（仅 enable=true 且备注 desc 含 mcp_allow 的条目，大小写不敏感），"
                "供创单前选型。可选 machine_type=mongodb|mongo_config|mongos。"
                "返回 results/count：含 spec_id、cpu/mem/storage_spec、device_class、desc。"
                "创单须用此处的 spec_id，禁止凭名称瞎猜。"
            )
        ),
        request_slz=ListMongoDBSpecsInputSerializer,
        response_slz=ListMongoDBSpecsOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MONGODB_BILL],
        name_prefix="mongodb_bill",
        permission_classes=[McpSkipPermission],
        mcp_auth_parser=auth_default,
    )
    def list_mongodb_specs(self, request, *args, **kwargs):
        p = self.params_validate(self.get_serializer_class())
        return Response(list_mongodb_specs(machine_type=p.get("machine_type") or ""))

    @mcp_tools_api_decorator(
        description=str(
            _(
                "创建 MongoDB 副本集集群部署单据（MONGODB_REPLICASET_APPLY）。"
                "优先 resource_pool：传 bk_biz_id、db_app_abbr、db_version、spec_id、"
                "replica_count/node_count/node_replica_count（node_count 固定为 3；"
                "replica_count 须能被 node_replica_count 整除）、"
                "replica_sets（数量=replica_count，含 set_id/domain）。"
                "city_code 随机用 default。返回 bill_id / bill_url。"
            )
        ),
        request_slz=SubmitBillMongoReplicaSetApplyInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        **_BILL_DECORATOR_COMMON,
    )
    def submit_bill_replicaset_apply(self, request, *args, **kwargs):
        p = self.params_validate(self.get_serializer_class())
        return Response(
            submit_mongodb_replicaset_apply_bill(
                bk_biz_id=p["bk_biz_id"],
                bk_cloud_id=p["bk_cloud_id"],
                db_app_abbr=p["db_app_abbr"],
                city_code=p.get("city_code") or "default",
                disaster_tolerance_level=p["disaster_tolerance_level"],
                db_version=p["db_version"],
                start_port=p["start_port"],
                replica_count=p["replica_count"],
                node_count=p["node_count"],
                node_replica_count=p["node_replica_count"],
                replica_sets=p["replica_sets"],
                spec_id=p["spec_id"],
                oplog_percent=p["oplog_percent"],
                ip_source=p["ip_source"],
                resource_spec=p.get("resource_spec"),
                nodes=p.get("nodes"),
                creator=request.user.username,
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                "创建 MongoDB 分片集群部署单据（MONGODB_SHARD_APPLY）。"
                "优先 resource_pool：传 bk_biz_id、db_app_abbr、cluster_name、db_version、"
                "shard_num/shard_machine_group（shard_num 须能被组数整除）、"
                "resource_spec 含 mongodb/mongo_config/mongos（各含 spec_id 与 count）。"
                "每个机器组的 mongodb count 固定为 3，mongo_config count 固定为 3，"
                "mongos count 至少为 2。返回 bill_id / bill_url。"
            )
        ),
        request_slz=SubmitBillMongoShardApplyInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        **_BILL_DECORATOR_COMMON,
    )
    def submit_bill_shard_apply(self, request, *args, **kwargs):
        p = self.params_validate(self.get_serializer_class())
        return Response(
            submit_mongodb_shard_apply_bill(
                bk_biz_id=p["bk_biz_id"],
                bk_cloud_id=p["bk_cloud_id"],
                db_app_abbr=p["db_app_abbr"],
                city_code=p.get("city_code") or "default",
                disaster_tolerance_level=p["disaster_tolerance_level"],
                cluster_name=p["cluster_name"],
                cluster_alias=p.get("cluster_alias") or "",
                db_version=p["db_version"],
                start_port=p["start_port"],
                oplog_percent=p["oplog_percent"],
                shard_machine_group=p["shard_machine_group"],
                shard_num=p["shard_num"],
                ip_source=p["ip_source"],
                resource_spec=p.get("resource_spec"),
                nodes=p.get("nodes"),
                creator=request.user.username,
            )
        )
