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
from typing import Dict, List

from bamboo_engine.builder import SubProcess

from backend.flow.engine.bamboo.scene.mysql.common.common_sub_flow import update_machine_system_info_flow


def collect_sysinfo(root_id: str, data: Dict, bk_cloud_id: int, ips: List[str]) -> SubProcess:
    return update_machine_system_info_flow(
        root_id=root_id, bk_cloud_id=bk_cloud_id, parent_global_data=data, ip_list=ips
    )
