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

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.db_meta.enums import InstanceInnerRole
from backend.db_meta.models import Cluster


def get_version_and_charset(bk_biz_id, db_module_id, cluster_type) -> Any:
    """获取版本号和字符集信息"""
    data = DBConfigApi.query_conf_item(
        {
            "bk_biz_id": str(bk_biz_id),
            "level_name": LevelName.MODULE,
            "level_value": str(db_module_id),
            "conf_file": "deploy_info",
            "conf_type": "deploy",
            "namespace": cluster_type,
            "format": FormatType.MAP,
        }
    )["content"]
    return data["charset"], data["db_version"]


def get_cluster_ports(cluster_ids: list) -> Dict:
    cluster_ports = []
    cluster_list = []
    clusters = Cluster.objects.filter(id__in=cluster_ids).all()
    clustertmp = clusters[0]
    db_module_id = clustertmp.db_module_id
    cluster_type = clustertmp.cluster_type
    bk_cloud_id = clustertmp.bk_cloud_id
    time_zone = clustertmp.time_zone
    for one_cluster in clusters:
        master = one_cluster.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER.value)
        cluster_port = master.port
        cluster_ports.append(cluster_port)
        cluster_list.append(
            {
                "master_ip": master.machine.ip,
                "mysql_port": cluster_port,
                "name": one_cluster.name,
                "master": one_cluster.immute_domain,
                "cluster_id": one_cluster.id,
                "bk_cloud_id": one_cluster.bk_cloud_id,
            }
        )
    cluster_info = {
        "cluster_ports": cluster_ports,
        "clusters": cluster_list,
        "db_module_id": db_module_id,
        "cluster_type": cluster_type,
        "bk_cloud_id": bk_cloud_id,
        "time_zone": time_zone,
    }
    return cluster_info


def get_ports(cluster_ids: list) -> list:
    cluster_ports = []
    clusters = Cluster.objects.filter(id__in=cluster_ids).all()
    for cluster in clusters:
        cluster_ports.append(cluster.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER.value).port)
    return cluster_ports
