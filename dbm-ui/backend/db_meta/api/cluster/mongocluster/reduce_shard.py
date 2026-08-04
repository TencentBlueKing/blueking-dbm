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
from typing import List, Optional

from django.db import transaction
from django.utils.translation import gettext as _

from backend.constants import DEFAULT_BK_CLOUD_ID
from backend.db_meta import request_validator
from backend.db_meta.models import Cluster, StorageInstance, StorageInstanceTuple
from backend.flow.utils.cc_manage import CcManage

logger = logging.getLogger("flow")


@transaction.atomic
def cluster_reduce_shard(
    bk_biz_id: int,
    cluster_id: int,
    storages: Optional[List] = None,
    creator: str = "",
    bk_cloud_id: int = DEFAULT_BK_CLOUD_ID,
):
    """
    分片集群减少分片：摘除 StorageInstance / nosqlstoragesetdtl / CC。

    Args:
        storages: [{"shard":"S1","nodes":[{"ip":,"port":},{},{}]},]
    """

    bk_biz_id = request_validator.validated_integer(bk_biz_id)
    storages = storages or []
    if not storages:
        raise ValueError(_("storages can not be empty"))

    try:
        cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)
    except Cluster.DoesNotExist as err:
        raise Exception(_("cluster {} not found").format(cluster_id)) from err

    cc_manage = CcManage(cluster.bk_biz_id, cluster.cluster_type)

    try:
        for storage in storages:
            shard_name = storage["shard"]
            nodes = storage.get("nodes") or []
            if not nodes:
                raise ValueError(_("shard {} nodes can not be empty").format(shard_name))

            # 删除分片映射
            deleted, _unused = cluster.nosqlstoragesetdtl_set.filter(seg_range=shard_name).delete()
            logger.info(
                "cluster {} delete nosqlstoragesetdtl shard={} count={} creator={}".format(
                    cluster.immute_domain, shard_name, deleted, creator
                )
            )

            storage_objs = []
            for node in nodes:
                try:
                    obj = cluster.storageinstance_set.get(
                        machine__ip=node["ip"],
                        port=node["port"],
                        machine__bk_cloud_id=bk_cloud_id,
                    )
                except StorageInstance.DoesNotExist as err:
                    raise Exception(
                        _("instance {}:{} not in cluster {}").format(node["ip"], node["port"], cluster.immute_domain)
                    ) from err
                storage_objs.append(obj)

            machines = []
            seen_host_ids = set()
            for storage_obj in storage_objs:
                logger.info(
                    "cluster {} remove storage {} for shard {}".format(cluster.immute_domain, storage_obj, shard_name)
                )
                storage_obj.proxyinstance_set.clear()
                for bind_entry in list(storage_obj.bind_entry.all()):
                    storage_obj.bind_entry.remove(bind_entry)
                StorageInstanceTuple.objects.filter(ejector=storage_obj).delete()
                StorageInstanceTuple.objects.filter(receiver=storage_obj).delete()
                cluster.storageinstance_set.remove(storage_obj)
                if storage_obj.machine.bk_host_id not in seen_host_ids:
                    machines.append(storage_obj.machine)
                    seen_host_ids.add(storage_obj.machine.bk_host_id)
                if storage_obj.bk_instance_id:
                    cc_manage.delete_service_instance(bk_instance_ids=[storage_obj.bk_instance_id])
                storage_obj.delete()

            for machine in machines:
                if StorageInstance.objects.filter(
                    machine__ip=machine.ip,
                    bk_biz_id=cluster.bk_biz_id,
                    machine__bk_cloud_id=cluster.bk_cloud_id,
                ).exists():
                    logger.info("ignore recycle machine {}, another instance existed.".format(machine))
                else:
                    logger.info("storage recycle machine {}".format(machine))
                    cc_manage.recycle_host([machine.bk_host_id])
                    machine.delete()
    except Exception as e:  # NOCC:broad-except(检查工具误报)
        logger.error(traceback.format_exc())
        raise Exception("mongocluster reduce shard failed {}".format(e)) from e
