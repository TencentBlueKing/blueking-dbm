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
from abc import abstractmethod
from typing import Dict, Optional

from bamboo_engine.builder import Data, EmptyStartEvent


class Builder(object):
    """
    构建子流程基本实现

    Attributes:
        root_id: 根流程id
        data: 单据所传递数据
        pipeline_data: 是否需要处理上下文
    """

    def __init__(self, root_id: str, data: Dict, pipeline_data: Optional[Data] = None):
        self.root_id = root_id
        self.data = data
        self.pipeline_data = pipeline_data

    @abstractmethod
    def build_tree(self) -> EmptyStartEvent:
        pass
