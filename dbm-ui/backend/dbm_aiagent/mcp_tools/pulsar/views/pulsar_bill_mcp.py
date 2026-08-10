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
import logging.config

from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.pulsar.impl.pulsar_bill import (
    submit_pulsar_apply_bill,
    submit_pulsar_destroy_bill,
    submit_pulsar_disable_bill,
    submit_pulsar_enable_bill,
    submit_pulsar_reboot_bill,
    submit_pulsar_replace_bill,
    submit_pulsar_scale_up_bill,
    submit_pulsar_shrink_bill,
)
from backend.dbm_aiagent.mcp_tools.pulsar.serializers.pulsar_bill import (
    SubmitBillOutputSerializer,
    SubmitBillPulsarApplyInputSerializer,
    SubmitBillPulsarRebootInputSerializer,
    SubmitBillPulsarReplaceInputSerializer,
    SubmitBillPulsarScaleUpInputSerializer,
    SubmitBillPulsarShrinkInputSerializer,
    SubmitBillPulsarTakeDownInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import RejectPermission

logger = logging.getLogger("flow")

"""
Pulsar 单据相关的 mcp
- 集群扩容/缩容/替换（支持 broker 和 bookkeeper 两个角色）
- 实例重启
- 集群启用/禁用/删除
- 集群部署
"""


class PulsarBillMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(
            _(
                "Pulsar集群扩容单据(支持资源池和手工输入两种方式)。"
                "可同时扩容 broker 和 bookkeeper 两个角色，zookeeper 固定3台不支持扩容。"
                "用户只说'扩容N台broker/bookkeeper'而未指明规格时，不必追问规格，"
                "resource_spec 传 {'broker': {'count': N}} 即可，会自动沿用该角色现有节点的规格。"
            )
        ),
        request_slz=SubmitBillPulsarScaleUpInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.PULSAR_BILL],
        name_prefix="pulsar_bill",
    )
    def submit_bill_scale_up(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = submit_pulsar_scale_up_bill(
            bk_biz_id=validated_params["bk_biz_id"],
            cluster_domain=validated_params["cluster_domain"],
            ip_source=validated_params["ip_source"],
            nodes=validated_params.get("nodes"),
            resource_spec=validated_params.get("resource_spec"),
            creator=request.user.username,
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(
            _(
                "Pulsar集群缩容单据。"
                "注意事项："
                "1. nodes参数需要包含待缩容节点的(ip, bk_host_id, bk_cloud_id)，可含 broker/bookkeeper 两个角色"
                "2. 当用户只提供IP地址时，必须先调用 pulsar_query_meta_cluster_overview 获取完整的节点信息"
                "3. broker 至少保留1台，bookkeeper 至少保留2台，不支持缩容 zookeeper"
            )
        ),
        request_slz=SubmitBillPulsarShrinkInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.PULSAR_BILL],
        name_prefix="pulsar_bill",
    )
    def submit_bill_shrink(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = submit_pulsar_shrink_bill(
            bk_biz_id=validated_params["bk_biz_id"],
            cluster_domain=validated_params["cluster_domain"],
            nodes=validated_params["nodes"],
            creator=request.user.username,
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(
            _(
                "Pulsar集群替换单据，用于故障机器或裁撤机器的替换。"
                "支持 broker/bookkeeper/zookeeper 三个角色，替换前后各角色数量必须一致。"
                "当用户只提供IP地址时，必须先调用 pulsar_query_meta_cluster_overview 获取完整的节点信息"
            )
        ),
        request_slz=SubmitBillPulsarReplaceInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.PULSAR_BILL],
        name_prefix="pulsar_bill",
    )
    def submit_bill_replace(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = submit_pulsar_replace_bill(
            bk_biz_id=validated_params["bk_biz_id"],
            cluster_domain=validated_params["cluster_domain"],
            old_nodes=validated_params["old_nodes"],
            ip_source=validated_params["ip_source"],
            new_nodes=validated_params.get("new_nodes"),
            resource_spec=validated_params.get("resource_spec"),
            creator=request.user.username,
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(
            _(
                "Pulsar实例重启单据。"
                "instance_list 中每个实例需包含 ip/port/instance_id/bk_host_id/bk_cloud_id，"
                "可通过 pulsar_query_meta_cluster_overview 的 nodes 字段获取"
            )
        ),
        request_slz=SubmitBillPulsarRebootInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.PULSAR_BILL],
        name_prefix="pulsar_bill",
    )
    def submit_bill_reboot(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = submit_pulsar_reboot_bill(
            bk_biz_id=validated_params["bk_biz_id"],
            cluster_domain=validated_params["cluster_domain"],
            instance_list=validated_params["instance_list"],
            creator=request.user.username,
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(_("Pulsar集群启用单据，将已禁用的集群重新启用")),
        request_slz=SubmitBillPulsarTakeDownInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.PULSAR_BILL],
        name_prefix="pulsar_bill",
    )
    def submit_bill_enable(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = submit_pulsar_enable_bill(
            bk_biz_id=validated_params["bk_biz_id"],
            cluster_domain=validated_params["cluster_domain"],
            creator=request.user.username,
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(_("Pulsar集群禁用单据，禁用后集群不可访问，是删除集群的前置步骤")),
        request_slz=SubmitBillPulsarTakeDownInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.PULSAR_BILL],
        name_prefix="pulsar_bill",
    )
    def submit_bill_disable(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = submit_pulsar_disable_bill(
            bk_biz_id=validated_params["bk_biz_id"],
            cluster_domain=validated_params["cluster_domain"],
            creator=request.user.username,
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(_("Pulsar集群删除单据，会清理集群所有数据和元信息，需集群已处于禁用状态。该操作不可逆，务必与用户确认")),
        request_slz=SubmitBillPulsarTakeDownInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.PULSAR_BILL],
        name_prefix="pulsar_bill",
    )
    def submit_bill_destroy(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = submit_pulsar_destroy_bill(
            bk_biz_id=validated_params["bk_biz_id"],
            cluster_domain=validated_params["cluster_domain"],
            creator=request.user.username,
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(
            _(
                "Pulsar集群部署单据。"
                "约束："
                "1. zookeeper 必须恰好3台，bookkeeper 至少2台，broker 至少1台"
                "2. replication_num 取值范围 2 到 bookkeeper 台数"
                "3. ack_quorum 必须小于等于 replication_num"
            )
        ),
        request_slz=SubmitBillPulsarApplyInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.PULSAR_BILL],
        name_prefix="pulsar_bill",
    )
    def submit_bill_apply(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = submit_pulsar_apply_bill(
            bk_biz_id=validated_params["bk_biz_id"],
            cluster_name=validated_params["cluster_name"],
            cluster_alias=validated_params.get("cluster_alias", ""),
            db_app_abbr=validated_params["db_app_abbr"],
            city_code=validated_params["city_code"],
            db_version=validated_params["db_version"],
            bk_cloud_id=validated_params.get("bk_cloud_id", 0),
            port=validated_params["port"],
            partition_num=validated_params["partition_num"],
            retention_hours=validated_params["retention_hours"],
            replication_num=validated_params["replication_num"],
            ack_quorum=validated_params["ack_quorum"],
            ip_source=validated_params["ip_source"],
            nodes=validated_params.get("nodes"),
            resource_spec=validated_params.get("resource_spec"),
            creator=request.user.username,
        )
        return Response(result)
