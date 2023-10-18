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

# 默认云区域ID
from dataclasses import dataclass

# 默认云区域ID
DEFAULT_BK_CLOUD_ID = 0

# 一些常量值
INT_MAX = 2 ** 31 - 1

# IP 端口分隔符
IP_PORT_DIVIDER = ":"

# IP 捕获正则表达式
IP_RE_PATTERN = r"(?:(?:2(?:5[0-5]|[0-4]\d))|[0-1]?\d{1,2})(?:\.(?:(?:2(?:5[0-5]|[0-4]\d))|[0-1]?\d{1,2})){3}"

# 是否有备份系统
BACKUP_SYS_STATUS = True

# 定义默认的时区: 东八区
DEFAULT_TIME_ZONE = "+08:00"

# 定义默认时间解析格式
DATETIME_PATTERN = "%Y-%m-%d %H:%M:%S"
DATE_PATTERN = "%Y-%m-%d"

QUERY_CMDB_LIMIT = 500


# 定义添加服务实例公共固定标签结构
@dataclass
class CommonInstanceLabels:
    app: str
    app_id: str
    app_name: str
    bk_biz_id: str
    bk_cloud_id: str
    cluster_domain: str
    cluster_name: str
    cluster_type: str
    instance: str
    instance_role: str
    instance_host: str
    instance_port: str
    db_module: str


# 定义添加host的公共固定标签结构
@dataclass
class CommonHostDBMeta:
    app: str
    app_id: str
    cluster_domain: str
    cluster_type: str
    instance_role: str


# 集群状态数据缓存key
CACHE_CLUSTER_STATS = "cluster_stats"
