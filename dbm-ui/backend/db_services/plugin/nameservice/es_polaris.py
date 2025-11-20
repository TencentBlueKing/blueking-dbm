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
from backend.db_meta.enums import ClusterEntryType, InstanceRole
from backend.db_meta.models import AppCache, Cluster, StorageInstance
from backend.db_services.plugin.nameservice.clb import response_fail, response_ok
from backend.env import NAMESERVICE_POLARIS_DEPARTMENT
from backend.flow.engine.bamboo.scene.es.atom_jobs.access_manager import get_access_ips_from_dbmeta


def create_service_alias_bind_targets(cluster_id: int) -> Dict[str, Any]:
    """创建polaris并绑定后端主机"""

    # 获取集群信息
    cluster = Cluster.objects.get(id=cluster_id)
    domain = cluster.immute_domain

    # 判断polaris是否已经存在，如果存在则直接返回
    if cluster.clusterentry_set.filter(cluster_entry_type=ClusterEntryType.POLARIS.value):
        message = "polaris of cluster:{} has been existed".format(domain)
        return response_fail(code=3, message=message)
    name = "polaris." + domain
    ips = get_access_ips_from_dbmeta(cluster_id=cluster_id)
    # 获取端口号
    masters = StorageInstance.objects.filter(cluster=cluster, instance_role=InstanceRole.ES_MASTER)
    if not masters:
        message = f"the cluster({cluster_id}, {cluster.name}) has no master node"
        return response_fail(code=3, message=message)
    port = masters.first().port

    instances = [f"{ip}:{str(port)}" for ip in ips]

    department = NAMESERVICE_POLARIS_DEPARTMENT
    bk_biz_id = cluster.bk_biz_id

    # 通过bk_biz_id获取dba列表
    users = DBAdministrator().get_biz_db_type_admins(bk_biz_id, DBType.Es)
    users = [user for user in users if user != "admin"]
    owners = ";".join(users)

    # 获取业务名称
    business = AppCache.get_app_attr(bk_biz_id)
    comment = users[0]

    # 进行请求，得到返回结果
    output = NameServiceApi.polaris_create_service_alias_and_bind_targets(
        {
            "name": name,
            "owners": owners,
            "department": department,
            "business": business,
            "ips": instances,
            "comment": comment,
        },
        raw=True,
    )
    return output


def add_polaris_info_to_meta(output: Dict[str, Any], cluster_id: int, creator: str) -> Dict[str, Any]:
    """添加polaris信息到meta"""

    # 获取信息
    cluster = Cluster.objects.get(id=cluster_id)
    # 进行判断请求结果,请求结果正确，写入数据库
    if output["code"] == 0 and not cluster.clusterentry_set.filter(cluster_entry_type=ClusterEntryType.POLARIS.value):
        try:
            api.entry.polaris.es_create(
                [
                    {
                        "domain": cluster.immute_domain,
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
    cluster = Cluster.objects.get(id=cluster_id)
    cluster_polaris_entry = cluster.clusterentry_set.filter(cluster_entry_type=ClusterEntryType.POLARIS).first()
    # 进行判断请求结果
    if output["code"] == 0 and cluster_polaris_entry:
        try:
            cluster_polaris_entry.polarisentrydetail_set.all().delete()
            cluster_polaris_entry.delete()
        except Exception as e:
            message = "delete polaris sucessfully, delete polaris:{} info in db fail, error:{}".format(
                cluster_polaris_entry.entry, str(e)
            )
            return response_fail(code=1, message=message)
    return response_ok()


def unbind_targets_delete_alias_service(cluster_id: int) -> Dict[str, Any]:
    """解绑后端主机并删除polaris"""

    # 获取集群信息
    cluster = Cluster.objects.get(id=cluster_id)
    domain = cluster.immute_domain
    cluster_polaris_entry = cluster.clusterentry_set.filter(cluster_entry_type=ClusterEntryType.POLARIS).first()
    # 判断polaris是否存在
    if not cluster_polaris_entry:
        message = "polaris of cluster:{} is not existed".format(domain)
        return response_fail(code=3, message=message)
    polaris_entry_detail = cluster_polaris_entry.polarisentrydetail_set.first()
    if not polaris_entry_detail:
        message = "polaris detail of cluster:{} is not existed".format(domain)
        return response_fail(code=3, message=message)
    service_name = polaris_entry_detail.polaris_name
    service_token = polaris_entry_detail.polaris_token
    alias = polaris_entry_detail.polaris_l5
    alias_token = polaris_entry_detail.alias_token

    # 进行请求，得到返回结果
    output = NameServiceApi.polaris_unbind_targets_and_delete_alias_service(
        {
            "servicename": service_name,
            "servicetoken": service_token,
            "alias": alias,
            "aliastoken": alias_token,
        },
        raw=True,
    )
    return output
