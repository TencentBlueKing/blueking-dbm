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

import base64

from django.utils.translation import ugettext as _

from backend.components import DBConfigApi, MySQLPrivManagerApi
from backend.db_meta.models import Cluster
from backend.flow.consts import DBM_JOB, DEFAULT_INSTANCE, MySQLPrivComponent, UserName
from backend.flow.utils.base.payload_handler import PayloadHandler


def decode_password_ret(data) -> dict:
    ret = {"redis_password": "", "redis_proxy_admin_password": "", "redis_proxy_password": ""}
    for item in data["items"]:
        if (
            item["username"] == UserName.REDIS_DEFAULT.value
            and item["component"] == MySQLPrivComponent.REDIS_PROXY_ADMIN.value
        ):
            ret["redis_proxy_admin_password"] = base64.b64decode(item["password"]).decode("utf-8")
        elif (
            item["username"] == UserName.REDIS_DEFAULT.value
            and item["component"] == MySQLPrivComponent.REDIS_PROXY.value
        ):
            ret["redis_proxy_password"] = base64.b64decode(item["password"]).decode("utf-8")
        elif item["username"] == UserName.REDIS_DEFAULT.value and item["component"] == MySQLPrivComponent.REDIS.value:
            ret["redis_password"] = base64.b64decode(item["password"]).decode("utf-8")
    return ret


def redis_migate_cluster_password(cluster: Cluster):
    # cluster_port = cluster.proxyinstance_set.first().port
    cluster_port = 0
    query_params = {
        "instances": [{"ip": str(cluster.id), "port": cluster_port, "bk_cloud_id": cluster.bk_cloud_id}],
        "users": [
            {"username": UserName.REDIS_DEFAULT.value, "component": MySQLPrivComponent.REDIS_PROXY_ADMIN.value},
            {"username": UserName.REDIS_DEFAULT.value, "component": MySQLPrivComponent.REDIS_PROXY.value},
            {"username": UserName.REDIS_DEFAULT.value, "component": MySQLPrivComponent.REDIS.value},
        ],
    }
    data = MySQLPrivManagerApi.get_password(query_params)
    ret = decode_password_ret(data)
    if ret["redis_password"] and ret["redis_proxy_password"] and ret["redis_proxy_admin_password"]:
        print(_("cluster:{} 密码已经正确存储").format(cluster.immute_domain))
        return
    cluster_port = cluster.proxyinstance_set.first().port
    query_params = {
        "instances": [{"ip": str(cluster.id), "port": cluster_port, "bk_cloud_id": cluster.bk_cloud_id}],
        "users": [
            {"username": UserName.REDIS_DEFAULT.value, "component": MySQLPrivComponent.REDIS_PROXY_ADMIN.value},
            {"username": UserName.REDIS_DEFAULT.value, "component": MySQLPrivComponent.REDIS_PROXY.value},
            {"username": UserName.REDIS_DEFAULT.value, "component": MySQLPrivComponent.REDIS.value},
        ],
    }
    data = MySQLPrivManagerApi.get_password(query_params)
    ret = decode_password_ret(data)
    if ret["redis_password"] and ret["redis_proxy_password"] and ret["redis_proxy_admin_password"]:
        print(_("cluster:{} 密码已存储port不正确,重新存储").format(cluster.immute_domain))
        PayloadHandler.redis_save_password_by_cluster(
            cluster, ret["redis_password"], ret["redis_proxy_password"], ret["redis_proxy_admin_password"]
        )
        PayloadHandler.redis_delete_cluster_password(
            cluster_id=cluster.id, cluster_port=cluster_port, bk_cloud_id=cluster.bk_cloud_id
        )
        return
    # 从 dbconfig 中获取密码
    conf_passwd = PayloadHandler.redis_get_cluster_pass_from_dbconfig(cluster)
    if not conf_passwd["redis_password"].startswith("{{") and not conf_passwd["redis_proxy_password"].startswith("{{"):
        print(_("cluster:{} 密码从dbconfig中迁移到密码服务中").format(cluster.immute_domain))
        PayloadHandler.redis_save_password_by_cluster(cluster, conf_passwd, conf_passwd, conf_passwd)
        return
    raise Exception(_("cluster:{} 在 dbconfig和密码服务中均不存在").format(cluster.immute_domain))
