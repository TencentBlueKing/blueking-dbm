"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from collections import defaultdict

from django.utils.translation import ugettext as _

from backend.db_meta.enums import AccessLayer
from backend.db_meta.models import Cluster
from backend.flow.consts import MIN_TENDB_PROXY_COUNT_IN_TICKET
from backend.flow.engine.bamboo.scene.mysql.validate.exception import ProxyReduceCountFailedException
from backend.flow.engine.validate.base_validate import validator_log_format
from backend.flow.engine.validate.exceptions import DuplicateIPException, TicketDataException
from backend.flow.engine.validate.mysql_base_validate import MysqlBaseValidator


class MySQLProxyClusterReduceFlowValidator(MysqlBaseValidator):
    """
    MySQLProxyClusterReduceFlow类对应的validate类
    判断传入flow的data参数合法性
    每行校验：
    检验1：传入集群、ip、proxy角色所属集群的基础信息合法性
    校验2：同一个flow, 同一主机，所关联集群信息是否有传全
    聚合校验：
    检验3：同一个flow，同一个集群，传入机器不能重复
    检验4：同一个flow，同一个集群，缩容后proxy节点不能少于2台
    校验5：同一个flow，同一个集群，缩容后如果proxy节点，要需要符合集群高可用特性
    """

    def __calc_reduce_ips_based_on_cluster(self):
        """
        根据传入结构，计算每个集群这次卸载的IP信息
        """
        cluster_reduced_ips = defaultdict(set)
        # 一次性遍历所有集群的这次缩容的proxy数量
        for info in self.data["infos"]:
            try:
                for cluster_id in info["cluster_ids"]:
                    cluster_reduced_ips[cluster_id].add(info["origin_proxy_ip"]["ip"])
            except KeyError as err:
                # 跳过缺少cluster_ids的key
                raise TicketDataException(f"run func [__calc_reduce_ips_based_on_cluster] failed:{err}")

        return cluster_reduced_ips

    @classmethod
    @validator_log_format
    def pre_check_ip_clusters_included(cls, ip: str, bk_cloud_id: int, cluster_ids: list, access_layer: AccessLayer):
        return super().pre_check_ip_clusters_included(ip, bk_cloud_id, cluster_ids, access_layer)

    def pre_check_remaining_proxy(self):
        """
        这里根据集群维度，检查缩容后剩余proxy的一些项。目前检查2项:
        1: 缩容后 running状态的 proxy节点不能少于2台
        2：缩容后如果proxy节点，要需要符合集群高可用特性
        """

        # 一次性遍历所有集群的这次缩容的proxy数量
        cluster_reduced_ips = self.__calc_reduce_ips_based_on_cluster()

        err_msg = ""
        for cluster_id, ips in cluster_reduced_ips.items():
            cluster = Cluster.objects.get(id=int(cluster_id))
            remaining_proxy = cluster.proxyinstance_set.exclude(machine__ip__in=list(ips))

            # 缩容后proxy节点数不能少于2
            if remaining_proxy.count() < MIN_TENDB_PROXY_COUNT_IN_TICKET:
                err_msg += _(
                    "集群[{}]缩容后proxy节点数量不能少于{}，请检查 \n".format(cluster.immute_domain, MIN_TENDB_PROXY_COUNT_IN_TICKET)
                )
                continue

            # 缩容后如果proxy数量还剩下两个以上，需要符合集群高可用特性
            check_hosts = [
                {"ip": i.machine.ip, "sub_zone_id": i.machine.bk_sub_zone_id, "rack_id": i.machine.bk_rack_id}
                for i in remaining_proxy
            ]
            if not self.check_disaster_tolerance_level(cluster=cluster, hosts=check_hosts):
                err_msg += _(
                    "[{}]集群剩余spider节点不满足容灾要求[{}]，请检查，剩余的节点信息:{}".format(
                        cluster.immute_domain, cluster.disaster_tolerance_level, check_hosts
                    )
                )
                continue

        return err_msg

    def __run_check_for_info(self, info: dict, index: int) -> list:
        """
        @param info：  self.data["infos"]每个元素体
        @param index： 每个元素体的编号
        """
        row_key = info.get("row_key", "")

        # 检查每一行ip传入是否合法
        log_format_tag = self.create_log_tag(field="origin_proxy_ip", index=index, row_key=row_key)
        error_msg = self.pre_check_ip([info["origin_proxy_ip"]["ip"]], **log_format_tag)
        if error_msg:
            return [error_msg]

        # 检查每一行集群是否存在
        log_format_tag = self.create_log_tag(field="cluster_ids", index=index, row_key=row_key)
        error_msg = self.pre_check_cluster_exist(info["cluster_ids"], **log_format_tag)
        if error_msg:
            return [error_msg]

        # 检查每一行传入的ip和集群信息，是否是所属关系
        log_format_tag = self.create_log_tag(field="origin_proxy_ip", index=index, row_key=row_key)
        error_msg = self.pre_check_mysql_proxy_in_cluster(
            [info["origin_proxy_ip"]["ip"]], info["cluster_ids"], **log_format_tag
        )
        if error_msg:
            return [error_msg]

        # 检查每一行的ip的所属集群信息是否传全
        log_format_tag = self.create_log_tag(field="origin_proxy_ip", index=index, row_key=row_key)
        error_msg = self.pre_check_ip_clusters_included(
            ip=info["origin_proxy_ip"]["ip"],
            bk_cloud_id=int(info["origin_proxy_ip"]["bk_cloud_id"]),
            cluster_ids=info["cluster_ids"],
            access_layer=AccessLayer.PROXY,
            **log_format_tag,
        )
        if error_msg:
            return [error_msg]

        return []

    def __call__(self):
        # 阶段1 检测每个行的数据合法性
        error_msgs = []
        for index, info in enumerate(self.data["infos"]):
            error_msgs += self.__run_check_for_info(info, index)
        if error_msgs:
            return error_msgs

        # 阶段2 做聚合校验
        # 同一个flow，同一个集群，传入机器不能重复
        err = self.pre_check_duplicate_ip("origin_proxy_ip")
        if err:
            raise DuplicateIPException(err)

        # 同一个flow，同一个集群，缩容后proxy节点不能少于2台
        # 同一个flow，同一个集群，缩容后如果proxy数量还剩下两个以上，需要符合集群高可用特性
        err = self.pre_check_remaining_proxy()
        if err:
            raise ProxyReduceCountFailedException(err)

        return None
