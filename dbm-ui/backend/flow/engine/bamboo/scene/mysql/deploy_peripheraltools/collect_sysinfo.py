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
from typing import Dict

from bamboo_engine.builder import SubProcess
from django.utils.translation import ugettext as _

from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.mysql.common.common_sub_flow import update_machine_system_info_flow


def collect_sysinfo(root_id: str, data: Dict, proxy_group, storage_group) -> SubProcess:
    """
    牵扯到上下文嵌套, 标准化流程不合适搞这个
    """
    pipes = []
    for bk_cloud_id, ip_dicts in {
        k: {**proxy_group[k], **storage_group[k]} for k in set(list(proxy_group.keys()) + list(storage_group.keys()))
    }.items():
        ips = list(ip_dicts.keys())
        pipes.append(
            update_machine_system_info_flow(
                root_id=root_id, bk_cloud_id=bk_cloud_id, parent_global_data=data, ip_list=ips
            )
        )

    sp = SubBuilder(root_id=root_id, data=data)
    sp.add_parallel_sub_pipeline(sub_flow_list=pipes)
    return sp.build_sub_process(sub_name=_("收集系统信息"))
