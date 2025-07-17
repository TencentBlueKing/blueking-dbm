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

from backend.db_meta.models import Cluster, StorageInstance

logger = logging.getLogger("root")


def oracle_delete_cluster(bk_biz_id: int, cluster_id: int):
    """oracle删除集群元数据"""

    try:
        cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=cluster_id)
        # cc_manage = CcManage(cluster.bk_biz_id, cluster.cluster_type)
        logger.info("user request delete cluster {}".format(cluster.immute_domain))
        # 删除服务实例
        # cc_manage.delete_service_instance(
        # bk_instance_ids=[obj.bk_instance_id for obj in cluster.storageinstance_set.all()])
        # 删除storage实例
        machines = []
        for storage_obj in cluster.storageinstance_set.all():
            logger.info("cluster storage instance {} for cluster {}".format(storage_obj, cluster.immute_domain))
            cluster.storageinstance_set.remove(storage_obj)
            machines.append(storage_obj.machine)
            logger.info("remove storage instance {} ".format(storage_obj))
            storage_obj.delete()
        # 删除machine
        for machine in machines:
            if StorageInstance.objects.filter(
                machine__ip=machine.ip, bk_biz_id=cluster.bk_biz_id, machine__bk_cloud_id=cluster.bk_cloud_id
            ).exists():
                logger.info("ignore storage machine {} , another instance existed.".format(machine))
            else:
                logger.info("storage machine {} ".format(machine))
                machine.delete()
        # 解除自关联关系
        if cluster.clusterentry_set.filter(forward_to_id__isnull=False).exists():
            for cluster_entry_obj in cluster.clusterentry_set.filter(forward_to_id__isnull=False).all():
                cluster_entry_obj.forward_to_id = None
                cluster_entry_obj.save()
        for cluster_entry_obj in cluster.clusterentry_set.all():
            logger.info("cluster entry {} for cluster {}".format(cluster_entry_obj, cluster.immute_domain))
            cluster_entry_obj.delete()
        logger.info("cluster detail {}".format(cluster.__dict__))

        # CcManage(cluster.bk_biz_id, cluster.cluster_type).delete_cluster_modules(
        #     db_type=DBType.MongoDB.value, cluster=cluster
        # )
        # 删除 cluster
        cluster.delete()
    except Exception as e:
        logger.error(traceback.format_exc())
        logger.error("delete oracle cluster:{} meta fail, error:{}".format(str(cluster_id), str(e)))
    logger.info("delete oracle cluster:{} meta successfully".format(str(cluster_id)))
