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
from typing import List

from backend.components import CCApi, DnsApi
from backend.db_meta.enums import ClusterEntryRole, ClusterEntryType
from backend.db_meta.models import Cluster, ClusterEntry
from backend.dbm_init.constants import CC_APP_ABBR_ATTR

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

    @staticmethod
    def format_domain(domain_name: str) -> str:
        """
        保证域名的格式为，保留最后一个英文句号 "."
        """
        if domain_name.endswith("."):
            return domain_name
        else:
            return f"{domain_name}."

    def create_domain(self, instance_list: list, add_domain_name: str) -> bool:
        """
        创建域名
        @param instance_list: list格式，每个元素的字符串格式为：ip#port
        @param add_domain_name: str 格式，待加入的域名信息
        """
        create_domain_payload = [
            {
                "domain_name": self.format_domain(add_domain_name),
                "instances": instance_list,
            }
        ]
        DnsApi.create_domain(
            {"app": str(self.bk_biz_id), "domains": create_domain_payload, "bk_cloud_id": self.bk_cloud_id}
        )
        return True

    def delete_domain(self, cluster_id: int, is_only_delete_slave_domain=False) -> bool:
        """
        删除域名， 删除域名的方式是传入的集群id(cluster_id) ，清理db-meta注册的域名信息, 适用场景：集群回收
        @param cluster_id : 集群id
        @param is_only_delete_slave_domain : 是否只删除从域名
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
            delete_domain_payload = [{"domain_name": self.format_domain(d.entry)}]
            logger.info(d.entry)
            res = DnsApi.delete_domain(
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
        res = DnsApi.delete_domain(
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
        DnsApi.update_domain(
            {
                "app": str(self.bk_biz_id),
                "domain_name": self.format_domain(update_domain_name),
                "instance": f"{old_instance}",
                "set": {"instance": f"{new_instance}"},
                "bk_cloud_id": self.bk_cloud_id,
            }
        )
        return True

    def get_domain(self, domain_name: str) -> list:
        """
        根据域名信息查询映射关系
        """
        res = DnsApi.get_domain(
            {
                "app": str(self.bk_biz_id),
                "domain_name": self.format_domain(domain_name),
                "bk_cloud_id": self.bk_cloud_id,
            }
        )
        return res["detail"]

    def remove_domain_ip(self, domain: str, del_instance_list: list) -> bool:
        delete_domain_payload = [{"domain_name": self.format_domain(domain), "instances": del_instance_list}]
        res = DnsApi.delete_domain(
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
        DnsApi.batch_update_domain(
            {
                "app": str(self.bk_biz_id),
                "domain_name": self.format_domain(update_domain_name),
                "set": sets,
                "bk_cloud_id": self.bk_cloud_id,
            }
        )
        return True

    def refresh_cluster_domain(self, domain_name: str, target_instance_list: List[str]):
        """
        刷新 DNS，数据以 DNS API 为准
        """
        domain_details = self.get_domain(domain_name)
        old_instance_list = []
        for domain in domain_details:
            instance = f'{domain["ip"]}#{domain["port"]}'
            old_instance_list.append(instance)
            # 不在新目标实例中的映射，需要删除
            if instance not in target_instance_list:
                self.remove_domain_ip(domain_name, [instance])
        # 差集需要新增映射（新实例不在旧实例中）
        new_instance_list = list(set(target_instance_list) - set(old_instance_list))
        self.create_domain(instance_list=new_instance_list, add_domain_name=domain_name)
