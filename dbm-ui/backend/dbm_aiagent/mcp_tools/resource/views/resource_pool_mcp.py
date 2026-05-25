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

from backend.db_services.dbresource.serializers import ResourceListSerializer
from backend.db_services.dbresource.views.resource import DBResourceViewSet
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.resource.impl.resource_pool_host import (
    resource_delete,
    resource_import_host,
    resource_transfer_pool,
    resource_undo_import,
)
from backend.dbm_aiagent.mcp_tools.resource.serializers.resource_pool import (
    ResourceHostDeleteOutputSerializer,
    ResourceHostDeleteSerializer,
    ResourceImportHostSerializer,
    ResourceImportOutPutSerializer,
    ResourceListOutPutSerializer,
    ResourceTransferPoolOutPutSerializer,
    ResourceTransferPoolSerializer,
    ResourceUnDoImportOutPutSerializer,
    ResourceUnDoImportSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.drf_perm.base import ResourceActionPermission

logger = logging.getLogger("resource")


class ResourcePoolMcpToolsViewSet(McpToolsViewSet):
    action_permission_map = {
        ("resource_import", "resource_undo_import", "resource_transfer_pool"): [
            ResourceActionPermission([ActionEnum.RESOURCE_POLL_MANAGE])
        ]
    }
    default_permission_class = [ResourceActionPermission([ActionEnum.RESOURCE_MANAGE])]

    @mcp_tools_api_decorator(
        description=str(
            _(
                """
        指定主机ip, 主机名称, 主机ipv6等信息导入资源池
        支持的参数： ip  类型str 多选英文逗号隔开
                   host_name 类型str 多选英文逗号隔开
                   ip_v6 类型str 多选英文逗号隔开
                   for_biz 类型int 代表要带入的主机所属的业务，默认公共资源池
                   resource_type 类型str 代表要带入的主机所属的组件类型，默认是通用
        """
            )
        ),
        request_slz=ResourceImportHostSerializer,
        response_slz=ResourceImportOutPutSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.RESOURCE_POOL],
        name_prefix="resource_pool",
    )
    def resource_import(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        return Response(resource_import_host(validated_params, request.user.username))

    @mcp_tools_api_decorator(
        description=str(
            _(
                """
        指定主机ip 主机id等信息撤销主机导入 需要撤销导入的主机需要都处于资源池中 且未做过别的操作
        支持的参数： ip  类型str 多选英文逗号隔开
                   host_id 类型str 多选英文逗号隔开
        参数ip和host_id可以一起传 但是二者需要是不同主机的信息 同主机的ip和host id不要同时传
        """
            )
        ),
        request_slz=ResourceUnDoImportSerializer,
        response_slz=ResourceUnDoImportOutPutSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.RESOURCE_POOL],
        name_prefix="resource_pool",
    )
    def resource_undo_import(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        return Response(resource_undo_import(validated_params, request.user.username))

    @mcp_tools_api_decorator(
        description=str(
            _(
                """
        指定主机ip 主机id等信息将主机删除（移出主机池，会回到cc待回收） 需要确保删除的主机都处于故障池中
        支持从海磊回收主机
        支持的参数： ip  类型str 多选英文逗号隔开
                   host_id 类型str 多选英文逗号隔开
                   remark 类型 str 非必传
                   hcm_recycle 类型 bool 非必填
        参数ip和host_id可以一起传 但是二者需要是不同主机的信息 同主机的ip和host id不要同时传
        """
            )
        ),
        request_slz=ResourceHostDeleteSerializer,
        response_slz=ResourceHostDeleteOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.RESOURCE_POOL],
        name_prefix="resource_pool",
    )
    def resource_delete(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        return Response(resource_delete(validated_params, request.user.username))

    @mcp_tools_api_decorator(
        description=str(
            _(
                """
        指定主机ip 主机id等信息将主机转移至其它池
        可支持的转移： 资源池 ---> 故障池 资源池 ---> 待回收池  故障池 ---> 待回收池
        支持的参数： ip  类型str 多选英文逗号隔开
                   host_id 类型str 多选英文逗号隔开
                   target 类型 str 值有 fault/recycle
                   remark 类型 str 非必传
        参数ip和host_id可以一起传 但是二者需要是不同主机的信息 同主机的ip和host id不要同时传
        """
            )
        ),
        request_slz=ResourceTransferPoolSerializer,
        response_slz=ResourceTransferPoolOutPutSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.RESOURCE_POOL],
        name_prefix="resource_pool",
    )
    def resource_transfer_pool(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        return Response(resource_transfer_pool(validated_params, request.user.username))

    @mcp_tools_api_decorator(
        description=str(
            _(
                """
        查询资源池主机
        支持的参数：limit  int 返回多少条数据
                  offset int 跳过多少条数据返回
                  hosts  str 主机ip,多个英文逗号隔开
                  for_biz int 所属业务
                  for_bizs []int 所属业务列表
                  resource_type str 所属db类型
                  resource_types []str 所属db类型列表
                  city  str  城市,地域 多个英文逗号隔开
                  subzone_ids str  园区id 多个英文逗号隔开
                  subzones str  园区名称 多个英文逗号隔开
                  cpu str cpu范围 如 '0-2'代表0-2核 '2-'代表大于等于2核 '-6'代表小于等于6核
                  mem str 内存范围 如 '0-2'代表0-2G '2-'代表大于等于2G '-6'代表小于等于6G
        """
            )
        ),
        request_slz=ResourceListSerializer,
        response_slz=ResourceListOutPutSerializer,
        reference_view=DBResourceViewSet.resource_list,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.RESOURCE_POOL],
        name_prefix="resource_pool",
    )
    def resource_list(self, request, *args, **kwargs):
        return Response()
