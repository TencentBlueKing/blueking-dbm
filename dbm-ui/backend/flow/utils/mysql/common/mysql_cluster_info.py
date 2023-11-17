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
import copy
from typing import Any, Dict

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.db_meta.enums import ClusterEntryType, InstanceInnerRole, InstanceStatus
from backend.db_meta.models import Cluster, ClusterEntry


def get_cluster_info(cluster_id: int) -> Dict:
    cluster = {}
    mysql_cluster = Cluster.objects.get(id=cluster_id)
    mysql_proxy = mysql_cluster.proxyinstance_set.all()
    mysql_storage_master = mysql_cluster.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER.value)
    mysql_storage_slave = mysql_cluster.storageinstance_set.filter(
        instance_inner_role=InstanceInnerRole.SLAVE.value, status=InstanceStatus.RUNNING.value
    )
    cluster["name"] = mysql_cluster.name
    cluster["cluster_id"] = mysql_cluster.id
    cluster["cluster_type"] = mysql_cluster.cluster_type
    cluster["bk_biz_id"] = mysql_cluster.bk_biz_id
    cluster["bk_cloud_id"] = mysql_cluster.bk_cloud_id
    cluster["db_module_id"] = mysql_cluster.db_module_id
    cluster["old_master_ip"] = cluster["master_ip"] = mysql_storage_master.machine.ip
    cluster["master_port"] = cluster["backend_port"] = cluster["mysql_port"] = mysql_storage_master.port
    slave_ips = [y.machine.ip for y in mysql_storage_slave]
    cluster["slave_ip"] = copy.deepcopy(slave_ips)

    # 理论上应该只有一个is_standby的slave, 这里是否要先兼容老版本情况呢？
    cluster["old_slave_ip"] = mysql_storage_slave.filter(is_stand_by=True).first().machine.ip
    cluster["other_slave_info"] = [
        y.machine.ip for y in mysql_storage_slave.exclude(machine__ip=cluster["old_slave_ip"])
    ]

    cluster["proxy_ip_list"] = [x.machine.ip for x in mysql_proxy]
    cluster["proxy_port"] = mysql_proxy[0].port

    # 查询待替换的slave节点对应的域名映射关系
    domain = ClusterEntry.get_cluster_entry_map_by_cluster_ids([cluster_id])
    cluster["master_domain"] = domain[cluster_id]["master_domain"]
    cluster["slave_domain"] = domain[cluster_id]["slave_domain"]
    old_slave = mysql_cluster.storageinstance_set.get(machine__ip=cluster["old_slave_ip"])
    slave_dns_list = old_slave.bind_entry.filter(cluster_entry_type=ClusterEntryType.DNS.value).all()
    cluster["slave_dns_list"] = [i.entry for i in slave_dns_list]
    # cluster["new_master_ip"] = new_master_ip
    # cluster["new_slave_ip"] = new_slave_ip
    return cluster


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
