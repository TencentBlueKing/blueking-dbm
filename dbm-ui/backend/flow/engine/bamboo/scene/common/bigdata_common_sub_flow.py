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
from dataclasses import asdict
from typing import List

from django.utils.translation import ugettext as _

from backend import env
from backend.components import CCApi
from backend.flow.consts import BIGDATA_DEPEND_PLUGINS
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.common.install_nodeman_plugin import (
    InstallNodemanPluginServiceComponent,
)
from backend.flow.plugins.components.collections.common.sa_idle_check import CheckMachineIdleComponent
from backend.flow.plugins.components.collections.common.sa_init import SaInitComponent
from backend.flow.utils.common_act_dataclass import InstallNodemanPluginKwargs

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


def make_install_plugins_acts(bk_host_ids: List[int]) -> list:
    """
    安装蓝鲸插件
    :param bk_host_ids: 机器ID列表
    :return: 安装插件act列表
    """
    # 安装插件
    acts_list = []
    # 这里用 bk_host_ids 临时兼容，更合理的做法是，参数流转都不使用 IP，统一使用 bk_host_id
    if bk_host_ids:
        for plugin_name in BIGDATA_DEPEND_PLUGINS:
            acts_list.append(
                {
                    "act_name": _("安装[{}]插件".format(plugin_name)),
                    "act_component_code": InstallNodemanPluginServiceComponent.code,
                    "kwargs": asdict(InstallNodemanPluginKwargs(bk_host_ids=bk_host_ids, plugin_name=plugin_name)),
                }
            )

    return acts_list


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
    plugin_acts = make_install_plugins_acts(bk_host_ids)
    if plugin_acts:
        act_exist = True
        sub_pipeline.add_parallel_acts(plugin_acts)

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


def get_bk_biz_id(bk_host_id: int) -> int:
    biz_res = CCApi.find_host_biz_relations({"bk_host_id": [bk_host_id]})
    return biz_res[0]["bk_biz_id"]
