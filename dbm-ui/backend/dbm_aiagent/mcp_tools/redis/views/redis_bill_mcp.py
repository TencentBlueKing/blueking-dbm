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

from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import auth_parse_clusters
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.redis.impl.redis_bill_impl import (
    redis_cluster_cutoff,
    redis_delete_key_by_regex,
    redis_extract_key,
    redis_flush_db,
    redis_full_backup,
    redis_hotkey_analysis,
    redis_load_modules,
    redis_memory_analysis,
    redis_proxy_increase,
    redis_proxy_reduce,
    redis_proxy_reduce_by_ip,
    redis_reinstall_dbmon,
    redis_version_update_online,
)
from backend.dbm_aiagent.mcp_tools.redis.serializers.redis_bill import (
    SubmitBillOutputSerializer,
    SubmitBillRedisAnalysisHotkeyInputSerializer,
    SubmitBillRedisBaseInputSerializer,
    SubmitBillRedisCutoffInputSerializer,
    SubmitBillRedisDeleteKeyInputSerializer,
    SubmitBillRedisExtractKeyInputSerializer,
    SubmitBillRedisFlushDBInputSerializer,
    SubmitBillRedisFullBackupInputSerializer,
    SubmitBillRedisKeyStatInputSerializer,
    SubmitBillRedisLoadModulesInputSerializer,
    SubmitBillRedisProxyReduceByIpInputSerializer,
    SubmitBillRedisProxyReduceOrIncreaseInputSerializer,
    SubmitBillRedisVersionUpdateInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.mcp import McpTicketToolPermission

"""
单据相关 mcp
- proxy扩缩容-> 指定IP缩容proxy
- 备份
- 提取key
- 高危单据：删除key、清档、后端扩缩容、禁用、删除
- 其他操作类流程： 修改参数？执行命令？

- 标准化、内存分析、热key分析、访问来源、整机替换、启用CLB、启用北极星
"""


class RedisBillMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [DBManagePermission()]

    # =========================== 涉及机器资源类单据 begin ===========================
    # done: proxy扩容、proxy缩容、整机替换
    # todo: 集群部署、容量变更、分片变更、类型变更、重做slave、迁移、回档
    # 高危todo：禁用、删除

    @mcp_tools_api_decorator(
        description=str(_("""redis 整机替换""")),
        request_slz=SubmitBillRedisCutoffInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.REDIS_BILL],
        name_prefix="redis_bill",
    )
    def submit_bill_redis_cluster_cutoff(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain")
        cutoff_ips = self.get_param("cutoff_ips")

        return Response(redis_cluster_cutoff(request, bk_biz_id, cluster_domain, cutoff_ips))

    @mcp_tools_api_decorator(
        description=str(_("""减少Redis集群proxy数量单据, 缩容后的proxy数量不允许少于2""")),
        request_slz=SubmitBillRedisProxyReduceOrIncreaseInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.REDIS_BILL],
        name_prefix="redis_bill",
    )
    def submit_bill_redis_proxy_reduce(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain")
        proxy_change_count = self.get_param("proxy_change_count")

        return Response(redis_proxy_reduce(request, bk_biz_id, cluster_domain, proxy_change_count))

    @mcp_tools_api_decorator(
        description=str(_("""指定IP 下架redis集群的proxy""")),
        request_slz=SubmitBillRedisProxyReduceByIpInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.REDIS_BILL],
        name_prefix="redis_bill",
    )
    def submit_bill_redis_proxy_reduce_by_ip(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain")
        reduce_ips = self.get_param("reduce_ips")

        return Response(redis_proxy_reduce_by_ip(request, bk_biz_id, cluster_domain, reduce_ips))

    @mcp_tools_api_decorator(
        description=str(_("""增加Redis集群proxy数量单据""")),
        request_slz=SubmitBillRedisProxyReduceOrIncreaseInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.REDIS_BILL],
        name_prefix="redis_bill",
    )
    def submit_bill_redis_proxy_increase(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain")
        proxy_change_count = self.get_param("proxy_change_count")

        return Response(redis_proxy_increase(request, bk_biz_id, cluster_domain, proxy_change_count))

    # =========================== 涉及机器资源类单据 end ===========================

    # =========================== 集群常规操作类单据 begin ===========================
    # - 集群备份、提取key、删除key、清档、集群标准化、安装modules、版本升级
    # todo: 主从切换
    @mcp_tools_api_decorator(
        description=str(_("""Redis集群备份单据""")),
        request_slz=SubmitBillRedisFullBackupInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.REDIS_BILL],
        name_prefix="redis_bill",
    )
    def submit_bill_redis_full_backup(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        backup_type = self.get_param("backup_type")
        cluster_domain = self.get_param("cluster_domain")
        target = self.get_param("target")

        return Response(redis_full_backup(request, bk_biz_id, cluster_domain, backup_type, target))

    @mcp_tools_api_decorator(
        description=str(_("""Redis集群清档单据""")),
        request_slz=SubmitBillRedisFlushDBInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.REDIS_BILL],
        name_prefix="redis_bill",
    )
    def submit_bill_redis_flush_db(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain")
        is_force = self.get_param("is_force")
        is_backup = self.get_param("is_backup")

        return Response(redis_flush_db(request, bk_biz_id, cluster_domain, is_force, is_backup))

    @mcp_tools_api_decorator(
        description=str(_("""Redis集群提取key单据""")),
        request_slz=SubmitBillRedisExtractKeyInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.REDIS_BILL],
        name_prefix="redis_bill",
    )
    def submit_bill_redis_extract_key(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain")
        white_regex = self.get_param("white_regex")
        black_regex = self.get_param("black_regex")

        return Response(redis_extract_key(request, bk_biz_id, cluster_domain, white_regex, black_regex))

    @mcp_tools_api_decorator(
        description=str(_("""Redis集群删除key单据""")),
        request_slz=SubmitBillRedisDeleteKeyInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.REDIS_BILL],
        name_prefix="redis_bill",
    )
    def submit_bill_redis_delete_key_by_regex(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain")
        white_regex = self.get_param("white_regex")
        black_regex = self.get_param("black_regex")
        delete_rate = self.get_param("delete_rate")

        return Response(
            redis_delete_key_by_regex(request, bk_biz_id, cluster_domain, white_regex, black_regex, delete_rate)
        )

    @mcp_tools_api_decorator(
        description=str(_("""Redis集群标准化""")),
        request_slz=SubmitBillRedisBaseInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.REDIS_BILL],
        name_prefix="redis_bill",
    )
    def submit_bill_redis_reinstall_dbmon(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain")

        return Response(redis_reinstall_dbmon(request, bk_biz_id, cluster_domain))

    @mcp_tools_api_decorator(
        description=str(_("""Redis集群版本升级""")),
        request_slz=SubmitBillRedisVersionUpdateInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.REDIS_BILL],
        name_prefix="redis_bill",
    )
    def submit_bill_redis_version_update_online(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain")
        node_type = self.get_param("node_type")
        target_version = self.get_param("target_version")

        return Response(redis_version_update_online(request, bk_biz_id, cluster_domain, node_type, target_version))

    @mcp_tools_api_decorator(
        description=str(_("""Redis安装modules插件""")),
        request_slz=SubmitBillRedisLoadModulesInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.REDIS_BILL],
        name_prefix="redis_bill",
    )
    def submit_bill_redis_load_modules(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain")
        modules = self.get_param("modules")

        return Response(redis_load_modules(request, bk_biz_id, cluster_domain, modules))

    # =========================== 集群常规操作类单据 end ===========================

    # =========================== 集群分析类单据 begin ===========================
    # - 热key分析、内存分析
    # todo: 数据复制
    @mcp_tools_api_decorator(
        description=str(_("""提Redis热key分析单据""")),
        request_slz=SubmitBillRedisAnalysisHotkeyInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.REDIS_BILL],
        name_prefix="redis_bill",
    )
    def submit_bill_redis_hotkey_analysis(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain")
        analysis_time = self.get_param("analysis_time")
        ins = self.get_param("ins")

        return Response(redis_hotkey_analysis(request, bk_biz_id, cluster_domain, analysis_time, ins))

    @mcp_tools_api_decorator(
        description=str(_("""Redis内存分析""")),
        request_slz=SubmitBillRedisKeyStatInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.REDIS_BILL],
        name_prefix="redis_bill",
    )
    def submit_bill_redis_memory_analysis(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain")
        ins = self.get_param("ins")

        return Response(redis_memory_analysis(request, bk_biz_id, cluster_domain, ins))
