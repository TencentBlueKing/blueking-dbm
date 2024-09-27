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
import re

from backend.ticket.constants import TicketType
from blue_krill.data_types.enum import EnumField, StructuredEnum

# 常规字段长度定义
LEN_SHORT = 32
LEN_NORMAL = 64
LEN_MIDDLE = 128
LEN_LONG = 255
LEN_L_LONG = 512
LEN_X_LONG = 1000
LEN_XX_LONG = 10000

IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

# 字段默认值
EMPTY_INT = 0
EMPTY_STRING = ""
EMPTY_DISPLAY_STRING = "--"
EMPTY_LIST = []
EMPTY_DICT = {}
EMPTY = "EMPTY"

# 特殊值
SMALLEST_POSITIVE_INTEGER = 1

# CACHE
CACHE_1MIN = 60
CACHE_5MIN = 5 * 60
CACHE_30MIN = 30 * 60
CACHE_1H = 1 * 60 * 60
CACHE_1D = 24 * 60 * 60

# 外部请求路由白名单
ROUTING_WHITELIST_PATTERNS = [
    # 大数据集群视图接口匹配模式
    r"/apis/bigdata\/bizs/[0-9]+\/([a-z_]+)?/\1_resources/[0-9a-z_\/]*",
    # 其他集群视图接口匹配模式
    r"/apis/[a-z_]+/bizs/[0-9]+/[a-z_]+?_resources/[0-9a-z_/]*",
    # 单据接口匹配模式
    r"/apis/tickets/",
    r"/apis/tickets/[0-9]+/[a-z_/]*/",
    # 集群相关接口
    r"/apis/dbbase/query_biz_cluster_attrs/",
    r"/apis/cmdb/[0-9]+/list_modules/",
    r"/apis/mysql/bizs/[0-9]+/remote_service/show_cluster_databases/",
    r"/apis/dbbase/simple_query_cluster/",
    # webconsole
    r"/apis/dbbase/webconsole/",
    # 平台设置相关接口
    "/apis/conf/biz_settings/simple/",
    # grafana和监控相关接口
    r"/grafana/*",
    r"/apis/monitor/grafana/get_dashboard/",
    # 制品库
    r"/apis/core/storage/create_bkrepo_access_token/",
    r"/apis/core/storage/generic/temporary/download/*",
    r"/apis/generic/temporary/download/*",
]

# 外部请求非转发路由(需要请求本地的视图)
NON_EXTERNAL_PROXY_ROUTING = [
    # 功能控制器
    "/apis/conf/function_controller/",
    # 环境变量
    "/apis/conf/system_settings/environ/",
    # django
    "/swagger/",
    "/admin/",
]

# 外部请求允许的白名单单据类型
EXTERNAL_TICKET_TYPE_WHITELIST = [TicketType.MYSQL_DUMP_DATA, TicketType.TENDBCLUSTER_DUMP_DATA]


# LOG
class LogLevelName(str, StructuredEnum):
    INFO = EnumField("INFO", "INFO")
    WARNING = EnumField("WARNING", "WARNING")
    ERROR = EnumField("ERROR", "ERROR")
    DEBUG = EnumField("DEBUG", "DEBUG")
