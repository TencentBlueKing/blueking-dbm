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
# fast_execute_script接口固定参数
fast_execute_script_common_kwargs = {
    "timeout": 3600,
    "account_alias": "root",
    "is_param_sensitive": 0,
}

# fast_transfer_file接口固定参数
fast_transfer_file_common_kwargs = {
    "account_alias": "root",
}

ACTUATOR_TEMPLATE = """
mkdir -p /data/install/dbactuator-{{uid}}/logs
cp /data/install/dbactuator /data/install/dbactuator-{{uid}}
cd /data/install/dbactuator-{{uid}}
chmod +x dbactuator
./dbactuator {{db_type}} {{action}} --uid {{uid}} --payload {{payload}}
"""  # noqa
