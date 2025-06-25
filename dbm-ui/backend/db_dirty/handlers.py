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
from backend.components import CCApi
from backend.components.dbresource.client import DBResourceApi
from backend.components.hcm.client import HCMApi
from backend.db_dirty.constants import MachineEventType, PoolType
from backend.db_dirty.exceptions import PoolTransferException
from backend.db_dirty.models import DirtyMachine, MachineEvent
from backend.db_meta.models import Machine
from backend.env import HCM_APIGW_DOMAIN

logger = logging.getLogger("root")


class DBDirtyMachineHandler(object):
    """
    污点池处理接口的逻辑处理
    """

    @classmethod
    def transfer_hosts_to_pool(
        cls,
        operator: str,
        bk_host_ids: List[int],
        source: PoolType,
        target: PoolType,
        remark: str = "",
        hcm_recycle: bool = False,
    ):
        """
        将主机转移待回收/故障池模块
        @param bk_host_ids: 主机列表
        @param operator: 操作者
        @param source: 主机来源
        @param target: 主机去向
        @param remark: 备注
        @param hcm_recycle: 是否在hcm创建回收单据，仅针对主机回收场景
        """
        bk_biz_id = env.DBA_APP_BK_BIZ_ID
        recycle_hosts = DirtyMachine.objects.filter(bk_host_id__in=bk_host_ids)
        hosts = [{"bk_host_id": host.bk_host_id} for host in recycle_hosts]
        recycle_id = None

        # 待回收池 ---> CC待回收
        if source == PoolType.Recycle and target == PoolType.Recycled:
            message = _("主机删除成功！")
            CCApi.transfer_host_to_recyclemodule({"bk_biz_id": bk_biz_id, "bk_host_id": bk_host_ids}, use_admin=True)
            # 如果配置了hcm，并且确认在hcm回收，则自动创建回收单据
            if HCM_APIGW_DOMAIN and hcm_recycle:
                recycle_id = HCMApi.create_recycle(bk_host_ids)
                remark = _("已自动在「海垒」创建回收单据(单号：{})").format(recycle_id)
                message += remark
            MachineEvent.host_event_trigger(bk_biz_id, hosts, MachineEventType.Recycled, operator, remark=remark)
        # 故障池 ---> 待回收池
        elif source == PoolType.Fault and target == PoolType.Recycle:
            message = _("主机转移成功！")
            MachineEvent.host_event_trigger(bk_biz_id, hosts, MachineEventType.ToRecycle, operator, remark=remark)
        # 资源池 ---> 故障池：这个是用于资源池自身巡检发现故障主机调用转移接口
        elif source == PoolType.Resource and target == PoolType.Fault:
            message = _("主机转移成功！")
            MachineEvent.host_event_trigger(bk_biz_id, hosts, MachineEventType.ToFault, operator, remark=remark)
        else:
            raise PoolTransferException(_("{}--->{}转移不合法").format(source, target))

        return {"message": message, "hcm_recycle_id": recycle_id}

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
