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
from backend.utils.env import get_type_env

# 日志平台相关环境变量

# 日志平台存储集群
BKLOG_STORAGE_CLUSTER_ID = get_type_env(key="BKLOG_STORAGE_CLUSTER_ID", _type=int)

# 存储集群是否支持冷热数据功能
BKLOG_CLUSTER_SUPPORT_HOT_COLD = get_type_env(key="BKLOG_CLUSTER_SUPPORT_HOT_COLD", _type=bool)

# 日志默认存储天数
BKLOG_DEFAULT_RETENTION = get_type_env(key="BKLOG_CLUSTER_SUPPORT_HOT_COLD", _type=int, default=7)

# 自定义日志保留天数
BKLOG_MYSQL_BACKUP_RESULT_RETENTION = get_type_env(key="BKLOG_MYSQL_BACKUP_RESULT_RETENTION", _type=int)
BKLOG_MYSQL_DBBACKUP_RESULT_RETENTION = get_type_env(key="BKLOG_MYSQL_DBBACKUP_RESULT_RETENTION", _type=int)
BKLOG_MYSQL_BINLOG_RESULT_RETENTION = get_type_env(key="BKLOG_MYSQL_BINLOG_RESULT_RETENTION", _type=int)
BKLOG_REDIS_BINGLOG_BACKUP_RETENTION = get_type_env(key="BKLOG_REDIS_BINGLOG_BACKUP_RETENTION", _type=int)
BKLOG_REDIS_FULLBACKUP_RETENTION = get_type_env(key="BKLOG_REDIS_FULLBACKUP_RETENTION", _type=int)
BKLOG_REDIS_BIG_KEY_RETENTION = get_type_env(key="BKLOG_REDIS_BIG_KEY_RETENTION", _type=int)
BKLOG_REDIS_SLOW_RETENTION = get_type_env(key="BKLOG_REDIS_SLOW_RETENTION", _type=int)
