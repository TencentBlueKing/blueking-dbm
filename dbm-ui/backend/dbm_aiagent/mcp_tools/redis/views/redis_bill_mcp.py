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

from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import auth_default, auth_parse_bizs, auth_parse_clusters
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.redis.impl.redis_bill_impl import (
    list_redis_specs,
    redis_cluster_apply,
    redis_cluster_cutoff,
    redis_cluster_new_apply,
    redis_delete_key_by_regex,
    redis_extract_key,
    redis_flush_db,
    redis_full_backup,
    redis_general_scale_down,
    redis_hotkey_analysis,
    redis_ins_apply,
    redis_load_modules,
    redis_master_slave_switch,
    redis_memory_analysis,
    redis_proxy_increase,
    redis_proxy_reduce,
    redis_proxy_reduce_by_ip,
    redis_reinstall_dbmon,
    redis_version_update_online,
)
from backend.dbm_aiagent.mcp_tools.redis.serializers.redis_bill import (
    ListRedisSpecsInputSerializer,
    ListRedisSpecsOutputSerializer,
    SubmitBillOutputSerializer,
    SubmitBillRedisAnalysisHotkeyInputSerializer,
    SubmitBillRedisBaseInputSerializer,
    SubmitBillRedisClusterApplyInputSerializer,
    SubmitBillRedisClusterNewApplyInputSerializer,
    SubmitBillRedisClusterScaleInputSerializer,
    SubmitBillRedisCutoffInputSerializer,
    SubmitBillRedisDeleteKeyInputSerializer,
    SubmitBillRedisExtractKeyInputSerializer,
    SubmitBillRedisFlushDBInputSerializer,
    SubmitBillRedisFullBackupInputSerializer,
    SubmitBillRedisInsApplyInputSerializer,
    SubmitBillRedisKeyStatInputSerializer,
    SubmitBillRedisLoadModulesInputSerializer,
    SubmitBillRedisMasterSlaveSwitchInputSerializer,
    SubmitBillRedisProxyReduceByIpInputSerializer,
    SubmitBillRedisProxyReduceOrIncreaseInputSerializer,
    SubmitBillRedisVersionUpdateInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.mcp import McpSkipPermission, McpTicketToolPermission

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

    @mcp_tools_api_decorator(
        description=str(
            _(
                "列出 Redis 资源规格（仅 enable=true 且备注 desc 含 mcp_allow 的条目，大小写不敏感），"
                "供创单前选型。可选 machine_type=proxy|TwemproxyRedisInstance|PredixyTendisplusCluster|"
                "TwemproxyTendisSSDInstance。"
                "返回 results/count：含 spec_id、cpu/mem/storage_spec、device_class、desc。"
                "创单须用此处的 spec_id，禁止凭名称瞎猜。"
            )
        ),
        request_slz=ListRedisSpecsInputSerializer,
        response_slz=ListRedisSpecsOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_BILL],
        name_prefix="redis_bill",
        permission_classes=[McpSkipPermission],
        mcp_auth_parser=auth_default,
    )
    def list_redis_specs(self, request, *args, **kwargs):
        p = self.params_validate(self.get_serializer_class())
        return Response(list_redis_specs(machine_type=p.get("machine_type") or ""))

    # =========================== 涉及机器资源类单据 begin ===========================
    # done: proxy扩容、proxy缩容、整机替换、集群部署（克隆申请）
    # todo: 容量变更、分片变更、类型变更、重做slave、迁移、回档
    # 高危todo：禁用、删除

    @mcp_tools_api_decorator(
        description=str(_("""参照已有集群的部署参数（架构、版本、规格、分片数、容灾级别等），克隆申请一个新的redis集群，机器来源固定为资源池""")),
        request_slz=SubmitBillRedisClusterApplyInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.REDIS_BILL],
        name_prefix="redis_bill",
    )
    def submit_bill_redis_cluster_apply(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain")
        new_cluster_name = self.get_param("new_cluster_name")
        keep_source_password = self.get_param("keep_source_password", False)

        return Response(
            redis_cluster_apply(request, bk_biz_id, cluster_domain, new_cluster_name, keep_source_password)
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                """参照已有主从的部署参数（版本、规格、容灾级别、城市、db数量等），克隆申请一个新的redis主从（TendisRedisInstance）；"""
                """机器来源默认资源池全新机器，可选指定cluster_domain下某个master的IP，在其所在主机对上追加部署"""
            )
        ),
        request_slz=SubmitBillRedisInsApplyInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.REDIS_BILL],
        name_prefix="redis_bill",
    )
    def submit_bill_redis_ins_apply(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain")
        new_cluster_name = self.get_param("new_cluster_name")
        spec_id = self.get_param("spec_id", None)
        keep_source_password = self.get_param("keep_source_password", False)
        master_ip = self.get_param("master_ip", None)

        return Response(
            redis_ins_apply(
                request, bk_biz_id, cluster_domain, new_cluster_name, spec_id, keep_source_password, master_ip
            )
        )

    @mcp_tools_api_decorator(
        description=str(_("""全新申请一个redis集群（不依赖任何已有集群，需自行指定架构类型、版本、规格、分片数、组数、容灾级别等），""" """机器来源固定为资源池""")),
        request_slz=SubmitBillRedisClusterNewApplyInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_bizs,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.REDIS_BILL],
        name_prefix="redis_bill",
    )
    def submit_bill_redis_cluster_new_apply(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_name = self.get_param("cluster_name")
        cluster_alias = self.get_param("cluster_alias", None)
        cluster_type = self.get_param("cluster_type")
        db_version = self.get_param("db_version")
        bk_cloud_id = self.get_param("bk_cloud_id", 0)
        city_code = self.get_param("city_code", "")
        disaster_tolerance_level = self.get_param("disaster_tolerance_level")
        proxy_spec_id = self.get_param("proxy_spec_id")
        proxy_count = self.get_param("proxy_count")
        backend_spec_id = self.get_param("backend_spec_id")
        group_num = self.get_param("group_num")
        shard_num = self.get_param("shard_num")
        proxy_pwd = self.get_param("proxy_pwd", None)
        port = self.get_param("port", 50000)
        apply_clb = self.get_param("apply_clb", False)
        apply_polaris = self.get_param("apply_polaris", False)

        return Response(
            redis_cluster_new_apply(
                request,
                bk_biz_id,
                cluster_name,
                cluster_type,
                db_version,
                proxy_spec_id,
                proxy_count,
                backend_spec_id,
                group_num,
                shard_num,
                cluster_alias=cluster_alias,
                bk_cloud_id=bk_cloud_id,
                city_code=city_code,
                disaster_tolerance_level=disaster_tolerance_level,
                proxy_pwd=proxy_pwd,
                port=port,
                apply_clb=apply_clb,
                apply_polaris=apply_polaris,
            )
        )

    @mcp_tools_api_decorator(
        description=str(_("""redis集群后端存储容量变更""")),
        request_slz=SubmitBillRedisClusterScaleInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.REDIS_BILL],
        name_prefix="redis_bill",
    )
    def submit_bill_redis_cluster_scale_down(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain")
        target_group_num = self.get_param("target_group_num")

        return Response(redis_general_scale_down(request, bk_biz_id, cluster_domain, target_group_num))

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
        proxy_change_count = abs(int(self.get_param("proxy_change_count")))

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

    @mcp_tools_api_decorator(
        description=str(_("""Redis集群主从切换（高危操作）""")),
        request_slz=SubmitBillRedisMasterSlaveSwitchInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.REDIS_BILL],
        name_prefix="redis_bill",
    )
    def submit_bill_redis_master_slave_switch(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain")
        master_ips = self.get_param("master_ips")

        return Response(redis_master_slave_switch(request, bk_biz_id, cluster_domain, master_ips))

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
