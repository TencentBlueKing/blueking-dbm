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
from collections import defaultdict
from typing import Any, Dict, List

from backend.components import CCApi
from backend.configuration.constants import MANAGE_TOPO
from backend.configuration.models import SystemSettings
from backend.db_dirty.models import DirtyMachine
from backend.db_meta.models import Machine
from backend.flow.utils.cc_manage import CcManage
from backend.ticket.models import Flow, Ticket


class DBDirtyMachineHandler(object):
    """
    污点池处理接口的逻辑处理
    """

    @classmethod
    def transfer_dirty_machines(cls, bk_host_ids: List[int]):
        """
        将污点主机转移待回收模块
        @param bk_host_ids: 主机列表
        """
        dirty_machines = DirtyMachine.objects.filter(bk_host_id__in=bk_host_ids)
        bk_biz_id__host_ids = defaultdict(list)
        for machine in dirty_machines:
            bk_biz_id__host_ids[machine.bk_biz_id].append(machine.bk_host_id)

        for bk_biz_id, bk_host_ids in bk_biz_id__host_ids.items():
            CCApi.transfer_host_to_recyclemodule({"bk_biz_id": bk_biz_id, "bk_host_id": bk_host_ids})

        dirty_machines.delete()

    @classmethod
    def insert_dirty_machines(cls, bk_biz_id: int, bk_host_ids: List[Dict[str, Any]], ticket: Ticket, flow: Flow):
        """
        将机器导入到污点池中
        @param bk_biz_id: 业务ID
        @param bk_host_ids: 主机列表
        @param ticket: 关联的单据
        @param flow: 关联的flow任务
        """
        # 排除已经录入到Machine表的机器（因为是成功消费不算污点机器）
        db_machines = list(Machine.objects.filter(bk_host_id__in=bk_host_ids).values_list("bk_host_id", flat=True))
        dirty_host_ids = list(set(bk_host_ids) - set(db_machines))

        # 查询污点机器信息
        host_property_filter = {
            "condition": "AND",
            "rules": [{"field": "bk_host_id", "operator": "in", "value": dirty_host_ids}],
        }
        dirty_host_infos = CCApi.list_biz_hosts(
            {
                "bk_biz_id": bk_biz_id,
                # 默认一次性录入的机器不会超过500
                "page": {"start": 0, "limit": 500, "sort": "bk_host_id"},
                "host_property_filter": host_property_filter,
                "fields": ["bk_host_id", "bk_cloud_id", "bk_host_innerip"],
            }
        )["info"]

        # 将污点机器信息转移至污点池模块
        dirty_module = SystemSettings.get_setting_value(key=MANAGE_TOPO)["dirty_module_id"]
        CcManage.transfer_host_module(bk_host_ids=dirty_host_ids, target_module_ids=[dirty_module])

        # 录入污点池表中
        DirtyMachine.objects.bulk_create(
            [
                DirtyMachine(
                    ticket=ticket,
                    flow=flow,
                    ip=host["bk_host_innerip"],
                    bk_biz_id=bk_biz_id,
                    bk_host_id=host["bk_host_id"],
                    bk_cloud_id=host["bk_cloud_id"],
                )
                for host in dirty_host_infos
            ]
        )

    @classmethod
    def remove_dirty_machines(cls, bk_host_ids: List[Dict[str, Any]]):
        """
        将机器从污点池挪走，一般是重试后会调用此函数。
        这里只用删除记录，无需做其他挪模块的操作，原因如下：
        1. 如果重试依然失败，则机器会重新回归污点池，模块不变
        2. 如果重试成功，则机器已经由flow挪到了对应的DB模块
        3. 如果手动处理，则机器会被挪到待回收模块
        @param bk_host_ids: 主机列表
        """
        DirtyMachine.objects.filter(bk_host_id__in=bk_host_ids).delete()
