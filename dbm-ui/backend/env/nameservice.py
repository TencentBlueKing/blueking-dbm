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

# 北极星域名，用于跳转链接，仅供内部使用
NAMESERVICE_POLARIS_DOMAIN = get_type_env(key="NAMESERVICE_POLARIS_DOMAIN", _type=str, default="https://a.b.c/")
# 名字服务北极星部门字段
NAMESERVICE_POLARIS_DEPARTMENT = get_type_env(key="NAMESERVICE_POLARIS_DEPARTMENT", _type=str, default="")
# 名字服务添加clb域名
CLB_DOMAIN = get_type_env(key="CLB_DOMAIN", _type=bool, default=False)
