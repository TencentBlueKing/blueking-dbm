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
import traceback
from collections import defaultdict
from typing import Dict, List

from django.db import transaction

from backend.db_meta.api import common
from backend.db_meta.api.cluster.nosqlcomm.cc_ops import cc_add_instances, cc_del_service_instances
from backend.db_meta.enums import AccessLayer, ClusterMachineAccessTypeDefine, DBCCModule, InstanceInnerRole
from backend.db_meta.models import Cluster, ProxyInstance

logger = logging.getLogger("flow")


@transaction.atomic
def add_proxies(cluster: Cluster, proxies: List[Dict]):
    """
    1. 不能已添加
    2. 不能归属于其他集群
    3. DNS/CLB/POLARIS 剔除 （放到流程）
    4. Done(新实例端口需要和源集群端口一致)
    """
    logger.info("user request cluster add proxies {} {}".format(cluster.immute_domain, proxies))
    proxy_objs = common.filter_out_instance_obj(
        proxies,
        ProxyInstance.objects.filter(
            machine_type=ClusterMachineAccessTypeDefine[cluster.cluster_type][AccessLayer.PROXY],
        ),
    )

    _t = common.not_exists(proxies, proxy_objs)
    if _t:
        raise Exception("{} not match".format(_t))

    _t = common.in_another_cluster(proxy_objs)
    if _t:
        raise Exception("{} in another cluster".format(_t))

    # 检查 新proxy 端口 必须和 集群端口一致
    cluster_ports = defaultdict(int)
    for p_obj in cluster.proxyinstance_set.all():
        cluster_ports[p_obj.port] += 1
    for proxy in proxies:
        if cluster_ports.get(proxy["port"]) is None:
            raise Exception("{} new proxy port not in cluster ports {}".format(proxy, cluster_ports.keys()))
    try:
        # 修改表 db_meta_proxyinstance_cluster
        cluster.proxyinstance_set.add(*proxy_objs)
        logger.info("cluster {} add proxyinstance {}".format(cluster.immute_domain, proxy_objs))

        # 修改表 db_meta_proxyinstance_bind_entry
        for cluster_entry_obj in cluster.clusterentry_set.all():
            cluster_entry_obj.proxyinstance_set.add(*proxy_objs)
            logger.info(
                "cluster {} entry {} add proxyinstance {}".format(
                    cluster.immute_domain, cluster_entry_obj.entry, proxy_objs
                )
            )
        # 修改表  db_meta_storageinstance_cluster 这里边已经包含master和slave
        master_objs = list(cluster.storageinstance_set.filter(instance_inner_role=InstanceInnerRole.MASTER))
        # 修改表  db_meta_proxyinstance_storageinstance
        for proxy_obj in proxy_objs:
            proxy_obj.db_module_id = cluster.db_module_id
            proxy_obj.cluster_type = cluster.cluster_type
            proxy_obj.storageinstance.add(*master_objs)
            proxy_obj.save(update_fields=["db_module_id", "cluster_type"])
        logger.info("cluster {} add storageinstance {}".format(cluster.immute_domain, master_objs))
        cc_add_instances(cluster, proxy_objs, DBCCModule.REDIS.value)
    except Exception as e:  # NOCC:broad-except(检查工具误报)
        logger.error(traceback.format_exc())
        raise e


@transaction.atomic
def delete_proxies(cluster: Cluster, proxies: List[Dict]):
    """
    这里并没有把实例下架， 只是从集群剔除，所以主机转移没放在这里， machine表清理也不在这里
    """
    logger.info("user request cluster delete proxies {} {}".format(cluster.immute_domain, proxies))
    try:
        proxy_objs = common.filter_out_instance_obj(proxies, cluster.proxyinstance_set.all())

        no_obj = common.not_exists(proxies, proxy_objs)
        if no_obj:
            raise Exception("{} not match".format(no_obj))

        # 修改表  db_meta_proxyinstance_cluster
        cluster.proxyinstance_set.remove(*proxy_objs)
        logger.info("cluster {} remove proxyinstance {}".format(cluster.immute_domain, proxy_objs))
        # 修改表  db_meta_proxyinstance_bind_entry
        for cluster_entry_obj in cluster.clusterentry_set.all():
            cluster_entry_obj.proxyinstance_set.remove(*proxy_objs)
            logger.info(
                "cluster {} entry {} remove proxyinstance {}".format(
                    cluster.immute_domain, cluster_entry_obj.entry, proxy_objs
                )
            )

        cc_del_service_instances(proxy_objs)
        # 修改表  db_meta_proxyinstance_storageinstance bUG Fixed
        for proxy_obj in proxy_objs:
            proxy_obj.storageinstance.clear()
            logger.info("proxy {}:{} remove storageinstance ".format(proxy_obj.machine, proxy_obj.port))

    except Exception as e:  # NOCC:broad-except(检查工具误报)
        logger.error(traceback.format_exc())
        raise e
