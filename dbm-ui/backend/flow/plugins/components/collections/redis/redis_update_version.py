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
import logging
from typing import List

from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend.db_meta.enums import InstanceStatus
from backend.db_meta.models import Cluster
from backend.db_services.redis.util import is_predixy_proxy_type, is_twemproxy_proxy_type
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.base.payload_handler import PayloadHandler
from backend.flow.utils.redis.redis_proxy_util import (
    get_online_predixy_version,
    get_online_redis_version,
    get_online_twemproxy_version,
)

logger = logging.getLogger("flow")


class RedisUpdateVersionService(BaseService):
    """
    更新 instance version :
    {
        "cluster_id":1111, /或者传： domain_name
        "bk_bzi_id":000,
        "update_all":True,
        "update_proxy":True,
        "update_storage":False,
    }
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")

        update_args = copy.deepcopy(kwargs["cluster"])

        if update_args.get("cluster_id", None) is not None:
            cluster = Cluster.objects.get(bk_biz_id=update_args["bk_biz_id"], id=update_args["cluster_id"])
        else:  # 新集群部署时 ， 还没有ClusterID
            cluster = Cluster.objects.get(bk_biz_id=update_args["bk_biz_id"], immute_domain=update_args["domain_name"])

        if update_args.get("update_proxy", False) or update_args.get("update_all", False):
            self.update_proxy_instance(cluster)
        if update_args.get("update_storage", False) or update_args.get("update_all", False):
            self.update_storage_instance(cluster)

        self.log_info("cluster [{}] all instance version updated successfully:".format(cluster.immute_domain))
        return True

    def update_proxy_instance(self, cluster: Cluster):
        passwd_ret = PayloadHandler.redis_get_password_by_cluster_id(cluster.id)
        for proxy in cluster.proxyinstance_set.filter(status=InstanceStatus.RUNNING):
            if is_predixy_proxy_type(cluster.cluster_type):
                v = get_online_predixy_version(
                    proxy.machine.ip, proxy.port, cluster.bk_cloud_id, passwd_ret.get("redis_proxy_password")
                )
                proxy.version = v
            elif is_twemproxy_proxy_type(cluster.cluster_type):
                v = get_online_twemproxy_version(proxy.machine.ip, proxy.port, cluster.bk_cloud_id)
                proxy.version = v
            proxy.save(update_fields=["version"])
        self.log_info("cluster [{}] proxy version updated successfully:".format(cluster.immute_domain))

    def update_storage_instance(self, cluster: Cluster):
        passwd_ret = PayloadHandler.redis_get_password_by_cluster_id(cluster.id)
        for storage in cluster.storageinstance_set.filter(status=InstanceStatus.RUNNING):
            v = get_online_redis_version(
                storage.machine.ip, storage.port, cluster.bk_cloud_id, passwd_ret.get("redis_password")
            )
            storage.version = v
            storage.save(update_fields=["version"])
        self.log_info("cluster [{}] storage version updated successfully:".format(cluster.immute_domain))

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class RedisUpdateVersionComponent(Component):
    name = __name__
    code = "redis_update_version"
    bound_service = RedisUpdateVersionService
