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

from backend import env
from backend.db_dirty.constants import MachineEventType, PoolType
from backend.db_dirty.exceptions import PoolTransferException
from backend.db_dirty.models import DirtyMachine, MachineEvent
from backend.flow.utils.cc_manage import CcManage

logger = logging.getLogger("root")


class DBDirtyMachineHandler(object):
    """
    污点池处理接口的逻辑处理
    """

    @classmethod
    def transfer_hosts_to_pool(
        cls, operator: str, bk_host_ids: List[int], source: PoolType, target: PoolType, remark: str = ""
    ):
        """
        将主机转移待回收/故障池模块
        @param bk_host_ids: 主机列表
        @param operator: 操作者
        @param source: 主机来源
        @param target: 主机去向
        @param remark: 备注
        """
        # 将主机按照业务分组
        recycle_hosts = DirtyMachine.objects.filter(bk_host_id__in=bk_host_ids)
        biz_grouped_recycle_hosts = itertools.groupby(recycle_hosts, key=lambda x: x.bk_biz_id)

        for bk_biz_id, hosts in biz_grouped_recycle_hosts:
            hosts = [{"bk_host_id": host.bk_host_id} for host in hosts]
            # 待回收 ---> 回收
            if source == PoolType.Recycle and target == PoolType.Recycled:
                MachineEvent.host_event_trigger(bk_biz_id, hosts, MachineEventType.Recycled, operator, remark=remark)
                CcManage(env.DBA_APP_BK_BIZ_ID, "").recycle_host(bk_host_ids)
            # 故障池 ---> 待回收
            elif source == PoolType.Fault and target == PoolType.Recycle:
                MachineEvent.host_event_trigger(bk_biz_id, hosts, MachineEventType.ToRecycle, operator, remark=remark)
            else:
                raise PoolTransferException(_("{}--->{}转移不合法").format(source, target))
