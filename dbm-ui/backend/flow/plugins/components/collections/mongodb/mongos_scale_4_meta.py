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
import logging.config
import traceback
from typing import Dict, List

from django.db import transaction
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend.db_meta import api
from backend.db_meta.api import common
from backend.db_meta.enums import (
    AccessLayer,
    ClusterMachineAccessTypeDefine,
    ClusterType,
    InstanceInnerRole,
    InstanceStatus,
    MachineType,
)
from backend.db_meta.models import Cluster, ProxyInstance
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.mongodb.mongodb_module_operate import MongoDBCCTopoOperator

logger = logging.getLogger("root")


class MongosScaleMetaService(BaseService):
    """
    # ShardCluster mongos       扩缩容
    #### 操作包含 (元数据): 1.安装, 2.添加到集群, 3.下架, 4.CC信息维护
    {
      "created_by":"xxxx",
      "immute_domain":"xxx", # 可选
      "cluster_id":1111,  # 必须的
      "bk_biz_id":0,
      "mongos_add":[
                {"ip": "a.b.c.d","spec_id": 1,"spec_config":{}}
      ],
      "mongos_del": [
                {"ip": "c.b.c.d","spec_id": 1,"spec_config":{}}
            ]
    }
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")

        try:
            mongo_cluster = Cluster.objects.get(bk_biz_id=kwargs["bk_biz_id"], id=kwargs["cluster_id"])
            if mongo_cluster.cluster_type != ClusterType.MongoShardedCluster.value or (
                not kwargs.get("mongos_add") and not kwargs.get("mongos_del")
            ):
                raise Exception(
                    "must input 'mongos_add/mongos_del' or must be shardCluster {}:{}=>{}".format(
                        mongo_cluster.immute_domain, mongo_cluster.cluster_type, kwargs
                    )
                )

            mongos_ports = set(obj.port for obj in mongo_cluster.proxyinstance_set.all())

            # 扩容 Mongos 节点
            if kwargs.get("mongos_add"):
                logger.info(
                    "scale out mongos 4 cluster {} mongos : {} ".format(
                        mongo_cluster.immute_domain, kwargs.get("mongos_add")
                    )
                )
                self.mongos_scale_out_scene(
                    mongo_cluster, kwargs.get("mongos_add"), mongos_ports, kwargs.get("created_by")
                )

            # 缩容 Mongos 节点
            if kwargs.get("mongos_del"):
                logger.info(
                    "scale in mongos 4 cluster {} mongos : {} ".format(
                        mongo_cluster.immute_domain, kwargs.get("mongos_del")
                    )
                )
                old_proxies = []
                for mongos in kwargs.get("mongos_del"):
                    old_proxies.extend([{"ip": mongos["ip"], "port": port} for port in mongos_ports])
                # # 删除老 mongos
                api.cluster.nosqlcomm.decommission_proxies(mongo_cluster, proxies=old_proxies, is_all=False)

        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error("scale mongos 4 cluster 4 meta fail, {}error:{}".format(kwargs, str(e)))
            return False
        logger.info("scale mongos 4 cluster 4 meta successfully {}".format(kwargs))
        return True

    # mongos(proxy) 扩容
    @transaction.atomic
    def mongos_scale_out_scene(self, cluster: Cluster, mongos_info, mongos_ports, created_by):
        machines, proxies = [
            {
                "bk_biz_id": cluster.bk_biz_id,
                "ip": mongos["ip"],
                "machine_type": MachineType.MONGOS.value,
                "spec_id": mongos["spec_id"],
                "spec_config": mongos["spec_config"],
            }
            for mongos in mongos_info
        ], []
        for mongos in mongos_info:
            proxies.extend([{"ip": mongos["ip"], "port": port} for port in mongos_ports])

        # 创建实例
        api.machine.create(machines=machines, bk_cloud_id=cluster.bk_cloud_id, creator=created_by)
        api.proxy_instance.create(proxies=proxies, status=InstanceStatus.RUNNING.value, creator=created_by)

        # 新增 mongos 到集群
        self.add_proxies(cluster, proxies)
        MongoDBCCTopoOperator(cluster).transfer_instances_to_cluster_module(proxies)

    # mongos(proxy) 添加到集群
    @transaction.atomic
    def add_proxies(self, cluster: Cluster, proxies: List[Dict]):
        """
        1. 不能已添加
        2. 不能归属于其他集群
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
            MongoDBCCTopoOperator(cluster).transfer_instances_to_cluster_module(proxy_objs)
        except Exception as e:  # NOCC:broad-except(检查工具误报)
            logger.error(traceback.format_exc())
            raise e

    # 流程节点输入参数
    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class MongosScaleMetaComponent(Component):
    """
    ShardCluster Mongos 扩缩容组件
    """

    name = __name__
    code = "mongos_scale_meta"
    bound_service = MongosScaleMetaService
