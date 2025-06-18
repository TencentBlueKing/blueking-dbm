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

from backend.flow.engine.controller.es_name_service import EsNameServiceController
from backend.ticket import builders
from backend.ticket.builders.common.bigdata import BaseEsTicketFlowBuilder, BigDataSingleClusterOpsDetailsSerializer
from backend.ticket.constants import TicketType


class EsDnsBindCLBDetailSerializer(BigDataSingleClusterOpsDetailsSerializer):
    pass


class EsDnsBindCLBFlowParamBuilder(builders.FlowParamBuilder):
    controller = EsNameServiceController.immute_domain_bind_clb_ip

    def format_ticket_data(self):
        super().format_ticket_data()


@builders.BuilderFactory.register(TicketType.ES_DNS_BIND_CLB)
class EsDnsBindCLBFlowBuilder(BaseEsTicketFlowBuilder):
    serializer = EsDnsBindCLBDetailSerializer
    inner_flow_builder = EsDnsBindCLBFlowParamBuilder
    inner_flow_name = _("主域名绑定CLB")
    default_need_itsm = False
