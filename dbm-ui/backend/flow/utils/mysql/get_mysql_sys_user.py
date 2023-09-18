"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from backend import env
from backend.core.encrypt.constants import RSAConfigType
from backend.core.encrypt.handlers import RSAHandler
from backend.db_proxy.constants import ExtensionType
from backend.db_proxy.models import DBExtension


def get_mysql_sys_users(bk_cloud_id) -> list:
    """
    增加方法：收集SaaS内mysql/spider的系统账号列表，作为固定参数传入待执行Actuator指令
    """
    sys_users_map = {
        ExtensionType.DRS: env.DRS_USERNAME,
        ExtensionType.DBHA: env.DBHA_USERNAME,
    }
    sys_users = []
    for key, value in sys_users_map.items():
        if value:
            sys_users.append(value)
        else:
            rsa = RSAHandler.get_or_generate_rsa_in_db(RSAConfigType.get_rsa_cloud_name(bk_cloud_id))
            info = DBExtension.get_latest_extension(bk_cloud_id=bk_cloud_id, extension_type=key)
            sys_users.append(RSAHandler.decrypt_password(rsa.rsa_private_key.content, info.details["user"]))

    return sys_users
