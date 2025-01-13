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
import os
from collections import defaultdict
from typing import Dict, List

from backend.utils.register import re_import_modules
from config import BASE_DIR

logger = logging.getLogger("root")

db_report_maps: Dict[str, List] = defaultdict(list)


def register_report(db_type):
    """巡检视图的注册器"""

    def decorator(report_cls):
        db_report_maps[db_type].append(report_cls)
        setattr(report_cls, "db_type", db_type)

    return decorator


def register_all_reports():
    """递归注册当前目录下所有的巡检报告"""
    re_import_modules(path=os.path.join(BASE_DIR, "backend/db_report/views"), module_path="backend.db_report.views")
