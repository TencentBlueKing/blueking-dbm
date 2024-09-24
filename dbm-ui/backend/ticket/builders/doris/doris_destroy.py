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
import logging

from django.utils.translation import ugettext_lazy as _

from backend.db_meta.enums import ClusterPhase
from backend.flow.engine.controller.doris import DorisController
from backend.ticket import builders
from backend.ticket.builders.common.base import HostRecycleSerializer
from backend.ticket.builders.common.bigdata import BaseDorisTicketFlowBuilder, BigDataTakeDownDetailSerializer
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


class DorisDestroyDetailSerializer(BigDataTakeDownDetailSerializer):
    ip_recycle = HostRecycleSerializer(help_text=_("主机回收信息"), default=HostRecycleSerializer.DEFAULT)


class DorisDestroyFlowParamBuilder(builders.FlowParamBuilder):
    controller = DorisController.doris_destroy_scene


@builders.BuilderFactory.register(TicketType.DORIS_DESTROY, phase=ClusterPhase.DESTROY)
class DorisDestroyFlowBuilder(BaseDorisTicketFlowBuilder):
    serializer = DorisDestroyDetailSerializer
    inner_flow_builder = DorisDestroyFlowParamBuilder
    inner_flow_name = _("DORIS集群删除")
    need_patch_recycle_cluster_details = True
