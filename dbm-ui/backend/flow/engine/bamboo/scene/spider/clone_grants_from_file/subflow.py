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
import copy
from typing import Dict

from backend.flow.consts import DBA_ROOT_USER
from backend.flow.engine.bamboo.scene.common.builder import SubProcess
from backend.flow.engine.bamboo.scene.mysql.clone_grants_from_file import (
    clone_grants_from_file_subflow as m_clone_subflow,
)


def clone_grants_from_file_subflow(
    root_id: str,
    data: Dict,
    bk_cloud_id: int,
    bk_biz_id: int,
    source_address: str,
    dest_addresses: list[str],
    run_as_system_user: str = DBA_ROOT_USER,
) -> SubProcess:
    return m_clone_subflow(
        root_id=root_id,
        data=copy.deepcopy(data),
        bk_cloud_id=bk_cloud_id,
        bk_biz_id=bk_biz_id,
        source_address=source_address,
        dest_addresses=dest_addresses,
        run_as_system_user=run_as_system_user,
    )
