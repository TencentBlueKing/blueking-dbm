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

from backend.db_meta.models import Cluster
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.redis.serializers.redis_bill import (
    SubmitBillOutputSerializer,
    SubmitBillRedisBaseInputSerializer,
    SubmitBillRedisDeleteKeyInputSerializer,
    SubmitBillRedisExtractKeyInputSerializer,
    SubmitBillRedisFlushDBInputSerializer,
    SubmitBillRedisFullBackupInputSerializer,
    SubmitBillRedisProxyReduceByIpInputSerializer,
    SubmitBillRedisProxyReduceOrIncreaseInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import RejectPermission
from backend.ticket.builders.common.base import IpSource
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket

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
    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(_("""Redis集群备份单据""")),
        request_slz=SubmitBillRedisFullBackupInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.REDIS_BILL],
        name_prefix="redis_bill",
    )
    def submit_bill_redis_full_backup(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        backup_type = self.get_param("backup_type")
        cluster_domain = self.get_param("cluster_domain")
        target = self.get_param("target")

        cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
        cluster_id = cluster_obj.id
        ticket_param = {
            "bk_biz_id": bk_biz_id,
            "ticket_type": TicketType.REDIS_BACKUP,
            "creator": request.user.username,
            "helpers": [],
            "remark": "mcp backup ticket",
            "details": {
                "rules": [
                    {"backup_type": backup_type, "cluster_id": cluster_id, "domain": cluster_domain, "target": target}
                ]
            },
        }

        tk = Ticket.create_ticket(**ticket_param)
        return Response({"bill_id": tk.pk, "bill_url": tk.url})

    @mcp_tools_api_decorator(
        description=str(_("""减少Redis集群proxy数量单据, 缩容后的proxy数量不允许少于2""")),
        request_slz=SubmitBillRedisProxyReduceOrIncreaseInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.REDIS_BILL],
        name_prefix="redis_bill",
    )
    def submit_bill_redis_proxy_reduce(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain")
        proxy_change_count = self.get_param("proxy_change_count")

        cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
        cluster_id = cluster_obj.id
        cluster_proxy_count = cluster_obj.proxyinstance_set.count()
        count = cluster_proxy_count - proxy_change_count
        ticket_param = {
            "bk_biz_id": bk_biz_id,
            "creator": request.user.username,
            "helpers": [],
            "remark": "mcp proxy reduce ticket",
            "ticket_type": TicketType.REDIS_PROXY_SCALE_DOWN,
            "details": {
                "infos": [
                    {"cluster_id": cluster_id, "online_switch_type": "user_confirm", "target_proxy_count": count}
                ],
            },
        }
        tk = Ticket.create_ticket(**ticket_param)
        return Response({"bill_id": tk.pk, "bill_url": tk.url})

    @mcp_tools_api_decorator(
        description=str(_("""指定IP 下架redis集群的proxy""")),
        request_slz=SubmitBillRedisProxyReduceByIpInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.REDIS_BILL],
        name_prefix="redis_bill",
    )
    def submit_bill_redis_proxy_reduce_by_ip(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain")
        reduce_ips = self.get_param("reduce_ips")

        cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
        cluster_id = cluster_obj.id
        proxys = cluster_obj.proxyinstance_set.all()
        count = len(proxys) - len(reduce_ips)
        remark = r"mcp proxy {} reduce ticket".format(reduce_ips)
        if count < 2:
            return Response({"error": _("缩容后集群proxy小于2，不满足亲和度要求")})
        # 获取主机相关的数据
        proxy_reduced_hosts = []
        for proxy in proxys:
            machine = proxy.machine
            if machine.ip in reduce_ips:
                proxy_reduced_hosts.append(
                    {
                        "ip": machine.ip,
                        "bk_biz_id": machine.bk_biz_id,
                        "bk_host_id": machine.bk_host_id,
                        "bk_cloud_id": machine.bk_cloud_id,
                    }
                )
        # 检查是否存在传入的IP与集群对应不上的
        if len(reduce_ips) != len(proxy_reduced_hosts):
            for proxy in proxy_reduced_hosts:
                reduce_ips.remove(proxy["ip"])
            return Response({"error": _("存在不属于集群{}的proxy{}".format(cluster_domain, reduce_ips))})
        ticket_param = {
            "bk_biz_id": bk_biz_id,
            "creator": request.user.username,
            "helpers": [],
            "remark": remark,
            "ticket_type": TicketType.REDIS_PROXY_SCALE_DOWN,
            "details": {
                "infos": [
                    {
                        "old_nodes": {"proxy_reduced_hosts": proxy_reduced_hosts},
                        "cluster_id": cluster_id,
                        "online_switch_type": "user_confirm",
                        "target_proxy_count": count,
                    }
                ],
            },
        }
        tk = Ticket.create_ticket(**ticket_param)
        return Response({"bill_id": tk.pk, "bill_url": tk.url})

    @mcp_tools_api_decorator(
        description=str(_("""增加Redis集群proxy数量单据""")),
        request_slz=SubmitBillRedisProxyReduceOrIncreaseInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.REDIS_BILL],
        name_prefix="redis_bill",
    )
    def submit_bill_redis_proxy_increase(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain")
        proxy_change_count = self.get_param("proxy_change_count")

        cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
        cluster_id = cluster_obj.id
        # 获取spec_id
        spec_id = cluster_obj.proxyinstance_set.first().machine.spec_id
        ticket_param = {
            "bk_biz_id": bk_biz_id,
            "creator": request.user.username,
            "helpers": [],
            "remark": "mcp proxy increase ticket",
            "ticket_type": TicketType.REDIS_PROXY_SCALE_UP,
            "details": {
                "infos": [
                    {
                        "bk_cloud_id": cluster_obj.bk_cloud_id,
                        "cluster_id": cluster_id,
                        "resource_spec": {"proxy": {"count": proxy_change_count, "spec_id": spec_id}},
                    }
                ],
                "ip_source": IpSource.RESOURCE_POOL.value,
                "shrink_type": "QUANTITY",
            },
        }

        tk = Ticket.create_ticket(**ticket_param)
        return Response({"bill_id": tk.pk, "bill_url": tk.url})

    @mcp_tools_api_decorator(
        description=str(_("""Redis集群清档单据""")),
        request_slz=SubmitBillRedisFlushDBInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.REDIS_BILL],
        name_prefix="redis_bill",
    )
    def submit_bill_flush_db(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain")
        is_force = self.get_param("is_force")
        is_backup = self.get_param("is_backup")

        cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
        cluster_id = cluster_obj.id
        cluster_type = cluster_obj.cluster_type
        ticket_param = {
            "bk_biz_id": bk_biz_id,
            "ticket_type": TicketType.REDIS_PURGE,
            "creator": request.user.username,
            "helpers": [],
            "remark": "mcp redis flushdb ticket",
            "details": {
                "rules": [
                    {
                        "force": is_force,
                        "backup": is_backup,
                        "domain": cluster_domain,
                        "db_list": [],
                        "flushall": True,
                        "cluster_id": cluster_id,
                        "cluster_type": cluster_type,
                    }
                ]
            },
        }

        tk = Ticket.create_ticket(**ticket_param)
        return Response({"bill_id": tk.pk, "bill_url": tk.url})

    @mcp_tools_api_decorator(
        description=str(_("""Redis集群提取key单据""")),
        request_slz=SubmitBillRedisExtractKeyInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.REDIS_BILL],
        name_prefix="redis_bill",
    )
    def submit_bill_extract_key(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain")
        white_regex = self.get_param("white_regex")
        black_regex = self.get_param("black_regex")

        cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
        cluster_id = cluster_obj.id
        ticket_param = {
            "bk_biz_id": bk_biz_id,
            "ticket_type": TicketType.REDIS_KEYS_EXTRACT,
            "creator": request.user.username,
            "helpers": [],
            "remark": "mcp redis extract key ticket",
            "details": {
                "rules": [
                    {
                        "domain": cluster_domain,
                        "cluster_id": cluster_id,
                        "black_regex": black_regex,
                        "white_regex": white_regex,
                    }
                ]
            },
        }

        tk = Ticket.create_ticket(**ticket_param)
        return Response({"bill_id": tk.pk, "bill_url": tk.url})

    @mcp_tools_api_decorator(
        description=str(_("""Redis集群删除key单据""")),
        request_slz=SubmitBillRedisDeleteKeyInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.REDIS_BILL],
        name_prefix="redis_bill",
    )
    def submit_bill_delete_key_by_regex(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain")
        white_regex = self.get_param("white_regex")
        black_regex = self.get_param("black_regex")
        delete_rate = self.get_param("delete_rate")

        cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
        cluster_id = cluster_obj.id
        ticket_param = {
            "bk_biz_id": bk_biz_id,
            "ticket_type": TicketType.REDIS_KEYS_DELETE,
            "creator": request.user.username,
            "helpers": [],
            "remark": "mcp redis delete key ticket",
            "details": {
                "delete_type": "regex",
                "rules": [
                    {
                        "domain": cluster_domain,
                        "delete_rate": delete_rate,
                        "cluster_id": cluster_id,
                        "black_regex": black_regex,
                        "white_regex": white_regex,
                    }
                ],
            },
        }

        tk = Ticket.create_ticket(**ticket_param)
        return Response({"bill_id": tk.pk, "bill_url": tk.url})

    @mcp_tools_api_decorator(
        description=str(_("""Redis集群标准化""")),
        request_slz=SubmitBillRedisBaseInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.REDIS_BILL],
        name_prefix="redis_bill",
    )
    def submit_bill_reinstall_dbmon(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain")

        cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
        cluster_id = cluster_obj.id
        ticket_param = {
            "bk_biz_id": bk_biz_id,
            "ticket_type": TicketType.REDIS_CLUSTER_REINSTALL_DBMON,
            "creator": request.user.username,
            "helpers": [],
            "remark": "mcp redis reinstall dbmon ticket",
            "details": {
                "is_stop": False,
                "bk_cloud_id": cluster_obj.bk_cloud_id,
                "restart_exporter": True,
                "cluster_ids": [cluster_id],
            },
        }

        tk = Ticket.create_ticket(**ticket_param)
        return Response({"bill_id": tk.pk, "bill_url": tk.url})
