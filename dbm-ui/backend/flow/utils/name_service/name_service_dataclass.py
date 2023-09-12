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
# name_service相关单据上下文
from dataclasses import dataclass
from typing import Any, Optional


@dataclass()
class ActKwargs:
    """节点私有变量数据类"""

    # 集群id
    cluster_id: int = None
    # 操作人员
    creator: str = None
    # 名字服务类型
    name_service_operation_type: str = None
    # 加载到上下文的dataclass类的名称
    set_trans_data_dataclass: str = None


@dataclass()
class TransDataKwargs:
    """可读写上下文"""
    
    # 调用第三方接口返回的数据
    output: Optional[Any] = None
