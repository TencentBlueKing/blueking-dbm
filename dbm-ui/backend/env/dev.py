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

# 云区域组件旁路配置
DRS_SKIP_SSL = get_type_env(key="DRS_SKIP_SSL", _type=bool, default=False)
DOMAIN_SKIP_PROXY = get_type_env(key="DOMAIN_SKIP_PROXY", _type=bool, default=False)
DRS_USERNAME = get_type_env(key="DRS_USERNAME", _type=str, default="")
DRS_PASSWORD = get_type_env(key="DRS_PASSWORD", _type=str, default="")
DBHA_USERNAME = get_type_env(key="DBHA_USERNAME", _type=str, default="")
DBHA_PASSWORD = get_type_env(key="DBHA_PASSWORD", _type=str, default="")
TEST_ACCESS_HOSTS = get_type_env(key="TEST_ACCESS_HOSTS", _type=list, default=[])

# 资源池伪造开关
FAKE_RESOURCE_APPLY_ENABLE = get_type_env(key="FAKE_RESOURCE_APPLY_ENABLE", _type=bool, default=False)

# 跳过审批开关，默认关闭，方便本地联调
ITSM_FLOW_SKIP = get_type_env(key="ITSM_FLOW_SKIP", _type=str, default=False)
