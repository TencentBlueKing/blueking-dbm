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
import math
import time
from typing import List

from django.utils.translation import ugettext as _

from backend import env
from backend.components.dbresource.client import DBResourceApi
from backend.db_dirty.constants import MachineEventType, PoolType
from backend.db_dirty.exceptions import PoolTransferException
from backend.db_dirty.models import DirtyMachine, MachineEvent
from backend.db_meta.models import Machine
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
        hosts = [{"bk_host_id": host.bk_host_id} for host in recycle_hosts]
        bk_biz_id = env.DBA_APP_BK_BIZ_ID
        # 待回收 ---> 回收
        if source == PoolType.Recycle and target == PoolType.Recycled:
            MachineEvent.host_event_trigger(bk_biz_id, hosts, MachineEventType.Recycled, operator, remark=remark)
            CcManage(bk_biz_id, "").recycle_host(bk_host_ids)
        # 故障池 ---> 待回收
        elif source == PoolType.Fault and target == PoolType.Recycle:
            MachineEvent.host_event_trigger(bk_biz_id, hosts, MachineEventType.ToRecycle, operator, remark=remark)
        else:
            raise PoolTransferException(_("{}--->{}转移不合法").format(source, target))

    @classmethod
    def migrate_machine_to_host_pool(cls):
        """
        迁移现网的machine表和资源池。 TODO: 迁移完毕后改代码可删除
        """
        size = 200

        machine_count = Machine.objects.count()
        batch = math.ceil(machine_count / size)
        for page in range(0, batch):
            hosts = Machine.objects.all()[page * size : (page + 1) * size].values("bk_host_id")
            # dbm主机，先转移到资源池，在更新pool为空字段，表示已占用
            DirtyMachine.hosts_pool_transfer(hosts=list(hosts), pool=PoolType.Resource, operator="admin")
            DirtyMachine.hosts_pool_transfer(hosts=list(hosts), pool="", operator="admin")
            print("machine batch %s 已完成...", page)
            time.sleep(0.01)

        resource_count = DBResourceApi.resource_list(params={"limit": 1, "offset": 0})["count"]
        batch = math.ceil(resource_count / size)
        exist_hosts_ids = list(Machine.objects.all().values_list("bk_host_id", flat=True))
        for page in range(0, batch):
            hosts = DBResourceApi.resource_list(params={"limit": size, "offset": page * size})["details"]
            # 排除已经存在元数据的主机
            new_resource_hosts = [host for host in hosts if host["bk_host_id"] not in exist_hosts_ids]
            # 资源池主机直接导入到资源池
            DirtyMachine.hosts_pool_transfer(hosts=new_resource_hosts, pool=PoolType.Resource, operator="admin")
            print("resource batch %s 已完成...", page)
            time.sleep(0.01)
