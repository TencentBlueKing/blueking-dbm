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
from backend.dbm_aiagent.mcp_tools.es.impl.es_bill import (
    submit_es_apply_bill,
    submit_es_bind_clb_bill,
    submit_es_create_clb_bill,
    submit_es_create_polaris_bill,
    submit_es_delete_polaris_bill,
    submit_es_destroy_bill,
    submit_es_disable_bill,
    submit_es_enable_bill,
    submit_es_replace_bill,
    submit_es_scale_up_bill,
    submit_es_shrink_bill,
    submit_es_unbind_clb_bill,
)
from backend.dbm_aiagent.mcp_tools.es.serializers.es_bill import (
    SubmitBillEsApplyInputSerializer,
    SubmitBillEsDestroyInputSerializer,
    SubmitBillEsDisableInputSerializer,
    SubmitBillEsEnableInputSerializer,
    SubmitBillEsNameServiceInputSerializer,
    SubmitBillEsReplaceInputSerializer,
    SubmitBillEsScaleUpInputSerializer,
    SubmitBillEsShrinkInputSerializer,
    SubmitBillOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import RejectPermission

logger = logging.getLogger("flow")

"""
ES 单据相关的 mcp
- 集群部署
- 集群扩容
- 集群缩容
- 集群替换
- 集群启用/禁用/删除
- CLB / Polaris 名字服务
"""


class EsBillMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(_("ES集群部署单据")),
        request_slz=SubmitBillEsApplyInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.ES_BILL],
        name_prefix="es_bill",
    )
    def submit_bill_apply(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        bk_biz_id = validated_params["bk_biz_id"]
        cluster_name = validated_params["cluster_name"]
        resource_spec = validated_params["resource_spec"]
        db_app_abbr = validated_params["db_app_abbr"]
        version = validated_params["version"]
        http_port = validated_params.get("http_port", 9200)
        city_code = validated_params["city_code"]
        cluster_alias = validated_params.get("cluster_alias", "")
        bk_cloud_id = validated_params.get("bk_cloud_id", 0)
        disaster_tolerance_level = validated_params.get("disaster_tolerance_level", "MAX_EACH_ZONE_EQUAL")

        result = submit_es_apply_bill(
            bk_biz_id=bk_biz_id,
            cluster_name=cluster_name,
            resource_spec=resource_spec,
            db_app_abbr=db_app_abbr,
            version=version,
            http_port=http_port,
            city_code=city_code,
            cluster_alias=cluster_alias,
            bk_cloud_id=bk_cloud_id,
            disaster_tolerance_level=disaster_tolerance_level,
            creator=request.user.username,
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(_("ES集群扩容单据")),
        request_slz=SubmitBillEsScaleUpInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.ES_BILL],
        name_prefix="es_bill",
    )
    def submit_bill_scale_up(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        bk_biz_id = validated_params["bk_biz_id"]
        cluster_domain = validated_params["cluster_domain"]
        resource_spec = validated_params["resource_spec"]

        result = submit_es_scale_up_bill(
            bk_biz_id=bk_biz_id,
            cluster_domain=cluster_domain,
            resource_spec=resource_spec,
            creator=request.user.username,
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(_("ES集群缩容单据")),
        request_slz=SubmitBillEsShrinkInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.ES_BILL],
        name_prefix="es_bill",
    )
    def submit_bill_shrink(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        bk_biz_id = validated_params["bk_biz_id"]
        cluster_domain = validated_params["cluster_domain"]
        old_nodes = validated_params["old_nodes"]

        result = submit_es_shrink_bill(
            bk_biz_id=bk_biz_id,
            cluster_domain=cluster_domain,
            old_nodes=old_nodes,
            creator=request.user.username,
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(_("ES集群替换单据")),
        request_slz=SubmitBillEsReplaceInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.ES_BILL],
        name_prefix="es_bill",
    )
    def submit_bill_replace(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        bk_biz_id = validated_params["bk_biz_id"]
        cluster_domain = validated_params["cluster_domain"]
        old_nodes = validated_params["old_nodes"]
        resource_spec = validated_params.get("resource_spec")

        result = submit_es_replace_bill(
            bk_biz_id=bk_biz_id,
            cluster_domain=cluster_domain,
            old_nodes=old_nodes,
            resource_spec=resource_spec,
            creator=request.user.username,
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(_("ES集群启用单据")),
        request_slz=SubmitBillEsEnableInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        tags=[DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.ES_BILL],
        name_prefix="es_bill",
    )
    def submit_bill_enable(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        bk_biz_id = validated_params["bk_biz_id"]
        cluster_domain = validated_params["cluster_domain"]

        result = submit_es_enable_bill(
            bk_biz_id=bk_biz_id,
            cluster_domain=cluster_domain,
            creator=request.user.username,
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(_("ES集群禁用单据")),
        request_slz=SubmitBillEsDisableInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        tags=[DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.ES_BILL],
        name_prefix="es_bill",
    )
    def submit_bill_disable(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        bk_biz_id = validated_params["bk_biz_id"]
        cluster_domain = validated_params["cluster_domain"]

        result = submit_es_disable_bill(
            bk_biz_id=bk_biz_id,
            cluster_domain=cluster_domain,
            creator=request.user.username,
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(_("ES集群删除单据")),
        request_slz=SubmitBillEsDestroyInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        tags=[DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.ES_BILL],
        name_prefix="es_bill",
    )
    def submit_bill_destroy(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        bk_biz_id = validated_params["bk_biz_id"]
        cluster_domain = validated_params["cluster_domain"]

        result = submit_es_destroy_bill(
            bk_biz_id=bk_biz_id,
            cluster_domain=cluster_domain,
            creator=request.user.username,
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(_("ES创建CLB单据，为集群创建CLB负载均衡")),
        request_slz=SubmitBillEsNameServiceInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        tags=[DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.ES_BILL],
        name_prefix="es_bill",
    )
    def submit_bill_create_clb(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        bk_biz_id = validated_params["bk_biz_id"]
        cluster_domain = validated_params["cluster_domain"]

        result = submit_es_create_clb_bill(
            bk_biz_id=bk_biz_id,
            cluster_domain=cluster_domain,
            creator=request.user.username,
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(_("ES主域名绑定CLB单据")),
        request_slz=SubmitBillEsNameServiceInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        tags=[DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.ES_BILL],
        name_prefix="es_bill",
    )
    def submit_bill_bind_clb(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        bk_biz_id = validated_params["bk_biz_id"]
        cluster_domain = validated_params["cluster_domain"]

        result = submit_es_bind_clb_bill(
            bk_biz_id=bk_biz_id,
            cluster_domain=cluster_domain,
            creator=request.user.username,
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(_("ES主域名解绑CLB单据")),
        request_slz=SubmitBillEsNameServiceInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        tags=[DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.ES_BILL],
        name_prefix="es_bill",
    )
    def submit_bill_unbind_clb(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        bk_biz_id = validated_params["bk_biz_id"]
        cluster_domain = validated_params["cluster_domain"]

        result = submit_es_unbind_clb_bill(
            bk_biz_id=bk_biz_id,
            cluster_domain=cluster_domain,
            creator=request.user.username,
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(_("ES创建北极星(Polaris)单据")),
        request_slz=SubmitBillEsNameServiceInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        tags=[DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.ES_BILL],
        name_prefix="es_bill",
    )
    def submit_bill_create_polaris(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        bk_biz_id = validated_params["bk_biz_id"]
        cluster_domain = validated_params["cluster_domain"]

        result = submit_es_create_polaris_bill(
            bk_biz_id=bk_biz_id,
            cluster_domain=cluster_domain,
            creator=request.user.username,
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(_("ES删除北极星(Polaris)单据")),
        request_slz=SubmitBillEsNameServiceInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        tags=[DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.ES_BILL],
        name_prefix="es_bill",
    )
    def submit_bill_delete_polaris(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        bk_biz_id = validated_params["bk_biz_id"]
        cluster_domain = validated_params["cluster_domain"]

        result = submit_es_delete_polaris_bill(
            bk_biz_id=bk_biz_id,
            cluster_domain=cluster_domain,
            creator=request.user.username,
        )
        return Response(result)
