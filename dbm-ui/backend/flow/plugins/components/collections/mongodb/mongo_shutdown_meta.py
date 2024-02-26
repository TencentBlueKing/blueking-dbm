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
from collections import defaultdict
from typing import Dict, List

from django.db import transaction
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend.configuration.constants import DBType
from backend.db_meta.api import common
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.cc_manage import CcManage

logger = logging.getLogger("root")


class MongosShutdownMetaService(BaseService):
    """
    集群 元数据下架
      # 该元数据操作包含 :  1.下架, 2.CC信息维护
    {
      "created_by":"xxxx",
      "immute_domain":"xxx", # 可选
      "cluster_id":1111,  # 必须的
      "bk_biz_id":0
    }
    """

    @transaction.atomic
    def decommission_proxies(self, cluster: Cluster, proxies: List[Dict]):
        logger.info("user request decmmission proxies {} {}".format(cluster.immute_domain, proxies))
        try:
            proxy_objs = common.filter_out_instance_obj(proxies, cluster.proxyinstance_set.all())
            _t = common.not_exists(proxies, proxy_objs)
            if _t:
                raise Exception("{} 存在不是本集群的实例下架列表".format(_t))

            machine_obj, cc_manage = defaultdict(dict), CcManage(cluster.bk_biz_id)
            cc_manage.delete_service_instance(bk_instance_ids=[obj.bk_instance_id for obj in proxy_objs])
            for proxy_obj in proxy_objs:
                logger.info("cluster proxy {} for cluster {}".format(proxy_obj, cluster.immute_domain))
                cluster.proxyinstance_set.remove(proxy_obj)

                logger.info(
                    "proxy storage {} for {} storageinstance {}".format(
                        proxy_obj, cluster.immute_domain, proxy_obj.storageinstance.all()
                    )
                )
                proxy_obj.storageinstance.clear()

                logger.info(
                    "proxy bind {} for {} cluster_bind_entry {}".format(
                        proxy_obj, cluster.immute_domain, proxy_obj.bind_entry.all()
                    )
                )
                proxy_obj.bind_entry.clear()

                logger.info("proxy instance {} ".format(proxy_obj))
                proxy_obj.delete()

                machine_obj[proxy_obj.machine.ip] = proxy_obj.machine

                # 需要检查， 是否该机器上所有实例都已经清理干净，
                if ProxyInstance.objects.filter(machine__ip=proxy_obj.machine.ip).exists():
                    logger.info("ignore storage machine {} , another instance existed.".format(proxy_obj.machine))
                else:
                    logger.info("proxy machine {}".format(proxy_obj.machine))
                    cc_manage.recycle_host([proxy_obj.machine.bk_host_id])
                    proxy_obj.machine.delete()
        except Exception as e:
            logger.error(traceback.format_exc())
            raise e

    @transaction.atomic
    def decommission_backends(self, cluster: Cluster, backends: List[Dict]):
        logger.info("user request decmmission backends {} {}".format(cluster.immute_domain, backends))
        cc_manage = CcManage(cluster.bk_biz_id)
        try:
            storage_objs = common.filter_out_instance_obj(backends, cluster.storageinstance_set.all())
            _t = common.not_exists(backends, storage_objs)
            if _t:
                raise Exception("{} not match".format(_t))

            cc_manage.delete_service_instance(bk_instance_ids=[obj.bk_instance_id for obj in storage_objs])
            machines = []
            for storage_obj in storage_objs:
                logger.info("cluster storage instance {} for cluster {}".format(storage_obj, cluster.immute_domain))
                cluster.storageinstance_set.remove(storage_obj)

                machines.append(storage_obj.machine)
                logger.info("remove storage instance {} ".format(storage_obj))
                storage_obj.delete()

            # 需要检查， 是否该机器上所有实例都已经清理干净，
            for machine in machines:
                if StorageInstance.objects.filter(machine__ip=machine.ip).exists():
                    logger.info("ignore storage machine {} , another instance existed.".format(machine))
                else:
                    logger.info("storage machine {} ".format(machine))
                    cc_manage.recycle_host([machine.bk_host_id])
                    machine.delete()
        except Exception as e:
            logger.error(traceback.format_exc())
            raise e

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")

        try:
            cluster = Cluster.objects.get(bk_biz_id=kwargs["bk_biz_id"], id=kwargs["cluster_id"])
            logger.info("user request decmmission cluster {}".format(cluster.immute_domain))
            if cluster.cluster_type not in (ClusterType.MongoReplicaSet.value):
                proxies = [
                    {"ip": proxy_obj.machine.ip, "port": proxy_obj.port}
                    for proxy_obj in cluster.proxyinstance_set.all()
                ]
                self.decommission_proxies(cluster, proxies)
            storages = [
                {"ip": storage_obj.machine.ip, "port": storage_obj.port}
                for storage_obj in cluster.storageinstance_set.all()
            ]
            self.decommission_backends(cluster, storages)
            # 解除自关联关系
            if cluster.clusterentry_set.filter(forward_to_id__isnull=False).exists():
                for cluster_entry_obj in cluster.clusterentry_set.filter(forward_to_id__isnull=False).all():
                    cluster_entry_obj.forward_to_id = None
                    cluster_entry_obj.save()
            for cluster_entry_obj in cluster.clusterentry_set.all():
                logger.info("cluster entry {} for cluster {}".format(cluster_entry_obj, cluster.immute_domain))
                cluster_entry_obj.delete()
            logger.info("cluster detail {}".format(cluster.__dict__))

            CcManage(cluster.bk_biz_id).delete_cluster_modules(db_type=DBType.MongoDB.value, cluster=cluster)
            cluster.delete()
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error("cluster shutdown 4 meta fail, {}error:{}".format(kwargs, str(e)))
            return False
        logger.info("cluster shutdown 4 meta successfully {}".format(kwargs))
        return True

    # 流程节点输入参数
    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class MongosShutdownMetaComponent(Component):
    """
    MongoShardCluster 、MongoReplicateSet 元数据下架
    """

    name = __name__
    code = "mongos_shutdown_meta"
    bound_service = MongosShutdownMetaService
