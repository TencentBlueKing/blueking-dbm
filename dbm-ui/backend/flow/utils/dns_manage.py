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

from backend.components import CCApi, GcsDnsApi
from backend.db_meta.enums import ClusterEntryRole, ClusterEntryType
from backend.db_meta.models import Cluster, ClusterEntry

logger = logging.getLogger("flow")


class DnsManage(object):
    """
    定义dns域名管理类
    目前服务部署模式：每个云区域都有专属的dns服务，需要云区域id来识别操作哪一套dns服务
    """

    def __init__(self, bk_biz_id: int, bk_cloud_id: int):
        """
        @param bk_biz_id: 业务id
        @param bk_cloud_id: 云区域id ，作为跨云管理的依据
        """
        self.bk_biz_id = bk_biz_id
        self.bk_cloud_id = bk_cloud_id

    def __get_app_name(self) -> str:
        """
        根据bk_biz_id 来获取业务名称（可能后续不需要）
        """
        res = CCApi.search_business(
            {
                "fields": ["bk_biz_id", "db_app_abbr"],
                "biz_property_filter": {
                    "condition": "AND",
                    "rules": [{"field": "bk_biz_id", "operator": "equal", "value": self.bk_biz_id}],
                },
            }
        )

        if res["count"] != 1:
            raise Exception(f"{res['count']} app found in cc by bk_biz_id: {self.bk_biz_id}")

        return res["info"][0]["db_app_abbr"]

    def create_domain(self, instance_list: list, add_domain_name: str) -> bool:
        """
        创建域名
        @param instance_list: list格式，每个元素的字符串格式为：ip#port
        @param add_domain_name: str 格式，待加入的域名信息
        """
        create_domain_payload = [
            {
                "domain_name": f"{add_domain_name}.",
                "instances": instance_list,
            }
        ]
        GcsDnsApi.create_domain(
            {"app": str(self.bk_biz_id), "domains": create_domain_payload, "bk_cloud_id": self.bk_cloud_id}
        )
        return True

    def delete_domain(self, cluster_id: int, is_only_delete_slave_domain: bool) -> bool:
        """
        删除域名， 删除域名的方式是传入的集群id(cluster_id) ，清理db-meta注册的域名信息, 适用场景：集群回收
        @param cluster_id : 集群id
        """

        # ClusterEntry表查询出所有dns类型的访问方式
        cluster = Cluster.objects.get(id=cluster_id)
        if is_only_delete_slave_domain:
            dns_info = ClusterEntry.objects.filter(
                cluster=cluster, cluster_entry_type=ClusterEntryType.DNS, role=ClusterEntryRole.SLAVE_ENTRY.value
            ).all()
        else:
            dns_info = ClusterEntry.objects.filter(cluster=cluster, cluster_entry_type=ClusterEntryType.DNS).all()
        for d in dns_info:
            delete_domain_payload = [{"domain_name": f"{d.entry}."}]
            logger.info(d.entry)
            res = GcsDnsApi.delete_domain(
                {"app": str(self.bk_biz_id), "domains": delete_domain_payload, "bk_cloud_id": self.bk_cloud_id}
            )
            logger.info(res)

        return True

    def recycle_domain_record(self, del_instance_list: list) -> bool:
        """
        清理域名映射记录， 根据ip#port 信息，回收对应的记录, 适用场景：实例下架同时回收某个映射记录
        @param del_instance_list: 实例信息，每个元素的格式是ip#port
        """
        # 默认认为回收域名的实例所属机器都在同一云区域下
        delete_domain_payload = [{"instances": del_instance_list}]
        res = GcsDnsApi.delete_domain(
            {"app": str(self.bk_biz_id), "domains": delete_domain_payload, "bk_cloud_id": self.bk_cloud_id}
        )
        logger.info(res)

        return True

    def update_domain(self, old_instance: str, new_instance: str, update_domain_name: str) -> bool:
        """
        更新域名，根据传入的域名修改映射关系
        @param old_instance : 目前的instance映射，字符串格式：ip#port
        @param new_instance : 新的instance映射，字符串格式：ip#port
        @param update_domain_name : 更改映射的域名名称
        """
        # TODO: 这个接口需要del_instance_list(或者其他方式)传入bk_cloud_id
        GcsDnsApi.update_domain(
            {
                "app": str(self.bk_biz_id),
                "domain_name": f"{update_domain_name}.",
                "instance": f"{old_instance}",
                "set": {"instance": f"{new_instance}"},
                "bk_cloud_id": self.bk_cloud_id,
            }
        )
        return True

    def get_domain(self, get_domain_name: str) -> list:
        """
        根据域名信息查询映射关系
        todo 功能尚未完善
        """
        res = GcsDnsApi.get_domain(
            {
                "app": str(self.bk_biz_id),
                "domain_name": f"{get_domain_name}.",
                "bk_cloud_id": self.bk_cloud_id,
            }
        )
        return res["detail"]

    def remove_domain_ip(self, domain: str, del_instance_list: list) -> bool:
        delete_domain_payload = [{"domain_name": f"{domain}.", "instances": del_instance_list}]
        res = GcsDnsApi.delete_domain(
            {"app": str(self.bk_biz_id), "domains": delete_domain_payload, "bk_cloud_id": self.bk_cloud_id}
        )
        logger.info(res)

        return True

    def batch_update_domain(
        self,
        old_instance_list: list,
        new_instance_list: list,
        update_domain_name: str,
    ) -> bool:
        """
        批量更新域名，根据传入的域名修改映射关系
        @param old_instance_list: list格式，每个元素的字符串格式为：ip#port
        @param new_instance_list: list格式，每个元素的字符串格式为：ip#port
        @param update_domain_name : 更改映射的域名名称
        """
        sets = []
        for i, old_instance in enumerate(old_instance_list):
            new_instance = new_instance_list[i]
            sets.append(
                {
                    "old_instance": f"{old_instance}",
                    "new_instance": f"{new_instance}",
                }
            )
        GcsDnsApi.batch_update_domain(
            {
                "app": str(self.bk_biz_id),
                "domain_name": f"{update_domain_name}.",
                "set": sets,
                "bk_cloud_id": self.bk_cloud_id,
            }
        )
        return True
