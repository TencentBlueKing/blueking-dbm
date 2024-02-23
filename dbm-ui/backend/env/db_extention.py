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

# 云区域组件旁路配置，当本地开发或者直连云区域组件使用容器化部署时开启
DRS_SKIP_SSL = get_type_env(key="DRS_SKIP_SSL", _type=bool, default=False)
DOMAIN_SKIP_PROXY = get_type_env(key="DOMAIN_SKIP_PROXY", _type=bool, default=False)

DRS_USERNAME = get_type_env(key="DRS_USERNAME", _type=str, default=get_type_env(key="APP_ID"))
DRS_PASSWORD = get_type_env(key="DRS_PASSWORD", _type=str, default=get_type_env(key="APP_TOKEN"))
DBHA_USERNAME = get_type_env(key="DBHA_USERNAME", _type=str, default=get_type_env(key="APP_ID"))
DBHA_PASSWORD = get_type_env(key="DBHA_PASSWORD", _type=str, default=get_type_env(key="APP_TOKEN"))

# 直连区域的服务访问地址（一般为结合 k8s nodeSelector 固定 Node 所在的 IP，本地开发时可指向测试的服务地址）
DEFAULT_CLOUD_DRS_ACCESS_HOSTS = get_type_env(key="DEFAULT_CLOUD_DRS_ACCESS_HOSTS", _type=list, default=["%"])
DEFAULT_CLOUD_DBHA_ACCESS_HOSTS = get_type_env(key="DEFAULT_CLOUD_DBHA_ACCESS_HOSTS", _type=list, default=["%"])

# 资源池伪造开关
FAKE_RESOURCE_APPLY_ENABLE = get_type_env(key="FAKE_RESOURCE_APPLY_ENABLE", _type=bool, default=False)

# 跳过审批开关，默认关闭，方便本地联调
ITSM_FLOW_SKIP = get_type_env(key="ITSM_FLOW_SKIP", _type=bool, default=False)
