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
import logging
from typing import List

from django.utils.translation import ugettext as _

from backend.db_dirty.constants import MachineEventType, PoolType
from backend.db_dirty.exceptions import PoolTransferException
from backend.db_dirty.models import DirtyMachine, MachineEvent
from backend.flow.consts import FAILED_STATES
from backend.flow.utils.cc_manage import CcManage
from backend.ticket.builders import BuilderFactory
from backend.ticket.builders.common.base import fetch_apply_hosts
from backend.ticket.models import Flow, Ticket

logger = logging.getLogger("root")


class DBDirtyMachineHandler(object):
    """
    污点池处理接口的逻辑处理
    """

    @classmethod
    def transfer_hosts_to_pool(cls, operator: str, bk_host_ids: List[int], source: PoolType, target: PoolType):
        """
        将主机转移待回收/故障池模块
        @param bk_host_ids: 主机列表
        @param operator: 操作者
        @param source: 主机来源
        @param target: 主机去向
        """
        # 将主机按照业务分组
        recycle_hosts = DirtyMachine.objects.filter(bk_host_id__in=bk_host_ids)
        biz_grouped_recycle_hosts = itertools.groupby(recycle_hosts, key=lambda x: x.bk_biz_id)

        for bk_biz_id, hosts in biz_grouped_recycle_hosts:
            hosts = [{"bk_host_id": host.bk_host_id} for host in hosts]
            # 故障池 ---> 待回收
            if source == PoolType.Recycle and target == PoolType.Recycled:
                CcManage(bk_biz_id, "").recycle_host([h["bk_host_id"] for h in hosts])
                MachineEvent.host_event_trigger(bk_biz_id, hosts, event=MachineEventType.Recycled, operator=operator)
            # 待回收 ---> 回收
            elif source == PoolType.Fault and target == PoolType.Recycle:
                MachineEvent.host_event_trigger(bk_biz_id, hosts, event=MachineEventType.ToRecycle, operator=operator)
            else:
                raise PoolTransferException(_("{}--->{}转移不合法").format(source, target))

    @classmethod
    def handle_dirty_machine(cls, ticket_id, root_id, origin_tree_status, target_tree_status):
        """
        处理执行失败/重试成功涉及的污点池机器
        @param ticket_id: 单据ID
        @param root_id: 流程ID
        @param origin_tree_status: 流程源状态
        @param target_tree_status: 流程目标状态
        """
        if (origin_tree_status not in FAILED_STATES) and (target_tree_status not in FAILED_STATES):
            return

        try:
            ticket = Ticket.objects.get(id=ticket_id)
            # 如果不是部署类单据，则无需处理
            if ticket.ticket_type not in BuilderFactory.apply_ticket_type:
                return
        except (Ticket.DoesNotExist, Flow.DoesNotExist, ValueError):
            return

        # 如果初始状态是失败，则证明是重试，将机器从污点池中移除
        hosts = fetch_apply_hosts(ticket.details)
        bk_host_ids = [h["bk_host_id"] for h in hosts]

        if not bk_host_ids:
            return

        # 如果是原状态失败，则证明是重试，这里只用删除记录
        if origin_tree_status in FAILED_STATES:
            logger.info(_("【污点池】主机列表:{} 将从污点池挪出").format(bk_host_ids))
            DirtyMachine.objects.filter(bk_host_id__in=bk_host_ids).delete()

        # 如果是目标状态失败，则证明是执行失败，将机器加入污点池
        if target_tree_status in FAILED_STATES:
            logger.info(_("【污点池】主机列表:{} 移入污点池").format(bk_host_ids))
            hosts = fetch_apply_hosts(ticket.details)
            MachineEvent.host_event_trigger(ticket.bk_biz_id, hosts, MachineEventType.ToDirty, ticket.creator, ticket)
