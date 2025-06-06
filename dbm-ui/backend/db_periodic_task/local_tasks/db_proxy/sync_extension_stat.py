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
import datetime
import logging

from backend.components import BKMonitorV3Api
from backend.db_periodic_task.local_tasks.db_proxy.constants import (
    CLOUD_COMMON_UNIFY_QUERY_PARAMS,
    QUERY_TEMPLATE_CLOUD_MAP,
)
from backend.db_proxy.constants import ExtensionServiceStatus
from backend.db_proxy.models import DBExtension
from backend.flow.consts import CloudServiceModuleName

logger = logging.getLogger("celery")


def sync_db_extension_stat():
    """同步云区域组件状态"""

    # 待更新的组件
    updated_extensions = []

    for extension in CloudServiceModuleName.get_values():
        if extension not in QUERY_TEMPLATE_CLOUD_MAP:
            continue
        params = copy.deepcopy(CLOUD_COMMON_UNIFY_QUERY_PARAMS)
        template = QUERY_TEMPLATE_CLOUD_MAP[extension]

        end_time = datetime.datetime.now(datetime.timezone.utc)
        start_time = end_time - datetime.timedelta(minutes=template["range"])

        # 更新查询的组件参数
        params["query_configs"][0]["metrics"] = template["metrics"]
        params["query_configs"][0]["where"][0]["value"] = [template["process_name"]]
        params["start_time"] = int(start_time.timestamp())
        params["end_time"] = int(end_time.timestamp())

        # 查询状态指标
        series = BKMonitorV3Api.unify_query(params)["series"]
        # 根据指标状态更新组件状态
        ip_list = [s["dimensions"]["bk_target_ip"] for s in series]
        db_extensions = DBExtension.objects.filter(extension=extension, details__ip__in=ip_list)
        ip__db_extension = {e.details["ip"]: e for e in db_extensions}

        for s in series:
            # 能读到数据，说明进程正常
            if s["datapoints"][-1][0] > 0:
                continue
            db_extension = ip__db_extension[s["dimensions"]["bk_target_ip"]]
            db_extension.status = ExtensionServiceStatus.UNAVAILABLE
            updated_extensions.append(db_extension)

    DBExtension.objects.bulk_update(updated_extensions)
