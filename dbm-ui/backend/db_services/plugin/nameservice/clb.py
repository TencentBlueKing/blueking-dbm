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
from backend.db_meta.models import Cluster
from backend.db_meta.enums import ClusterEntryType
from django.db import transaction


def create_lb_and_register_target(cluster_id: int, creator: str) -> Dict[str, Any]:
    """创建clb并绑定后端主机"""

    # 获取集群信息
    result = api.cluster.nosqlcomm.other.get_cluster_detail(cluster_id)
    cluster = result[0]
    domain = cluster["immute_domain"]

    # 判断clb是否已经存在
    if "clb" in cluster["clusterentry_set"]:
        return {"status": 3, "message": "clb of cluster:%s has been existed" % domain}
    region = cluster["region"]
    ips = cluster["twemproxy_set"]
    bk_biz_id = cluster["bk_biz_id"]

    # 通过bk_biz_id获取manager，backupmanager，去除admin
    users = DBAdministrator().get_biz_db_type_admins(bk_biz_id, DBType.Redis)
    users = [user for user in users if user != "admin"]
    manager = users[0]
    backupmanager = users[1] if len(users) > 1 else users[0]

    # 进行请求，得到返回结果
    output = NameServiceApi.clb_create_lb_and_register_target(
        {
            "region": region,
            "loadbalancername": domain,
            "listenername": domain,
            "manager": manager,
            "backupmanager": backupmanager,
            "protocol": "TCP",
            "ips": ips,
        },
        raw=True,
    )

    # 进行判断请求结果,请求结果正确，写入数据库
    if output["status"] == 0:
        api.entry.clb.create(
            [
                {
                    "domain": domain,
                    "clb_ip": output["loadbalancerip"],
                    "clb_id": output["loadbalancerid"],
                    "clb_listener_id": output["listenerid"],
                    "clb_region": region,
                }
            ],
            creator,
        )
    return output


def deregister_target_and_delete_lb(cluster_id: int) -> Dict[str, Any]:
    """解绑后端主机并删除clb"""

    # 获取集群信息
    result = api.cluster.nosqlcomm.other.get_cluster_detail(cluster_id)
    cluster = result[0]
    domain = cluster["immute_domain"]

    # 判断clb是否存在
    if "clb" not in cluster["clusterentry_set"]:
        return {"status": 3, "message": "clb of cluster:%s is not existed" % domain}
    region = cluster["clusterentry_set"]["clb"][0]["clb_region"]
    loadbalancerid = cluster["clusterentry_set"]["clb"][0]["clb_id"]
    listenerid = cluster["clusterentry_set"]["clb"][0]["listener_id"]

    # 进行请求，得到返回结果
    output = NameServiceApi.clb_deregister_target_and_del_lb(
        {
            "region": region,
            "loadbalancerid": loadbalancerid,
            "listenerid": listenerid,
        },
        raw=True,
    )

    # 进行判断请求结果，如果为0操作删除db数据
    if output["status"] == 0:
        err = delete_clb(domain)
        if err is not None:
            output["status"] = 1
            output["message"] = "delete clb sucessfully, delete clb:{} info in db fail, error:{}".format(
                loadbalancerid, err)
    return output


@transaction.atomic
def delete_clb(domain: str) -> str:
    """删除db中clb数据"""

    try:
        cluster = Cluster.objects.filter(immute_domain=domain).get()
        cluster.clusterentry_set.filter(cluster_entry_type=ClusterEntryType.CLB).delete()
    except Exception as e:
        return str(e)
