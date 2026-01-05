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
from backend.dbm_aiagent.mcp_tools.constants import DBMAMcpTools, DBMMCPTags
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.redis.serializers.redis_bill import (
    SubmitBillOutputSerializer,
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
"""


class RedisBillMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(_("""Redis集群备份单据""")),
        request_slz=SubmitBillRedisFullBackupInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMAMcpTools.REDIS_BILL],
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
            "creator": "admin",
            "helpers": [],
            "remark": "mcp backup ticket",
            "details": {
                "rules": [
                    {"backup_type": backup_type, "cluster_id": cluster_id, "domain": cluster_domain, "target": target}
                ]
            },
        }

        tk = Ticket.create_ticket(**ticket_param)
        return Response({"bill_id": tk.pk})

    @mcp_tools_api_decorator(
        description=str(_("""减少Redis集群proxy数量单据, 缩容后的proxy数量不允许少于2""")),
        request_slz=SubmitBillRedisProxyReduceOrIncreaseInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMAMcpTools.REDIS_BILL],
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
            "creator": "admin",
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
        return Response({"bill_id": tk.pk})

    @mcp_tools_api_decorator(
        description=str(_("""指定IP 下架redis集群的proxy""")),
        request_slz=SubmitBillRedisProxyReduceByIpInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMAMcpTools.REDIS_BILL],
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
            "creator": "admin",
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
        return Response({"bill_id": tk.pk})

    @mcp_tools_api_decorator(
        description=str(_("""增加Redis集群proxy数量单据""")),
        request_slz=SubmitBillRedisProxyReduceOrIncreaseInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMAMcpTools.REDIS_BILL],
        name_prefix="redis_bill",
    )
    def submit_bill_redis_proxy_increase(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain")
        proxy_change_count = self.get_param("proxy_change_count")

        cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
        cluster_id = cluster_obj.id
        cluster_proxy_count = cluster_obj.proxyinstance_set.count()
        count = cluster_proxy_count + proxy_change_count
        # 获取spec_id
        spec_id = cluster_obj.proxyinstance_set.first().machine.spec_id
        ticket_param = {
            "bk_biz_id": bk_biz_id,
            "creator": "admin",
            "helpers": [],
            "remark": "mcp proxy increase ticket",
            "ticket_type": TicketType.REDIS_PROXY_SCALE_UP,
            "details": {
                "infos": [
                    {
                        "bk_cloud_id": cluster_obj.bk_cloud_id,
                        "cluster_id": cluster_id,
                        "resource_spec": {"proxy": {"count": count, "spec_id": spec_id}},
                    }
                ],
                "ip_source": IpSource.RESOURCE_POOL.value,
                "shrink_type": "QUANTITY",
            },
        }

        tk = Ticket.create_ticket(**ticket_param)
        return Response({"bill_id": tk.pk})
