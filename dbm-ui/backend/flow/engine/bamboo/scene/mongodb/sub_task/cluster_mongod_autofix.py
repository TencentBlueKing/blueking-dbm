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

from typing import Dict, Optional

from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs

from .mongod_replace import CUTOVER_REPLACE_WITH_SOURCE_DOWN, mongod_replace


def mongod_autofix(
    root_id: str,
    ticket_data: Optional[Dict],
    sub_sub_kwargs: ActKwargs,
    cluster_role: str,
    info: dict,
) -> SubBuilder:
    """
    mongod 自愈叶子：统一走 mongod_replace 的 sourceDown 切主 + 叶子内创下架单。

    get_conf / cache&oplog / key_file 等由 mongod_replace 在 cluster_role 路径内补齐。
    """
    return mongod_replace(
        root_id=root_id,
        ticket_data=ticket_data,
        sub_sub_kwargs=sub_sub_kwargs,
        cluster_role=cluster_role,
        info=info,
        mongod_scale=False,
        cutover_mode=CUTOVER_REPLACE_WITH_SOURCE_DOWN,
        emit_deinstall_ticket=True,
    )
