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
from collections import defaultdict
from typing import List

from django.utils.translation import gettext as _

from backend import env
from backend.components import CCApi
from backend.db_meta.models.machine import DeviceClass
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.install_plugins import install_nodeman_plugins
from backend.flow.plugins.components.collections.common.sa_idle_check import CheckMachineIdleComponent
from backend.flow.plugins.components.collections.common.sa_init import SaInitComponent
from backend.flow.plugins.components.collections.common.write_bandwidth_file_script import (
    WriteBandwidthFileScriptComponent,
)

"""
定义大数据组件实施流程上可能会用到的子流程，以减少代码的重复率
"""

logger = logging.getLogger("flow")


def make_idle_check_act(
    ips: list,
    bk_biz_id: int,
):
    """
    构造空闲检查子流程
    :param ips: ip数组
    :param bk_biz_id: 机器所属业务ID
    :return:
    """
    if env.SA_CHECK_TEMPLATE_ID and ips:
        idle_check_act = {
            "act_name": _("执行sa空闲检查"),
            "act_component_code": CheckMachineIdleComponent.code,
            "kwargs": {"ips": ips, "bk_biz_id": bk_biz_id},
        }
        return idle_check_act

    return None


def make_sa_init_act(ips: list, bk_biz_id: int, bk_host_ids: List[int] = None):
    """
    构造 机器初始化 子流程
    :param ips: ip数组
    :param bk_biz_id: 机器所属业务ID
    :param bk_host_ids: 机器ID列表, 当前非必传
    :return:
    """
    # 执行sa初始化
    if env.SA_INIT_TEMPLATE_ID and ips:
        sa_init_act = {
            "act_name": _("执行sa初始化"),
            "act_component_code": SaInitComponent.code,
            "kwargs": {"ips": ips, "bk_biz_id": bk_biz_id},
        }
        return sa_init_act

    return None


def make_bandwidth_init_sub_flow(root_id: str, uid: str, bk_cloud_id: int, machine_list: list):
    """
    构造 写入带宽文件 子流程
    :param root_id:  根流程id
    :param uid: 单据id
    :param bk_cloud_id: 云区域ID
    :param machine_list: ip、机型的列表
    :return:
    """
    if machine_list:
        machine_dic = defaultdict(list)
        for machine in machine_list:
            machine_dic[machine["bk_svr_device_cls_name"]].append(machine["bk_host_innerip"])

        init_bandwidth_pipeline = SubBuilder(root_id=root_id, data={"uid": uid})
        acts_list = []
        for machine_type, ips in machine_dic.items():
            bandwidth = 2**31 - 1
            device = DeviceClass.objects.filter(device_type=machine_type)
            if device:
                bandwidth = device[0].bandwidth
            write_bandwidth_file_act = {
                "act_name": _("写入 [{}] 带宽文件").format(machine_type),
                "act_component_code": WriteBandwidthFileScriptComponent.code,
                "kwargs": {"ips": ips, "bk_cloud_id": bk_cloud_id, "bandwidth": bandwidth},
            }
            acts_list.append(write_bandwidth_file_act)
        init_bandwidth_pipeline.add_parallel_acts(acts_list=acts_list)
        return init_bandwidth_pipeline.build_sub_process(sub_name=_("初始化节点的带宽信息"))
    return None


def new_machine_common_sub_flow(
    uid: str,
    root_id: str,
    bk_cloud_id: int,
    new_ips: list,
):
    if not new_ips:
        raise Exception(_("构建init_machine_sub子流程失败，联系系统管理员, new_ips is null"))

    act_exist = False

    sub_pipeline = SubBuilder(root_id=root_id, data={"uid": uid})
    bk_host_ids = list_bk_host_ids(ips=new_ips, bk_cloud_id=bk_cloud_id)
    if not bk_host_ids:
        logger.error("ccapi can't find any bk host ids.")
        return None
    machine_biz_id = get_bk_biz_id(bk_host_ids[0])
    idle_check_act = make_idle_check_act(ips=new_ips, bk_biz_id=machine_biz_id)
    if idle_check_act:
        act_exist = True
        sub_pipeline.add_parallel_acts([idle_check_act])
    sa_init_act = make_sa_init_act(ips=new_ips, bk_biz_id=machine_biz_id)
    if sa_init_act:
        act_exist = True
        sub_pipeline.add_parallel_acts([sa_init_act])
    if bk_host_ids:
        act_exist = True
        sub_pipeline.add_sub_pipeline(install_nodeman_plugins(root_id, uid, bk_host_ids))
    machine_bandwidth = list_machine_bandwidth(new_ips, bk_cloud_id)
    if machine_bandwidth:
        act_exist = True
        sub_pipeline.add_sub_pipeline(
            make_bandwidth_init_sub_flow(
                root_id=root_id, uid=uid, bk_cloud_id=bk_cloud_id, machine_list=machine_bandwidth
            )
        )

    if act_exist:
        return sub_pipeline.build_sub_process(sub_name=_("机器空闲检查及初始化"))
    else:
        return None


def list_bk_host_ids(ips: list, bk_cloud_id: int) -> list:
    # 获取新部署机器对应的bk_host_ids
    res = CCApi.list_hosts_without_biz(
        {
            "fields": ["bk_host_id"],
            "host_property_filter": {
                "condition": "AND",
                "rules": [
                    {"field": "bk_host_innerip", "operator": "in", "value": ips},
                    {"field": "bk_cloud_id", "operator": "equal", "value": bk_cloud_id},
                ],
            },
        },
        use_admin=True,
    )
    if not res or "info" not in res:
        return []
    else:
        return [host["bk_host_id"] for host in res["info"]]


def list_machine_bandwidth(ips: list, bk_cloud_id: int) -> list:
    # 获取新部署机器对应的带宽
    res = CCApi.list_hosts_without_biz(
        {
            "fields": ["bk_host_innerip", "bk_svr_device_cls_name"],
            "host_property_filter": {
                "condition": "AND",
                "rules": [
                    {"field": "bk_host_innerip", "operator": "in", "value": ips},
                    {"field": "bk_cloud_id", "operator": "equal", "value": bk_cloud_id},
                ],
            },
        },
        use_admin=True,
    )
    if not res or "info" not in res:
        return []
    else:
        if "bk_host_innerip" not in res["info"][0] or "bk_svr_device_cls_name" not in res["info"][0]:
            return []
        else:
            return res["info"]


def get_bk_biz_id(bk_host_id: int) -> int:
    biz_res = CCApi.find_host_biz_relations({"bk_host_id": [bk_host_id]}, use_admin=True)
    return biz_res[0]["bk_biz_id"]
