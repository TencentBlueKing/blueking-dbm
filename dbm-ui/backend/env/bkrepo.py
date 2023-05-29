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

# 制品库相关环境变量
from ..utils.env import get_type_env

STORAGE_TYPE = get_type_env(key="STORAGE_TYPE", _type=str, default="BLUEKING_ARTIFACTORY")
FILE_OVERWRITE = get_type_env(key="FILE_OVERWRITE", _type=bool, default=True)
BKREPO_USERNAME = get_type_env(key="BKREPO_USERNAME", _type=str)
BKREPO_PASSWORD = get_type_env(key="BKREPO_PASSWORD", _type=str)
BKREPO_PROJECT = get_type_env(key="BKREPO_PROJECT", _type=str)
# 默认文件存放仓库
BKREPO_BUCKET = get_type_env(key="BKREPO_PUBLIC_BUCKET", _type=str)
# 对象存储平台域名
BKREPO_ENDPOINT_URL = get_type_env(key="BKREPO_ENDPOINT_URL", _type=str)
# 备份系统相关系统变量
IBS_INFO_URL = get_type_env(key="IBS_INFO_URL", _type=str)
IBS_INFO_KEY = get_type_env(key="IBS_INFO_KEY", _type=str)
IBS_INFO_SYSID = get_type_env(key="IBS_INFO_SYSID", _type=str)

# 密钥文件存储路径
BKREPO_SSL_PATH = "/cloud/ssl"
