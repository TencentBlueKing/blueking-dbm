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
from collections import defaultdict
from typing import Any, Dict, List

from django.utils.translation import ugettext as _

from backend import env
from backend.components import CCApi
from backend.components.dbresource.client import DBResourceApi
from backend.configuration.constants import SystemSettingsEnum
from backend.configuration.models import SystemSettings
from backend.db_dirty.models import DirtyMachine
from backend.db_meta.models import AppCache
from backend.db_services.ipchooser.constants import IDLE_HOST_MODULE
from backend.db_services.ipchooser.handlers.topo_handler import TopoHandler
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.flow.consts import FAILED_STATES
from backend.flow.utils.cc_manage import CcManage
from backend.ticket.builders import BuilderFactory
from backend.ticket.models import Flow, Ticket
from backend.utils.basic import get_target_items_from_details
from backend.utils.batch_request import request_multi_thread

logger = logging.getLogger("root")


class DBDirtyMachineHandler(object):
    """
    污点池处理接口的逻辑处理
    """

    @classmethod
    def transfer_dirty_machines(cls, bk_host_ids: List[int]):
        """
        将污点主机转移待回收模块，并从资源池移除
        @param bk_host_ids: 主机列表
        """
        # 将主机移动到待回收模块
        dirty_machines = DirtyMachine.objects.filter(bk_host_id__in=bk_host_ids)
        bk_biz_id__host_ids = defaultdict(list)
        for machine in dirty_machines:
            bk_biz_id__host_ids[machine.bk_biz_id].append(machine.bk_host_id)

        for bk_biz_id, bk_host_ids in bk_biz_id__host_ids.items():
            CcManage(int(bk_biz_id), "").recycle_host(bk_host_ids)

        # 删除污点池记录，并从资源池移除(忽略删除错误，因为机器可能不来自资源池)
        dirty_machines.delete()
        DBResourceApi.resource_delete(params={"bk_host_ids": bk_host_ids}, raise_exception=False)

    @classmethod
    def query_dirty_machine_records(cls, bk_host_ids: List[int]):
        """
        查询污点池主机信息
        @param bk_host_ids: 主机列表
        """

        def get_module_data(data):
            params, res = data
            params = params["params"]
            return [{"bk_biz_id": params["bk_biz_id"], **d} for d in res]

        if not bk_host_ids:
            return []

        # 如果传入的列表已经是DirtyMachine，则直接用
        if not isinstance(bk_host_ids[0], DirtyMachine):
            dirty_machines = DirtyMachine.objects.filter(bk_host_id__in=bk_host_ids)
        else:
            dirty_machines = bk_host_ids
            bk_host_ids = [dirty.bk_host_id for dirty in dirty_machines]

        # 缓存云区域和业务信息
        bk_biz_ids = [dirty_machine.bk_biz_id for dirty_machine in dirty_machines]
        for_biz_infos = AppCache.batch_get_app_attr(bk_biz_ids=bk_biz_ids, attr_name="bk_biz_name")
        cloud_info = ResourceQueryHelper.search_cc_cloud(get_cache=True)

        # 查询污点主机当前所处的模块
        host_topo_infos = CCApi.find_host_biz_relations(params={"bk_host_id": bk_host_ids})
        host__topo_info_map: Dict[int, List] = defaultdict(list)
        biz__modules_map: Dict[int, List] = defaultdict(list)
        for topo in host_topo_infos:
            host__topo_info_map[topo["bk_host_id"]].append(topo)
            biz__modules_map[topo["bk_biz_id"]].append(topo["bk_module_id"])
        # 批量获取业务下模块信息
        module_infos = request_multi_thread(
            func=CCApi.find_module_batch,
            params_list=[
                {
                    "params": {"bk_biz_id": biz, "bk_ids": modules, "fields": ["bk_module_id", "bk_module_name"]},
                    "use_admin": True,
                }
                for biz, modules in biz__modules_map.items()
            ],
            get_data=get_module_data,
            in_order=True,
        )
        module_infos = list(itertools.chain(*module_infos))
        biz__module__module_name: Dict[int, Dict[int, str]] = defaultdict(dict)
        for info in module_infos:
            biz__module__module_name[info["bk_biz_id"]][info["bk_module_id"]] = info["bk_module_name"]

        # 获取污点池模块
        system_manage_topo = SystemSettings.get_setting_value(key=SystemSettingsEnum.MANAGE_TOPO.value)
        dirty_module = system_manage_topo["dirty_module_id"]

        # 获取污点池列表信息
        dirty_machine_list: List[Dict] = []
        for dirty in dirty_machines:
            # 填充污点池主机基础信息
            dirty_machine_info = {
                "ip": dirty.ip,
                "bk_host_id": dirty.bk_host_id,
                "bk_cloud_name": cloud_info[str(dirty.bk_cloud_id)]["bk_cloud_name"],
                "bk_cloud_id": dirty.bk_cloud_id,
                "bk_biz_name": for_biz_infos[int(dirty.bk_biz_id)],
                "bk_biz_id": dirty.bk_biz_id,
                "ticket_type": dirty.ticket.ticket_type,
                "ticket_id": dirty.ticket.id,
                "ticket_type_display": dirty.ticket.get_ticket_type_display(),
                "task_id": dirty.flow.flow_obj_id,
                "operator": dirty.ticket.creator,
                "is_dirty": True,
            }

            # 如果主机已经不存在于cc，则仅能删除记录
            if dirty.bk_host_id not in host__topo_info_map:
                dirty_machine_info.update(is_dirty=False)
                dirty_machine_list.append(dirty_machine_info)
                continue

            # 补充主机所在的模块信息
            host_in_module = [
                {
                    "bk_module_id": h["bk_module_id"],
                    "bk_module_name": biz__module__module_name[h["bk_biz_id"]].get(h["bk_module_id"], ""),
                }
                for h in host__topo_info_map[dirty.bk_host_id]
            ]
            dirty_machine_info.update(bk_module_infos=host_in_module)

            # 如果主机 不处于/不仅仅处于【污点池】中，则不允许移入待回收
            host = host__topo_info_map[dirty.bk_host_id][0]
            if len(host__topo_info_map[dirty.bk_host_id]) > 1:
                dirty_machine_info.update(is_dirty=False)
            elif host["bk_biz_id"] != env.DBA_APP_BK_BIZ_ID or host["bk_module_id"] != dirty_module:
                dirty_machine_info.update(is_dirty=False)

            dirty_machine_list.append(dirty_machine_info)

        dirty_machine_list.sort(key=lambda x: x["ticket_id"], reverse=True)
        return dirty_machine_list

    @classmethod
    def insert_dirty_machines(cls, bk_biz_id: int, bk_host_ids: List[Dict[str, Any]], ticket: Ticket, flow: Flow):
        """
        将机器导入到污点池中
        @param bk_biz_id: 业务ID
        @param bk_host_ids: 主机列表
        @param ticket: 关联的单据
        @param flow: 关联的flow任务
        """
        # 查询污点机器信息
        host_property_filter = {
            "condition": "AND",
            "rules": [{"field": "bk_host_id", "operator": "in", "value": bk_host_ids}],
        }
        dirty_host_infos = CCApi.list_hosts_without_biz(
            {
                # 默认一次性录入的机器不会超过500
                "page": {"start": 0, "limit": 500, "sort": "bk_host_id"},
                "host_property_filter": host_property_filter,
                "fields": ["bk_host_id", "bk_cloud_id", "bk_host_innerip"],
            },
            use_admin=True,
        )["info"]

        # 获取业务空闲机模块，资源池模块和污点池模块
        idle_module = CcManage(bk_biz_id, "").get_biz_internal_module(bk_biz_id)[IDLE_HOST_MODULE]["bk_module_id"]
        system_manage_topo = SystemSettings.get_setting_value(key=SystemSettingsEnum.MANAGE_TOPO.value)
        resource_module, dirty_module = system_manage_topo["resource_module_id"], system_manage_topo["dirty_module_id"]
        # 获取主机的拓扑信息(注：这里不能带上业务信息，因为主机可能转移业务)
        host_topo_infos = TopoHandler.query_host_set_module(bk_host_ids=bk_host_ids)["hosts_topo_info"]
        # 将污点机器信息转移至DBA污点池模(如果污点机器不在空闲机/资源池，则放弃转移，认为已到正确拓扑)
        transfer_host_ids = [
            info["bk_host_id"]
            for info in host_topo_infos
            if not set(info["bk_module_ids"]) - {resource_module, idle_module}
        ]
        if transfer_host_ids:
            update_host_properties = {"dbm_meta": [], "need_monitor": False, "update_operator": False}
            CcManage(bk_biz_id=env.DBA_APP_BK_BIZ_ID, cluster_type="").transfer_host_module(
                transfer_host_ids, target_module_ids=[dirty_module], update_host_properties=update_host_properties
            )

        # 录入污点池表中
        exist_dirty_machine_ids = list(
            DirtyMachine.objects.filter(bk_host_id__in=bk_host_ids).values_list("bk_host_id", flat=True)
        )
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
                if host["bk_host_id"] not in exist_dirty_machine_ids
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

    @classmethod
    def handle_dirty_machine(cls, ticket_id, root_id, origin_tree_status, target_tree_status):
        """处理执行失败/重试成功涉及的污点池机器"""
        if (origin_tree_status not in FAILED_STATES) and (target_tree_status not in FAILED_STATES):
            return

        try:
            ticket = Ticket.objects.get(id=ticket_id)
            flow = Flow.objects.get(flow_obj_id=root_id)
            # 如果不是部署类单据，则无需处理
            if ticket.ticket_type not in BuilderFactory.apply_ticket_type:
                return
        except (Ticket.DoesNotExist, Flow.DoesNotExist, ValueError):
            return

        # 如果初始状态是失败，则证明是重试，将机器从污点池中移除
        bk_host_ids = get_target_items_from_details(
            obj=ticket.details, match_keys=["host_id", "bk_host_id", "bk_host_ids"]
        )

        if not bk_host_ids:
            return

        if origin_tree_status in FAILED_STATES:
            logger.info(_("【污点池】主机列表:{} 将从污点池挪出").format(bk_host_ids))
            DBDirtyMachineHandler.remove_dirty_machines(bk_host_ids)

        # 如果是目标状态失败，则证明是执行失败，将机器加入污点池
        if target_tree_status in FAILED_STATES:
            logger.info(_("【污点池】单据-{}：任务-{}执行失败，主机列表:{}挪到污点池").format(ticket_id, root_id, bk_host_ids))
            DBDirtyMachineHandler.insert_dirty_machines(
                bk_biz_id=ticket.bk_biz_id, bk_host_ids=bk_host_ids, ticket=ticket, flow=flow
            )
