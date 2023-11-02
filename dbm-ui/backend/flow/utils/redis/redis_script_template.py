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
# 这里独立出来，遇到过全局变量被其他db修改，导致用户错乱的问题
redis_fast_execute_script_common_kwargs = {
    "timeout": 3600,
    "account_alias": "root",
    "is_param_sensitive": 0,
}

redis_actuator_template = """
mkdir -p {{data_dir}}/install/dbactuator-{{uid}}/logs
cp {{data_dir}}/install/dbactuator_redis {{data_dir}}/install/dbactuator-{{uid}}
cd {{data_dir}}/install/dbactuator-{{uid}}
chmod +x dbactuator_redis
./dbactuator_redis --uid {{uid}} --root_id {{root_id}} --node_id {{node_id}} \
--version_id {{version_id}} --payload {{payload}} --atom-job-list {{action}}
"""


redis_data_structure_payload_template = """
{{payload}}
"""

redis_data_structure_actuator_template = """
mkdir -p {{data_dir}}/install/dbactuator-{{uid}}/logs
cp {{data_dir}}/install/dbactuator_redis {{data_dir}}/install/dbactuator-{{uid}}
cd {{data_dir}}/install/dbactuator-{{uid}}
chmod +x dbactuator_redis
./dbactuator_redis --uid {{uid}} --root_id {{root_id}} --node_id {{node_id}} \
--version_id {{version_id}} --payload_file={{data_dir}}/install/{{file_name}} --atom-job-list {{action}}
"""
