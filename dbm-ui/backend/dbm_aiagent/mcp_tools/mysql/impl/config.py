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
from backend import env
from backend.components import BKLogApi

MYSQL_SLOW_LOG_INDEX_SET_ID = 0


def init_collectors_index_set_id():
    global MYSQL_SLOW_LOG_INDEX_SET_ID

    if env.MYSQL_SLOW_LOG_INDEX_SET_ID:
        MYSQL_SLOW_LOG_INDEX_SET_ID = env.MYSQL_SLOW_LOG_INDEX_SET_ID
        return

    data = BKLogApi.list_collectors({"bk_biz_id": env.DBA_APP_BK_BIZ_ID, "pagesize": 500, "page": 1}, use_admin=True)
    collectors_name__info_map = {collector["collector_config_name_en"]: collector for collector in data["list"]}
    MYSQL_SLOW_LOG_INDEX_SET_ID = collectors_name__info_map["mysql_slowlog"]["index_set_id"]
