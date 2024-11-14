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

# 同步元数据相关环境变量
SYNC_META_ENABLE = get_type_env(key="SYNC_META_ENABLE", _type=bool, default="")
SYNC_META_APP_CODE = get_type_env(key="SYNC_META_APP_CODE", _type=str, default="")
SYNC_META_APP_TOKEN = get_type_env(key="SYNC_META_APP_TOKEN", _type=str, default="")
SYNC_META_DBM_APIGW_DOMAIN = get_type_env(key="SYNC_META_DBM_APIGW_DOMAIN", _type=str, default="")
SYNC_META_BIZ_ID = get_type_env(key="SYNC_META_BIZ_ID", _type=int, default="")
SYNC_META_CREATOR = get_type_env(key="SYNC_META_CREATOR", _type=str, default="admin")


# TENDBHA
SYNC_META_TENDBHA_MODULE_ID = get_type_env(key="SYNC_META_TENDBHA_MODULE_ID", _type=int, default="")
SYNC_META_TENDBHA_BACKEND_SPEC_ID = get_type_env(key="SYNC_META_TENDBHA_BACKEND_SPEC_ID", _type=int, default="")
SYNC_META_TENDBHA_PROXY_SPEC_ID = get_type_env(key="SYNC_META_TENDBHA_PROXY_SPEC_ID", _type=int, default="")
SYNC_META_TENDBHA_CHARSET = get_type_env(key="SYNC_META_TENDBHA_CHARSET", _type=str, default="utf8mb4")
