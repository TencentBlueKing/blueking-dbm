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

from django.core.exceptions import ObjectDoesNotExist

from backend.db_meta.enums import AccessLayer, ClusterType, TenDBClusterSpiderRole
from backend.db_meta.exceptions import ClusterEntryNotExistException
from backend.db_meta.models import ClusterEntry


def cluster_instances(entry_name: str):
    """
    TenDBCluster 的授权只需要和 spider 交互, 所以这个 api 不需要返回存储层的信息
    授权系统设计权限申请会同时在主备开通, 所以所有的 spider 都需要返回
    稍微特殊的是, 运维节点(老系统中的 tmp 节点) 是例外的
    但是也不用多虑, 因为对于运维节点的授权不会用到这个 api, 而是在确定集群 immute_domain 后选择的明文 ip:port
    所以目前可以认为, 这个 api 不需要返回运维节点的信息
    bind_to 虽然没什么用, 但还是保留下来了, 让 api 的 response 看起来更相似一些
    """
    try:
        input_entry = ClusterEntry.objects.get(entry=entry_name, cluster__cluster_type=ClusterType.TenDBCluster.value)
        cluster = input_entry.cluster

        return {
            "bind_to": AccessLayer.PROXY.value,
            "entry_role": input_entry.role,
            "cluster_type": cluster.cluster_type,
            "bk_biz_id": cluster.bk_biz_id,
            "db_module_id": cluster.db_module_id,
            "bk_cloud_id": cluster.bk_cloud_id,
            "immute_domain": cluster.immute_domain,
            "spider_master": [
                {"ip": ele.machine.ip, "port": ele.port}
                for ele in cluster.proxyinstance_set.filter(
                    tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER.value
                )
            ],
            "spider_slave": [
                {"ip": ele.machine.ip, "port": ele.port}
                for ele in cluster.proxyinstance_set.filter(
                    tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE.value
                )
            ],
            # "spider_mnt": [
            #     {"ip": ele.machine.ip, "port": ele.port}
            #     for ele in cluster.proxyinstance_set.filter(
            #         tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MNT.value
            #     )
            # ],
        }
    except ObjectDoesNotExist:
        raise ClusterEntryNotExistException(entry=entry_name)
