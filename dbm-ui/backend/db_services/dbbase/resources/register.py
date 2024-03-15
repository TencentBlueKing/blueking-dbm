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
import importlib
import logging
import os
from typing import Dict

from backend.db_services.dbbase.resources.query import ListRetrieveResource

logger = logging.getLogger("root")

# 获取集群类型与对应resource类的映射
cluster_type__resource_class: Dict[str, ListRetrieveResource] = {}


def register_resource_decorator(*args, **kwargs):
    """resource类的装饰器"""

    def decorator(cls: ListRetrieveResource):
        # 将resource类注册到对应的单据类型
        for cluster_type in cls.cluster_types:
            cluster_type__resource_class[cluster_type] = cls
        # 其他注册逻辑...
        return cls

    return decorator


def register_all_resource(path="backend/db_services", module_path="backend.db_services"):
    """递归注册当前目录下所有的resource类"""
    for name in os.listdir(path):
        if os.path.isdir(os.path.join(path, name)):
            register_all_resource(os.path.join(path, name), ".".join([module_path, name]))
        # 所有的resource类都放在query.py文件下
        elif name == "query.py":
            try:
                module_name = name.replace(".py", "")
                import_path = ".".join([module_path, module_name])
                importlib.import_module(import_path)
            except ModuleNotFoundError as e:
                logger.warning(e)
