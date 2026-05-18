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
import logging

from backend.flow.utils.oracle.oracle_password import OraclePassword

logger = logging.getLogger("flow")


def ip_change_password(old_ip: str, old_port: int, new_ip: str, new_port: int, bk_cloud_id: int):
    """
    修改 Oracle 密码
    """

    manager_user = "perfstat"
    execute_user = "execute_user"
    oracle_password = OraclePassword()
    for username in [manager_user, execute_user]:
        # 获取旧机器密码
        result = oracle_password.get_password_from_db(
            ip=old_ip, port=old_port, bk_cloud_id=bk_cloud_id, username=username
        )
        if result["password"] is None:
            raise ValueError(
                "get {}:{} password of user:{} from password service fail, error:{}".format(
                    old_ip, old_port, username, result["info"]
                )
            )
        # 保存新机器密码
        result = oracle_password.save_password_to_db(
            instances=[{"ip": new_ip, "port": new_port, "bk_cloud_id": bk_cloud_id}],
            username=username,
            password=result["password"],
            operator="admin",
        )
        if result:
            raise ValueError("{}:{} save user:{} password fail, error:{}".format(new_ip, new_port, username, result))
    # 删除旧机器密码
    result = oracle_password.delete_password_from_db(
        instances=[{"ip": old_ip, "port": old_port, "bk_cloud_id": bk_cloud_id}],
        usernames=[manager_user, execute_user],
    )
    if result:
        raise ValueError(
            "{}:{} delete users:{} password fail, error:{}".format(
                old_ip, old_port, [manager_user, execute_user], result
            )
        )
