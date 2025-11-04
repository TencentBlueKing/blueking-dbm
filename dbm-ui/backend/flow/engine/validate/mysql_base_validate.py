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
from typing import List, Set

from django.utils.translation import gettext as _

from backend.db_meta.enums import AccessLayer
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance
from backend.flow.engine.validate.base_validate import BaseValidator, validator_log_format
from backend.flow.engine.validate.exceptions import TicketDataException
from backend.flow.utils.spider.spider_bk_config import calc_spider_max_count, get_spider_version_and_charset


class MysqlBaseValidator(BaseValidator):
    """
    tenDB/tenDBCluster的基础校验类
    """

    @classmethod
    def pre_check_spider_master_count(
        cls, bk_biz_id: int, db_module_id: int, ready_to_add_count: int, existing_count: int, immute_domain: str
    ) -> (bool, int):
        """
        校验spider_master/mnt节点数量是否超过集群的设置上限
        @param bk_biz_id: 业务id
        @param db_module_id: db配置组id
        @param ready_to_add_count: 待加入的节点数量
        @param existing_count: 已经存在的节点数量
        @param immute_domain: 集群主域名信息, 默认是None，如果是None的情况下，则表示集群部署阶段检验，需要转化传 is_init = True
        """
        # 获取Spider版本号
        _, spider_version = get_spider_version_and_charset(bk_biz_id, db_module_id)
        upper_limit_count = calc_spider_max_count(
            bk_biz_id=bk_biz_id,
            db_module_id=db_module_id,
            db_version=spider_version,
            immute_domain=immute_domain,
        )

        if ready_to_add_count + existing_count > upper_limit_count:
            # 表示已经超过了设置的理论值上限
            return False, upper_limit_count

        return True, upper_limit_count

    def pre_check_spider_role_for_cluster(self, cluster_id_field_name: str, spider_role_field_name: str):
        """
        根据cluster维度聚合，计算这个单据需要的spider角色数量，如果大于2, 则记录异常
        @param cluster_id_field_name: 在info结构体获取集群ID的key名称
        @param spider_role_field_name: 在info结构体获取spider角色的key名称
        """
        id_roles = defaultdict(set)

        # 一次性遍历收集所有角色
        for info in self.data["infos"]:
            try:
                cluster_id = info[cluster_id_field_name]
                spider_role = info[spider_role_field_name]
                id_roles[cluster_id].add(spider_role)
            except KeyError as err:
                # 跳过缺少id或role的条目
                raise TicketDataException(f"run func [pre_check_spider_role_count_for_cluster] failed:{err}")

        # 找出大于1的set
        err_msg = ""
        for cluster_id, spider_roles in id_roles.items():
            if len(spider_roles) > 1:
                err_msg += _("在单据中，集群ID [{}] 出现两个以上的实例角色操作，请检查 \n".format(cluster_id))

        return err_msg

    def pre_check_duplicate_ip(self, check_ip_field_name: str):
        """
        检验是否有存在重复的ip信息，如果有则记录异常
        因为SaaS传给所有flow的ip信息都是固定格式，故可以做通用处理
        @param check_ip_field_name: 在info结构体获取ip的key名称
        """
        ip_counts = defaultdict(int)
        for info in self.data["infos"]:
            if isinstance(info[check_ip_field_name], list):
                for ip_info in info[check_ip_field_name]:
                    ip_counts[ip_info["ip"]] += 1
            elif isinstance(info[check_ip_field_name], dict):
                ip_counts[info[check_ip_field_name]["ip"]] += 1

            else:
                # 不是传入通用的ip表达方式，无法计算，退出异常
                raise TicketDataException(
                    f"run [pre_check_duplicate_ip] failed: No such type checking is supported:"
                    f"{info[check_ip_field_name]}"
                )

        # 找出统计数大于1的ip数量
        err_msg = ""
        for ip, count in ip_counts.items():
            if count > 1:
                err_msg += _("在单据中，存在重复IP信息填入 [{}]，请检查 \n".format(ip))

        return err_msg

    def pre_check_duplicate_cluster_ids(self, check_cluster_ids_field_name: str):
        """
        检验是否有存在重复的ip信息，如果有则记录异常
        因为SaaS传给所有flow的ip信息都是固定格式，故可以做通用处理
        @param check_cluster_ids_field_name: 在info结构体获取ip的key名称
        """
        cluster_id_counts = defaultdict(int)
        for info in self.data["infos"]:
            if isinstance(info[check_cluster_ids_field_name], list):
                for c_id in info[check_cluster_ids_field_name]:
                    cluster_id_counts[c_id] += 1
            elif isinstance(info[check_cluster_ids_field_name], int):
                cluster_id_counts[info[check_cluster_ids_field_name]] += 1

            else:
                # 不是传入通用的ip表达方式，无法计算，退出异常
                raise TicketDataException(
                    f"run [pre_check_duplicate_cluster_ids] failed: No such type checking is supported:"
                    f"{info[check_cluster_ids_field_name]}"
                )

        # 找出统计数大于1的ip数量
        err_msg = ""
        for cluster_id, count in cluster_id_counts.items():
            if count > 1:
                err_msg += _("在单据中，存在重复集群ID信息填入 [{}]，请检查 \n".format(cluster_id))

        return err_msg

    @classmethod
    @validator_log_format
    def pre_check_mysql_proxy_in_cluster(cls, ip_list: list, cluster_ids: List[int]):
        """
        检验单据中传入ip信息，检查ip在DBM系统里是否属于这个集群
        @param ip_list: 检验ip列表
        @param cluster_ids: 集群id列表
        """
        err_msg = ""
        for ip in ip_list:
            for cluster_id in cluster_ids:
                cluster = Cluster.objects.get(id=cluster_id)
                if not cluster.proxyinstance_set.filter(machine__ip=ip).exists():
                    err_msg += _("IP[{}]不属于该集群[{}]的proxy机器，请检查 \n".format(ip, cluster.immute_domain))

        return err_msg

    @classmethod
    def pre_check_ip_clusters_included(
        cls, ip: str, bk_cloud_id: int, cluster_ids: List[int], access_layer: AccessLayer
    ):
        """
        检验单据中传入ip信息，所属的集群是否和传入的cluster_ids一样
        @param ip: 待校验的ip信息
        @param bk_cloud_id: 待校验的云区域ID
        @param cluster_ids: 待校验的集群id列表
        @param access_layer: 待检测ip的接入类型，此方法只支持proxy和storage检验
        """
        if access_layer == AccessLayer.PROXY:
            real_cluster_ids = [
                p.cluster.get().id
                for p in ProxyInstance.objects.filter(machine__ip=ip, machine__bk_cloud_id=bk_cloud_id)
            ]

        elif access_layer == AccessLayer.STORAGE:
            real_cluster_ids = [
                p.cluster.get().id
                for p in StorageInstance.objects.filter(machine__ip=ip, machine__bk_cloud_id=bk_cloud_id)
            ]

        else:
            # 其余的不支持
            raise TicketDataException(f" No such access_layer [{access_layer}] type checking is supported")

        if sorted(real_cluster_ids) != sorted(cluster_ids):
            return _(
                "整机校验：IP[{}]传入的集群信息没有包括所有的关联的集群，请检查:  查到的cluster_ids:{}, 传入的cluster_ids：{}\n".format(
                    ip, real_cluster_ids, cluster_ids
                )
            )

        return ""

    @validator_log_format
    def pre_check_proxy_clusters_included(self, proxy_ip: str, bk_cloud_id: int, cluster_ids: List[int]):
        """
        判断proxy_ip和传入的cluster_ids的所属关系，是否已经完整
        @param proxy_ip: 待判断的proxy_ip
        @param bk_cloud_id: 带判断proxy_ip所在的云区域
        @param cluster_ids: 待判断的集群列表信息
        """
        return self.pre_check_ip_clusters_included(proxy_ip, bk_cloud_id, cluster_ids, AccessLayer.PROXY)

    @validator_log_format
    def pre_check_storage_clusters_included(self, storage_ip: str, bk_cloud_id: int, cluster_ids: List[int]):
        """
        判断storage_ip和传入的cluster_ids的所属关系，是否已经完整
        @param storage_ip: 待判断的storage_ip
        @param bk_cloud_id: 带判断proxy_ip所在的云区域
        @param cluster_ids: 待判断的集群列表信息
        """

        return self.pre_check_ip_clusters_included(storage_ip, bk_cloud_id, cluster_ids, AccessLayer.STORAGE)

    @classmethod
    def pre_check_same_group_relationship(
        cls, cluster_ids: List[int], access_layer: AccessLayer, check_is_all_in_group: bool = False
    ) -> str:
        """
        根据传入的集群ID列表，判断这些集群是否同组共享的，同时判断有没有别集群也是同组共享的，且没有传进来
        怎么定义集群才是同组共享：
        比如 集群ID 1,2，且两组集群的对应的proxy所有机器，都是完全一样，则认为proxy层是同组共享，否则不是
        @param cluster_ids: 待检测的集群ID列表
        @param access_layer: 待检测的接入类型，比如传入的是proxy，则只检测集群的proxy是否同组共享关系，以此类推
        @param check_is_all_in_group: 是否开启检查 cluster_ids的列表，已经是所有同组共享的集群列表，默认不开启
        """
        if len(cluster_ids) != len(set(cluster_ids)):
            # 这里判断传入的cluster_ids中，有元素重复，应该检查
            return _("传入的集群ID列表中，有元素重复，请检查[{}]".format(cluster_ids))

        first_cluster_ips_set = set()
        first_cluster = ""
        for cluster in Cluster.objects.filter(id__in=cluster_ids).prefetch_related(
            "storageinstance_set", "proxyinstance_set"
        ):

            if access_layer == AccessLayer.PROXY:
                ips = {i.machine.ip for i in cluster.proxyinstance_set.all()}

            elif access_layer == AccessLayer.STORAGE:
                ips = {i.machine.ip for i in cluster.storageinstance_set.all()}

            else:
                # 其余的不支持
                raise TicketDataException(f" No such access_layer [{access_layer}] type checking is supported")

            if not first_cluster_ips_set:
                first_cluster_ips_set = ips
                first_cluster = cluster.immute_domain
                continue

            if first_cluster_ips_set != ips:
                # 出现不一样的ip集合，则报出异常。
                return _(
                    "这批集群存在不属于同组共享特性，排查类型：{}，判定集群：[{}:{}]，不一致集群:[{}:{}]".format(
                        access_layer, first_cluster, first_cluster_ips_set, cluster.immute_domain, ips
                    )
                )
        if check_is_all_in_group:
            # 判断cluster_ids的列表，已经是所有同组共享的集群列表
            # 这里如果上面检查通过，则已经证明了cluster_ids的集群，是同组共享，现在这里是判断是否包括所有的同组共享的集群。
            # 拿第一个集群的机器，作为判断依据，或者机器关联所有的集群信息，是否和传入cluster_ids 对等
            if access_layer == AccessLayer.PROXY:
                check_machine = Cluster.objects.get(id=cluster_ids[0]).proxyinstance_set.first().machine
                all_cluster_ids = {p.cluster.get().id for p in ProxyInstance.objects.filter(machine=check_machine)}
            else:
                check_machine = Cluster.objects.get(id=cluster_ids[0]).storageinstance_set.first().machine
                all_cluster_ids = {s.cluster.get().id for s in StorageInstance.objects.filter(machine=check_machine)}
            if all_cluster_ids != set(cluster_ids):
                # 如果两个集合不相等，则认为传入的cluster_ids，不齐全，检查不通过
                return _("检测到传入集群列表，还有缺漏的同机共享的集群， 缺漏的集群ID:[{}]".format(all_cluster_ids - set(cluster_ids)))

        return ""

    @classmethod
    def per_check_all_machine_in_cluster(cls, cluster_id: int, machines: Set[str], access_layer: AccessLayer) -> str:
        """
        判断传入的机器列表machines，是否属于集群cluster_id的接入类型access_layer, 并且判断集群所有的access_layer类型，都在machines里面
        @param cluster_id: 待检查集群列表
        @param machines: 待检查的机器信息，机器列表是[ip1,ip2,...]
        @param access_layer: 待检测的接入类型，比如传入的是proxy，则检查proxy类型的关系，以此类推
        """
        cluster = Cluster.objects.prefetch_related("storageinstance_set", "proxyinstance_set").get(id=cluster_id)

        if access_layer == AccessLayer.PROXY:
            ips = {i.machine.ip for i in cluster.proxyinstance_set.all()}

        elif access_layer == AccessLayer.STORAGE:
            ips = {i.machine.ip for i in cluster.storageinstance_set.all()}

        else:
            # 其余的不支持
            raise TicketDataException(f" No such access_layer [{access_layer}] type checking is supported")

        if ips < machines:
            # 表示machines里面，存在不属于集群的access_layer类型机器，检查不通过
            return _("存在不属于集群[{}]所有{}类型的机器, 无效的机器信息{}".format(cluster.immute_domain, access_layer, machines - ips))

        if ips > machines:
            # 表示machines里面，不能包括集群所有access_layer类型的机器，检查不通过
            return _("没有包括集群[{}]所有{}类型的机器, 相差的机器信息{}".format(cluster.immute_domain, access_layer, ips - machines))

        if ips != machines:
            # 表示两个集合不相等，校验不通过
            return _("集群[{}]所有{}类型的机器和存入的机器不对等, 差异的机器信息{}".format(cluster.immute_domain, access_layer, ips ^ machines))

        # 表示两个集合相等，则代表集群所有的access_layer类型的机器，都在machines里面，校验通过
        return ""
