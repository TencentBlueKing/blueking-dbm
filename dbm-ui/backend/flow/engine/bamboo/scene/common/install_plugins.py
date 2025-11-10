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
from typing import List, Optional

from bamboo_engine.builder import SubProcess
from django.utils.translation import gettext as _

from backend.flow.consts import DEPENDENCIES_PLUGINS
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.exceptions import PipelineError
from backend.flow.plugins.components.collections.common.install_nodeman_plugin import (
    InstallNodemanPluginServiceComponent,
)
from backend.flow.utils.common_act_dataclass import InstallNodemanPluginKwargs

logger = logging.getLogger("flow")


def install_nodeman_plugins(
    root_id: str, uid: str = None, bk_host_ids: List[int] = None, ips: List[str] = None, bk_cloud_id: int = None
) -> Optional[SubProcess]:
    """
    安装节点管理插件
    @param root_id: 根流程id
    @param uid: 单据ID
    @param bk_host_ids: 主机id列表(主机IP或者主机ID二选一)
    @param ips: 主机ip列表
    @param bk_cloud_id: 云区域id
    @return: 安装节点管理子流程
    """
    if not bk_host_ids and (not ips or not bk_cloud_id):
        raise PipelineError(_("不存在主机，无法安装节点管理插件"))

    plugin_pipeline = SubBuilder(root_id=root_id, data={"uid": uid})

    acts_list = []
    for plugin in DEPENDENCIES_PLUGINS:
        acts_list.append(
            {
                "act_name": _("安装[{}]插件".format(plugin)),
                "act_component_code": InstallNodemanPluginServiceComponent.code,
                "kwargs": asdict(
                    InstallNodemanPluginKwargs(
                        bk_host_ids=bk_host_ids, plugin_name=plugin, ips=ips, bk_cloud_id=bk_cloud_id
                    )
                ),
                "timeout": 600,
            }
        )

    plugin_pipeline.add_parallel_acts(acts_list=acts_list)
    return plugin_pipeline.build_sub_process(sub_name=_("安装节点管理插件"))
