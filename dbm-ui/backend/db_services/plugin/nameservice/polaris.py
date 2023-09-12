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
from typing import Any, Dict

from django.db import transaction

from backend.components import NameServiceApi
from backend.configuration.constants import DBType
from backend.configuration.models import DBAdministrator
from backend.db_meta import api
from backend.db_meta.enums import ClusterEntryType
from backend.db_meta.models import Cluster
from backend.db_services.cmdb import biz
from backend.db_services.plugin.nameservice.clb import response_fail, response_ok
from backend.env import NAMESERVICE_POLARIS_DEPARTMENT


@transaction.atomic
def delete_polaris(domain: str):
    """删除db中polaris数据"""

    cluster = Cluster.objects.filter(immute_domain=domain).get()
    cluster.clusterentry_set.filter(cluster_entry_type=ClusterEntryType.POLARIS).delete()


def get_cluster_info(cluster_id: int) -> Dict[str, Any]:
    """获取集群信息"""

    # 获取集群信息
    result = api.cluster.nosqlcomm.other.get_cluster_detail(cluster_id)
    cluster = result[0]
    return cluster


def create_service_alias_bind_targets(cluster_id: int) -> Dict[str, Any]:
    """创建polaris并绑定后端主机"""

    # 获取集群信息
    cluster = get_cluster_info(cluster_id=cluster_id)
    domain = cluster["immute_domain"]

    # 判断polaris是否已经存在
    if ClusterEntryType.POLARIS.value in cluster["clusterentry_set"]:
        message = "polaris of cluster:{} has been existed".format(domain)
        return response_fail(code=3, message=message)
    name = "polaris." + domain
    ips = cluster["twemproxy_set"]
    department = NAMESERVICE_POLARIS_DEPARTMENT
    bk_biz_id = cluster["bk_biz_id"]

    # 通过bk_biz_id获取dba列表
    users = DBAdministrator().get_biz_db_type_admins(bk_biz_id, DBType.Redis)
    users = [user for user in users if user != "admin"]
    owners = ";".join(users)

    # 获取业务名称
    business = biz.get_db_app_abbr(bk_biz_id)
    comment = users[0]

    # 进行请求，得到返回结果
    output = NameServiceApi.polaris_create_service_alias_and_bind_targets(
        {
            "name": name,
            "owners": owners,
            "department": department,
            "business": business,
            "ips": ips,
            "comment": comment,
        },
        raw=True,
    )
    return output


def add_polaris_info_to_meta(output: Dict[str, Any], cluster_id: int, creator: str) -> Dict[str, Any]:
    """添加polaris信息到meta"""

    # 获取信息
    cluster = get_cluster_info(cluster_id=cluster_id)
    # 进行判断请求结果,请求结果正确，写入数据库
    if output["code"] == 0 and ClusterEntryType.POLARIS.value not in cluster["clusterentry_set"]:
        try:
            api.entry.polaris.create(
                [
                    {
                        "domain": cluster["immute_domain"],
                        "polaris_name": output["data"]["servicename"],
                        "polaris_token": output["data"]["servicetoken"],
                        "polaris_l5": output["data"]["alias"],
                        "alias_token": output["data"]["aliastoken"],
                    }
                ],
                creator,
            )
        except Exception as e:
            message = "add polaris info to meta fail, error:{}".format(str(e))
            return response_fail(code=3, message=message)
    return response_ok()


def delete_polaris_info_from_meta(output: Dict[str, Any], cluster_id: int) -> Dict[str, Any]:
    """在meta中删除polaris信息"""

    # 获取信息
    cluster = get_cluster_info(cluster_id=cluster_id)
    # 进行判断请求结果
    if output["code"] == 0 and ClusterEntryType.POLARIS.value in cluster["clusterentry_set"]:
        servicename = cluster["clusterentry_set"]["polaris"][0]["polaris_name"]
        try:
            delete_polaris(cluster["immute_domain"])
        except Exception as e:
            message = "delete polaris sucessfully, delete polaris:{} info in db fail, error:{}".format(
                servicename, str(e)
            )
            return response_fail(code=1, message=message)
    return response_ok()


def unbind_targets_delete_alias_service(cluster_id: int) -> Dict[str, Any]:
    """解绑后端主机并删除polaris"""

    # 获取集群信息
    cluster = get_cluster_info(cluster_id=cluster_id)
    domain = cluster["immute_domain"]

    # 判断polaris是否存在
    if ClusterEntryType.POLARIS.value not in cluster["clusterentry_set"]:
        message = "polaris of cluster:{} is not existed".format(domain)
        return response_fail(code=3, message=message)
    servicename = cluster["clusterentry_set"]["polaris"][0]["polaris_name"]
    servicetoken = cluster["clusterentry_set"]["polaris"][0]["polaris_token"]
    alias = cluster["clusterentry_set"]["polaris"][0]["polaris_l5"]
    aliastoken = cluster["clusterentry_set"]["polaris"][0]["alias_token"]

    # 进行请求，得到返回结果
    output = NameServiceApi.polaris_unbind_targets_and_delete_alias_service(
        {
            "servicename": servicename,
            "servicetoken": servicetoken,
            "alias": alias,
            "aliastoken": aliastoken,
        },
        raw=True,
    )
    return output
