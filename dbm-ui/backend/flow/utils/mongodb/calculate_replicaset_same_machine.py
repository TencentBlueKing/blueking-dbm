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
from backend.db_meta.enums.cluster_type import ClusterType
from backend.flow.consts import MongoDBInstanceType, MongoDBManagerUser
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs
from backend.flow.utils.mongodb.mongodb_repo import MongoRepository


def replicaset_same_machine(bill_info: dict) -> dict:
    """计算副本集同机部署聚合"""

    # 获取集群id列表
    cluster_ids = bill_info["cluster_ids"]

    # 副本集分组信息
    # {"1.1.1.1:2.2.2.2:3.3.3.3:0":{
    # "db_version":"4.0.10",
    # "bk_cloud_id":0,
    # "hosts":[{"ip":"1.1.1.1","bk_cloud_id":0}],
    # "instance_type":"mongod",
    # "instance_info":[{"port":27001,"admin_password":"123456"}]
    # }}
    replicasets = {}
    # 集群分组信息
    clusters = []
    # 管理员用户名
    admin_user = MongoDBManagerUser.DbaUser

    for cluster_id in cluster_ids:
        cluster_info = MongoRepository().fetch_one_cluster(id=cluster_id)
        bk_cloud_id = cluster_info.bk_cloud_id

        if cluster_info.cluster_type == ClusterType.MongoShardedCluster.value:
            # 分片集群
            ip = cluster_info.get_mongos()[0].ip
            port = int(cluster_info.get_mongos()[0].port)
            clusters.append(
                {
                    "cluster_id": cluster_id,
                    "admin_user": admin_user,
                    "cluster_type": cluster_info.cluster_type,
                    "db_version": cluster_info.major_version,
                    "bk_cloud_id": bk_cloud_id,
                    "hosts": [{"ip": ip, "bk_cloud_id": bk_cloud_id}],
                    "port": port,
                    "instance_type": MongoDBInstanceType.MongoS.value,
                    "admin_password": ActKwargs().get_password(
                        ip=ip, port=port, bk_cloud_id=bk_cloud_id, username=admin_user
                    ),
                    "region": cluster_info.region,
                }
            )
        elif cluster_info.cluster_type == ClusterType.MongoReplicaSet.value:
            # 副本集集群
            ip_list = sorted([member.ip for member in cluster_info.get_shards()[0].members])
            # 同机器部署的副本集标识  "1.1.1.1:2.2.2.2:3.3.3.3:0"
            rsp_same_ip_flag = ":".join(ip_list) + ":" + str(bk_cloud_id)

            if rsp_same_ip_flag not in replicasets:
                ip = cluster_info.get_shards()[0].members[0].ip
                port = int(cluster_info.get_shards()[0].members[0].port)
                replicasets[rsp_same_ip_flag] = {}
                replicasets[rsp_same_ip_flag]["db_version"] = cluster_info.major_version
                replicasets[rsp_same_ip_flag]["cluster_type"] = cluster_info.cluster_type
                replicasets[rsp_same_ip_flag]["admin_user"] = admin_user
                replicasets[rsp_same_ip_flag]["bk_cloud_id"] = bk_cloud_id
                replicasets[rsp_same_ip_flag]["hosts"] = [{"ip": ip, "bk_cloud_id": bk_cloud_id}]
                replicasets[rsp_same_ip_flag]["instance_type"] = MongoDBInstanceType.MongoD.value
                replicasets[rsp_same_ip_flag]["region"] = cluster_info.region
                replicasets[rsp_same_ip_flag]["instance_info"] = []
                replicasets[rsp_same_ip_flag]["instance_info"].append(
                    {
                        "cluster_id": cluster_id,
                        "port": port,
                        "admin_password": ActKwargs().get_password(
                            ip=ip, port=port, bk_cloud_id=bk_cloud_id, username=MongoDBManagerUser.DbaUser
                        ),
                    }
                )
            else:
                exec_ip = replicasets[rsp_same_ip_flag]["hosts"][0]["ip"]
                for member in cluster_info.get_shards()[0].members:
                    if member.ip == exec_ip:
                        port = int(member.port)
                        replicasets[rsp_same_ip_flag]["instance_info"].append(
                            {
                                "cluster_id": cluster_id,
                                "port": port,
                                "admin_password": ActKwargs().get_password(
                                    ip=exec_ip, port=port, bk_cloud_id=bk_cloud_id, username=MongoDBManagerUser.DbaUser
                                ),
                            }
                        )
        else:
            raise Exception("cluster type:{} not support".format(cluster_info["cluster_type"]))

    # 副本集分组列表
    bill_info[ClusterType.MongoReplicaSet.value] = [value for _, value in replicasets.items()]
    bill_info[ClusterType.MongoShardedCluster.value] = clusters
    return bill_info
