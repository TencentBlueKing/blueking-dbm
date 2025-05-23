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

# 创建原子任务创建目录
oracle_create_actuator_dir_template = """
find {{file_path}}/install -mtime +30  -type d -name "dbactuator-*"  |xargs rm -rf
mkdir -p {{file_path}}/install/dbactuator-{{uid}}/logs
cp {{file_path}}/install/oracle-dbactuator {{file_path}}/install/dbactuator-{{uid}}
"""


# os初始化原子任务模板
oracle_os_init_actuator_template = """
cd {{file_path}}/install/dbactuator-{{uid}}
chmod +x oracle-dbactuator
./oracle-dbactuator --uid {{uid}} --root_id {{root_id}} --node_id {{node_id}} \
--version_id {{version_id}}  --atom-job-list {{action}}
"""


# 其他原子任务模板
oracle_actuator_template = """
cd {{file_path}}/install/dbactuator-{{uid}}
chmod +x oracle-dbactuator
./oracle-dbactuator --uid {{uid}} --root_id {{root_id}} --node_id {{node_id}} \
--version_id {{version_id}} --payload {{payload}} --atom-job-list {{action}}
"""


def make_script_common_kwargs(timeout=3600, exec_account="root", is_param_sensitive=0):
    """
    make_script_common_kwargs 生成脚本执行的公共参数
    """
    return {
        "timeout": timeout,
        "account_alias": exec_account,
        "is_param_sensitive": is_param_sensitive,
    }
