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

from backend.db_meta.enums import ClusterEntryType
from backend.db_meta.exceptions import InstanceNotExistException
from backend.db_meta.models import Cluster, ClusterEntry, ProxyInstance, StorageInstance
from backend.db_services.dbbase.resources.query import ListRetrieveResource
from backend.flow.utils.dns_manage import DnsManage

logger = logging.getLogger("root")


class ClusterEntryHandler:
    def __init__(self, cluster_id):
        self.cluster_id = cluster_id
        self.cluster = Cluster.objects.get(id=self.cluster_id)

    def refresh_cluster_domain(self, cluster_entry_details):
        for detail in cluster_entry_details:
            # 修改 DNS 记录
            cluster_entry_ins_map = {}
            if detail["cluster_entry_type"] == ClusterEntryType.DNS:
                cluster_entry = ClusterEntry.objects.get(
                    cluster__id=self.cluster_id,
                    cluster_entry_type=ClusterEntryType.DNS,
                    entry=detail["domain_name"],
                )
                if cluster_entry.id not in cluster_entry_ins_map:
                    cluster_entry_ins_map[cluster_entry.id] = {
                        "cluster_entry": cluster_entry,
                        "storage_instances": [],
                        "proxy_instances": [],
                    }
                # 修改实例与访问入口的绑定关系
                for target_instance in detail["target_instances"]:
                    ip, port = target_instance.split("#")
                    filter_condition = dict(machine__ip=ip, cluster=self.cluster)
                    storage_ins = StorageInstance.objects.filter(**filter_condition).first()
                    if storage_ins is None:
                        proxy_ins = ProxyInstance.objects.filter(**filter_condition).first()
                        if proxy_ins is None:
                            raise InstanceNotExistException(bk_cloud_id=self.cluster.bk_cloud_id, ip=ip, port=port)
                        else:
                            # 重新绑定代理实例
                            cluster_entry_ins_map[cluster_entry.id]["proxy_instances"].append(proxy_ins)
                    else:
                        # 重新绑定存储实例
                        cluster_entry_ins_map[cluster_entry.id]["storage_instances"].append(storage_ins)

                DnsManage(self.cluster.bk_biz_id, self.cluster.bk_cloud_id).refresh_cluster_domain(
                    detail["domain_name"], detail["target_instances"]
                )

            # 重新绑定实例
            for cluster_entry_info in cluster_entry_ins_map.values():
                cluster_entry = cluster_entry_info["cluster_entry"]
                # 清除并重新绑定实例
                if cluster_entry_info["proxy_instances"]:
                    cluster_entry.proxyinstance_set.set(cluster_entry_info["proxy_instances"])
                if cluster_entry_info["storage_instances"]:
                    cluster_entry.storageinstance_set.set(cluster_entry_info["storage_instances"])

    def get_cluster_entries(self, bk_biz_id, cluster_entry_type=None):

        extra = {"cluster_entry_type": cluster_entry_type} if cluster_entry_type else {}
        cluster_entries = ListRetrieveResource.query_cluster_entry_details(
            {
                "id": self.cluster.id,
                "bk_cloud_id": self.cluster.bk_cloud_id,
                "bk_biz_id": bk_biz_id,
            },
            **extra,
        )
        return cluster_entries
