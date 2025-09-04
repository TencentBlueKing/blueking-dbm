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
from typing import List

from django.utils.translation import ugettext as _

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
        cls, bk_biz_id: int, db_module_id: int, ready_to_add_count: int, existing_count: int, immute_domain: str = None
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
        # 判断immute_domain是否为空
        if not immute_domain:
            upper_limit_count = calc_spider_max_count(
                bk_biz_id=bk_biz_id,
                db_module_id=db_module_id,
                db_version=spider_version,
                immute_domain="",
                is_init=True,
            )
        # 获取集群spider_master数量理论值
        else:
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
    def pre_check_ip_clusters_included(cls, ip: str, bk_cloud_id: int, cluster_ids: list, access_layer: AccessLayer):
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
