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

from backend.components import NameServiceApi
from backend.configuration.constants import DBType
from backend.configuration.models import DBAdministrator
from backend.db_meta import api
from backend.db_services.cmdb import biz
from backend.env import NAMESERVICE_POLARIS_DEPARTMENT


def create_service_alias_and_bind_targets(cluster_id: int, creator: str) -> Dict[str, Any]:
    """创建polaris并绑定后端主机"""

    # 获取集群信息
    result = api.cluster.nosqlcomm.get_cluster_detail(cluster_id)
    cluster = result[0]
    domain = cluster["immute_domain"]

    # 判断polaris是否已经存在
    if "polaris" in cluster["clusterentry_set"]:
        return {"status": 3, "message": "polaris of cluster:%s has been existed" % domain}
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

    # 进行判断请求结果,请求结果正确，写入数据库
    if output["status"] == 0:
        api.entry.polaris.create(
            [
                {
                    "domain": domain,
                    "polaris_name": output["servicename"],
                    "polaris_token": output["servicetoken"],
                    "polaris_l5": output["alias"],
                    "alias_token": output["aliastoken"],
                }
            ],
            creator,
        )
    return output


def unbind_targets_and_delete_alias_service(cluster_id: int) -> Dict[str, Any]:
    """解绑后端主机并删除polaris"""

    # 获取集群信息
    result = api.cluster.nosqlcomm.get_cluster_detail(cluster_id)
    cluster = result[0]
    domain = cluster["immute_domain"]

    # 判断polaris是否存在
    if "polaris" not in cluster["clusterentry_set"]:
        return {"status": 3, "message": "polaris of cluster:%s is not existed" % domain}

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

    # 进行判断请求结果
    if output["status"] == 0:
        # TODO 请求结果正确，删除数据库信息
        pass
    return output
