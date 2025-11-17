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

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class RedisRollbackExerciseConfig:
    switch: bool = False
    bk_biz_id: int = 0  # The biz where the drill ticket locates
    polling_interval: int = 10  # sec
    polling_timeout: int = 3600  # sec

    targets: Optional[Dict[int, List[str]]] = None  # Mannually specified targets
