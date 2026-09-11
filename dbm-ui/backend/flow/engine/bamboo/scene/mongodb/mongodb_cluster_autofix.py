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
import logging.config
from typing import Dict, Optional

from backend.flow.engine.bamboo.scene.mongodb.mongodb_machine_replace import MongoMachineReplaceFlow

logger = logging.getLogger("flow")


class MongoClusterAutofixFlow(object):
    """
    MongoDB分片集群自愈flow（兼容薄壳）。

    实际编排见 MongoMachineReplaceFlow；请新代码直接使用后者。
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data
        self._impl = MongoMachineReplaceFlow(root_id=root_id, data=data)

    def cluster_autofix_flow(self):
        self._impl.multi_host_replace_flow()
