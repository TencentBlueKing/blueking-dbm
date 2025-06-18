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


class EsDeletePolarisDetailSerializer(BigDataSingleClusterOpsDetailsSerializer):
    pass


class EsDeletePolarisFlowParamBuilder(builders.FlowParamBuilder):
    controller = EsNameServiceController.polaris_delete

    def format_ticket_data(self):
        super().format_ticket_data()


@builders.BuilderFactory.register(TicketType.ES_DELETE_POLARIS)
class EsDeletePolarisFlowBuilder(BaseEsTicketFlowBuilder):
    serializer = EsDeletePolarisDetailSerializer
    inner_flow_builder = EsDeletePolarisFlowParamBuilder
    inner_flow_name = _("删除北极星")
    default_need_itsm = False
