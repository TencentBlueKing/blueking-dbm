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

from django.utils.translation import ugettext_lazy as _
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.components.hadb.client import HADBApi
from backend.db_meta.models import Cluster
from backend.db_proxy.constants import SWAGGER_TAG
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket

from ..views import BaseProxyPassViewSet
from .serializers import DumperMigrateProxyPassSerializer


class DumperProxyPassViewSet(BaseProxyPassViewSet):
    """
    Dumper服务接口的透传视图
    """

    @common_swagger_auto_schema(
        operation_summary=_("[dumper]迁移"),
        request_body=DumperMigrateProxyPassSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"], detail=False, serializer_class=DumperMigrateProxyPassSerializer, url_path="dumper/switch"
    )
    def dumper_switch(self, request):
        data = self.params_validate(self.get_serializer_class())
        # 获取集群ID
        cluster_domains = [info["cluster_domain"] for info in data["infos"]]
        domain__cluster = {
            cluster.immute_domain: cluster for cluster in Cluster.objects.filter(immute_domain__in=cluster_domains)
        }
        for info in data["infos"]:
            info["cluster_id"] = domain__cluster[info["cluster_domain"]]
        # 创建dumper迁移单据
        Ticket.create_ticket(
            ticket_type=TicketType.TBINLOGDUMPER_SWITCH_NODES,
            creator=request.user.username,
            bk_biz_id=data.pop("bk_biz_id"),
            remark=_("透传接口dumper迁移创建的单据"),
            details=data,
        )
