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
import itertools
from collections import defaultdict
from typing import Dict, List

from django.utils.translation import ugettext as _

from backend.bk_web import viewsets
from backend.bk_web.pagination import AuditedLimitOffsetPagination
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_meta.enums import InstanceInnerRole
from backend.db_meta.enums.extra_process_type import ExtraProcessType
from backend.db_meta.models import Cluster
from backend.db_meta.models.extra_process import ExtraProcessInstance
from backend.db_services.mysql.dumper.filters import DumperInstanceListFilter
from backend.db_services.mysql.dumper.handlers import DumperHandler
from backend.db_services.mysql.dumper.serializers import DumperInstanceConfigSerializer
from backend.ticket.constants import TicketStatus, TicketType
from backend.ticket.models import Ticket

SWAGGER_TAG = "dumper"


class DumperInstanceViewSet(viewsets.AuditedModelViewSet):
    pagination_class = AuditedLimitOffsetPagination
    queryset = ExtraProcessInstance.objects.filter(proc_type=ExtraProcessType.TBINLOGDUMPER)
    serializer_class = DumperInstanceConfigSerializer
    filter_class = DumperInstanceListFilter

    def get_queryset(self):
        return self.queryset.filter(bk_biz_id=self.kwargs["bk_biz_id"])

    @common_swagger_auto_schema(
        operation_summary=_("查询数据订阅实例列表"),
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        dumper_results = resp.data["results"]
        DumperHandler.patch_dumper_list_info(dumper_results, bk_biz_id=kwargs["bk_biz_id"], need_status=True)
        return resp
