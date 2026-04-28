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

import sys
import types

def patch_bk_plugin_framework():
    """Mock bk_plugin_framework 模块，避免引入整个 SDK"""
    for mod_name in ["bk_plugin_framework", "bk_plugin_framework.kit", "bk_plugin_framework.kit.decorators"]:
        sys.modules.setdefault(mod_name, types.ModuleType(mod_name))
    sys.modules["bk_plugin_framework.kit.decorators"].inject_user_token = lambda f: f
