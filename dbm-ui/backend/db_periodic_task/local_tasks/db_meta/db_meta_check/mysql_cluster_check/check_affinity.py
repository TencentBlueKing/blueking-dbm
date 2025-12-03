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
from collections import defaultdict
from typing import Dict, List, Optional, Set

from django.db.models import Q
from django.utils.translation import gettext as _

from backend.configuration.constants import AffinityEnum, DBType
from backend.configuration.models import DBAdministrator
from backend.db_meta.enums import ClusterPhase, ClusterType, InstancePhase, InstanceRole, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster, StorageInstance
from backend.db_report.enums import ReportStateType
from backend.ticket.constants import TICKET_RUNNING_STATUS_SET, TicketType
from backend.ticket.models.ticket import ClusterOperateRecord

from .base import create_or_update_affinity_report, delete_old_affinity_reports, get_cluster_expected_city_ids

logger = logging.getLogger("root")


def check_mysql_affinity():
    """
    检查 MySQL 集群的亲和性
    """
    MySQLAffinityChecker().check_all_clusters()


class MySQLAffinityChecker:
    """
    MySQL 集群亲和性检查器

    支持的集群类型:
    - TenDBHA: 检查 proxy 分布和 backend master-slave pair 亲和性
    - TenDBCluster: 检查 spider_master 分布和 remote master-slave pair 亲和性

    支持的亲和性级别:
    - SAME_SUBZONE_CROSS_SWTICH: 同园区跨交换机
    - CROS_SUBZONE: 跨园区
    - CROSS_RACK: 跨机架
    """

    PROXY_DISTRIBUTION_CHECK = "proxy_distribution"
    BACKEND_PAIRS_CHECK = "backend_pairs_location"
    SPIDER_DISTRIBUTION_CHECK = "spider_distribution"
    REMOTE_PAIRS_CHECK = "remote_pairs_location"

    def __init__(self):
        """初始化检查器"""
        # 支持的集群类型
        self._supported_cluster_types = [
            ClusterType.TenDBHA.value,
            ClusterType.TenDBCluster.value,
        ]
        # 需要忽略的工单类型（集群正在变更中）
        # 注意：TenDBHA 集群使用 MYSQL_HA_DESTROY，TenDBCluster 使用 TENDBCLUSTER_DESTROY
        self._ignore_tickets = [
            TicketType.MYSQL_HA_DESTROY.value,  # TenDBHA 集群删除
            TicketType.TENDBCLUSTER_DESTROY.value,  # TenDBCluster 集群删除
        ]
        # 支持的亲和性级别
        self._supported_levels = {
            AffinityEnum.SAME_SUBZONE_CROSS_SWTICH.value,
            AffinityEnum.CROS_SUBZONE.value,
            AffinityEnum.CROSS_RACK.value,
        }

    def check_all_clusters(self) -> None:
        """检查所有 MySQL 集群的亲和性"""
        # 删除旧记录
        delete_old_affinity_reports(self._supported_cluster_types, 30)

        # 只查询支持的集群类型和亲和性级别，且 phase 为 online
        for cluster in Cluster.objects.filter(
            Q(cluster_type__in=self._supported_cluster_types),
            Q(disaster_tolerance_level__in=self._supported_levels),
            Q(phase=ClusterPhase.ONLINE.value),
        ):
            try:
                self._check_cluster_affinity(cluster)
            except Exception as e:
                logger.error(_("亲和性检查: 检查集群 {} 时发生错误: {}").format(cluster.immute_domain, str(e)), exc_info=True)

    def _check_cluster_affinity(self, cluster: Cluster) -> None:
        """检查单个集群的亲和性"""
        logger.info(_("亲和性检查: 开始检查集群 {}").format(cluster.immute_domain))

        # 检查是否应该忽略该集群
        if self._should_ignore_cluster(cluster):
            return

        # 获取DBA
        dba_list = DBAdministrator.get_biz_db_type_admins(bk_biz_id=cluster.bk_biz_id, db_type=DBType.MySQL.value)
        creator = dba_list[0] if dba_list else "admin"

        # 获取亲和性级别（已在查询时过滤，这里直接使用）
        affinity_level = cluster.disaster_tolerance_level

        # 检查 region 是否为空或为 default
        if not cluster.region or cluster.region.lower() == "default":
            region_value = cluster.region if cluster.region else _("空")
            error_msg = _(
                "集群配置错误: region 为 '{}' 无法进行亲和性检查\n" "集群亲和性级别: {}\n" "亲和性检查要求 region 必须配置为有效的城市/地域，不能为空或 'default'"
            ).format(region_value, affinity_level)
            logger.error(_("亲和性检查: 集群 {} - region 配置错误").format(cluster.immute_domain))
            create_or_update_affinity_report(
                cluster=cluster,
                affinity_type=affinity_level,
                msg=error_msg,
                state=ReportStateType.ABNORMAL.value,
                creator=creator,
            )
            return

        # 获取集群期望的城市ID（用于CROS_SUBZONE检查）
        expected_city_ids = get_cluster_expected_city_ids(cluster)

        # 根据集群类型执行不同的检查
        if cluster.cluster_type == ClusterType.TenDBHA.value:
            self._check_tendbha_affinity(cluster, affinity_level, expected_city_ids, creator)
        elif cluster.cluster_type == ClusterType.TenDBCluster.value:
            self._check_tendbcluster_affinity(cluster, affinity_level, expected_city_ids, creator)

    def _should_ignore_cluster(self, cluster: Cluster) -> bool:
        """检查是否应该忽略该集群"""
        # phase 已在查询时过滤，这里只检查是否有活跃的销毁/禁用工单
        if ClusterOperateRecord.objects.filter(
            ticket__ticket_type__in=self._ignore_tickets,
            ticket__status__in=TICKET_RUNNING_STATUS_SET,
            cluster_id=cluster.id,
        ).exists():
            logger.info(_("亲和性检查: 忽略集群 {}，存在活跃的销毁/禁用工单").format(cluster.immute_domain))
            return True

        return False

    def _check_tendbha_affinity(
        self, cluster: Cluster, affinity_level: str, expected_city_ids: Set[int], creator: str
    ) -> None:
        """检查 TenDBHA 集群的亲和性"""
        check_results = []

        # 1. 检查 proxy 分布（只检查 online 状态的实例）
        proxy_instances = cluster.proxyinstance_set.filter(phase=InstancePhase.ONLINE.value)
        if proxy_instances.exists():
            proxy_result = self._validate_proxies_affinity(proxy_instances, affinity_level, expected_city_ids)
            proxy_result["result_type"] = self.PROXY_DISTRIBUTION_CHECK
            proxy_result["identifier"] = "proxies"
            check_results.append(proxy_result)

        # 2. 检查 backend master-slave pairs（只检查 online 状态的实例）
        master_instances = cluster.storageinstance_set.filter(
            instance_role=InstanceRole.BACKEND_MASTER.value, phase=InstancePhase.ONLINE.value
        )
        backend_results = self._validate_backends_affinity(master_instances, affinity_level, expected_city_ids)
        for machine_ip, result in backend_results.items():
            result["result_type"] = self.BACKEND_PAIRS_CHECK
            result["identifier"] = machine_ip
            check_results.append(result)

        # 创建报告
        self._create_affinity_reports(
            cluster=cluster,
            affinity_level=affinity_level,
            check_results=check_results,
            creator=creator,
        )

    def _check_tendbcluster_affinity(
        self, cluster: Cluster, affinity_level: str, expected_city_ids: Set[int], creator: str
    ) -> None:
        """检查 TenDBCluster 集群的亲和性"""
        check_results = []

        # 1. 检查 spider_master 分布（只检查 online 状态的实例）
        spider_masters = cluster.proxyinstance_set.filter(
            tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER.value,
            phase=InstancePhase.ONLINE.value,
        )
        if spider_masters.exists():
            spider_result = self._validate_proxies_affinity(spider_masters, affinity_level, expected_city_ids)
            spider_result["result_type"] = self.SPIDER_DISTRIBUTION_CHECK
            spider_result["identifier"] = "spider_masters"
            check_results.append(spider_result)

        # 2. 检查 remote master-slave pairs（只检查 online 状态的实例）
        remote_masters = cluster.storageinstance_set.filter(
            instance_role=InstanceRole.REMOTE_MASTER.value, phase=InstancePhase.ONLINE.value
        )
        remote_results = self._validate_backends_affinity(remote_masters, affinity_level, expected_city_ids)
        for machine_ip, result in remote_results.items():
            result["result_type"] = self.REMOTE_PAIRS_CHECK
            result["identifier"] = machine_ip
            check_results.append(result)

        # 创建报告
        self._create_affinity_reports(
            cluster=cluster,
            affinity_level=affinity_level,
            check_results=check_results,
            creator=creator,
        )

    @classmethod
    def _validate_proxies_affinity(
        cls, proxy_instances, affinity_level: str, expected_city_ids: Set[int]
    ) -> Dict[str, any]:
        """
        检查 proxy/spider 实例是否满足亲和性要求

        Returns:
            dict: {msg: str, state: ReportStateType, proxy_count: int}
        """
        subzones_racks_map = defaultdict(set)
        subzones_machines_map = defaultdict(int)
        subzones_ips_map = defaultdict(list)

        for proxy_obj in proxy_instances:
            subzone_id = proxy_obj.machine.bk_sub_zone_id
            rack_id = proxy_obj.machine.bk_rack_id

            subzones_racks_map[subzone_id].add(rack_id)
            subzones_machines_map[subzone_id] += 1
            subzones_ips_map[(subzone_id, rack_id)].append(proxy_obj.machine.ip)

        result = {
            "state": ReportStateType.NORMAL.value,
            "msg": "",
            "proxy_count": len(proxy_instances),
        }

        msg, state = None, ReportStateType.NORMAL
        if affinity_level == AffinityEnum.SAME_SUBZONE_CROSS_SWTICH.value:
            msg, state = cls._check_proxies_same_subzone(
                subzones_racks_map, subzones_machines_map, subzones_ips_map, proxy_instances
            )
        elif affinity_level == AffinityEnum.CROS_SUBZONE.value:
            msg, state = cls._check_proxies_cross_subzone(
                subzones_racks_map, subzones_machines_map, subzones_ips_map, expected_city_ids, proxy_instances
            )
        elif affinity_level == AffinityEnum.CROSS_RACK.value:
            msg, state = cls._check_proxies_cross_rack(
                subzones_racks_map, subzones_machines_map, subzones_ips_map, proxy_instances
            )

        if msg:
            result["state"] = state.value
            result["msg"] = msg

        return result

    @classmethod
    def _check_proxies_same_subzone(cls, racks_map: dict, machines_map: dict, ips_map: dict, proxy_instances) -> tuple:
        """检查 SAME_SUBZONE_CROSS_SWTICH 级别的 proxy 分布"""
        proxy_count = sum(machines_map.values())
        subzone_count = len(racks_map.keys())

        if subzone_count != 1:
            # 收集所有 proxy 的详细位置信息
            proxy_details = []
            for proxy_obj in proxy_instances:
                city_name = proxy_obj.machine.bk_city.bk_idc_city_name
                subzone = proxy_obj.machine.bk_sub_zone or _("未知园区")
                rack = proxy_obj.machine.bk_rack or _("未知机架")
                proxy_details.append(f"{proxy_obj.machine.ip} ({city_name}/{subzone}/{_('机架')}{rack})")
            proxies_info = ", ".join(proxy_details)
            return (
                _("亲和性违规: proxies 分布在 {} 个不同的园区，期望只在 1 个园区\n详情: {}").format(subzone_count, proxies_info),
                ReportStateType.ABNORMAL,
            )

        subzone_id = list(racks_map.keys())[0]
        rack_count = len(list(racks_map.values())[0])

        # 计算该园区内每个机架的机器数量
        rack_machine_counts = {}
        for (sz_id, r_id), ips in ips_map.items():
            if sz_id == subzone_id:
                rack_machine_counts[r_id] = len(ips)

        ok, limit, violating_rack = cls._cross_rack_check_and_get_limits(proxy_count, rack_count, rack_machine_counts)
        if not ok:
            # 收集该园区内所有 proxy 的详细信息
            proxy_details = []
            for proxy_obj in proxy_instances:
                if proxy_obj.machine.bk_sub_zone_id == subzone_id:
                    city_name = proxy_obj.machine.bk_city.bk_idc_city_name
                    subzone = proxy_obj.machine.bk_sub_zone or _("未知园区")
                    rack = proxy_obj.machine.bk_rack or _("未知机架")
                    rack_id = proxy_obj.machine.bk_rack_id
                    proxy_details.append(f"{proxy_obj.machine.ip} ({city_name}/{subzone}/{_('机架ID')}:{rack_id})")
            proxies_info = ", ".join(proxy_details)

            # 根据不同的违规类型生成错误信息
            if rack_count < limit:
                msg = _("亲和性违规: {} 个 proxies 在园区 {} 中分布在 {} 个机架，期望至少 {} 个机架\n详情: {}").format(
                    proxy_count, subzone_id, rack_count, limit, proxies_info
                )
            elif violating_rack:
                r_id, cnt = violating_rack
                msg = _("亲和性违规: {} 个 proxies 在园区 {} 中，机架机器数达到或超过限制 {}\n" "超限机架: {}\n详情: {}").format(
                    proxy_count, subzone_id, limit, _("机架ID {} 有 {} 台").format(r_id, cnt), proxies_info
                )
            else:
                msg = _("亲和性违规: {} 个 proxies 在园区 {} 中分布不符合要求\n详情: {}").format(proxy_count, subzone_id, proxies_info)
            return msg, ReportStateType.WARNING
        return None, ReportStateType.NORMAL

    @classmethod
    def _check_proxies_cross_subzone(
        cls, racks_map: dict, machines_map: dict, ips_map: dict, expected_city_ids: Set[int], proxy_instances
    ) -> tuple:
        """检查 CROS_SUBZONE 级别的 proxy 分布"""
        proxy_count = sum(machines_map.values())
        # 单个园区最多允许 n*0.5 向上取整的数量
        max_proxies_per_subzone = proxy_count // 2 + 1

        # 检查城市I
        if expected_city_ids:
            for proxy_obj in proxy_instances:
                machine_city_id = proxy_obj.machine.bk_city.bk_idc_city_id
                if machine_city_id not in expected_city_ids:
                    city_name = proxy_obj.machine.bk_city.bk_idc_city_name
                    subzone = proxy_obj.machine.bk_sub_zone or _("未知园区")
                    return (
                        _("亲和性违规: proxy {} 的城市 {}(ID:{}) 不在集群期望的城市ID集合 {} 中").format(
                            proxy_obj.machine.ip, city_name, machine_city_id, expected_city_ids
                        ),
                        ReportStateType.ABNORMAL,
                    )

        for subzone_id, rack_set in racks_map.items():
            sub_proxy_count = machines_map[subzone_id]

            # 收集该园区内的 proxy 详细信息
            proxy_details = []
            for proxy_obj in proxy_instances:
                if proxy_obj.machine.bk_sub_zone_id == subzone_id:
                    city_name = proxy_obj.machine.bk_city.bk_idc_city_name
                    subzone = proxy_obj.machine.bk_sub_zone or _("未知园区")
                    rack_id = proxy_obj.machine.bk_rack_id
                    proxy_details.append(f"{proxy_obj.machine.ip} ({city_name}/{subzone}/{_('机架ID')}:{rack_id})")
            proxies_info = ", ".join(proxy_details)

            if sub_proxy_count >= max_proxies_per_subzone:
                msg = _("亲和性违规: {} 个 proxies 在园区(id:{}) 中达到或超过限制 {}\n详情: {}").format(
                    sub_proxy_count, subzone_id, max_proxies_per_subzone, proxies_info
                )
                return msg, ReportStateType.ABNORMAL

            # 计算该园区内每个机架的机器数量
            rack_machine_counts = {}
            for (sz_id, r_id), ips in ips_map.items():
                if sz_id == subzone_id:
                    rack_machine_counts[r_id] = len(ips)

            rack_count = len(rack_set)
            ok, limit, violating_rack = cls._cross_rack_check_and_get_limits(
                sub_proxy_count, rack_count, rack_machine_counts
            )
            if not ok:
                if rack_count < limit:
                    msg = _("亲和性违规: {} 个 proxies 在园区(id:{}) 中分布在 {} 个机架，期望至少 {} 个机架\n详情: {}").format(
                        sub_proxy_count, subzone_id, rack_count, limit, proxies_info
                    )
                elif violating_rack:
                    r_id, cnt = violating_rack
                    msg = _("亲和性违规: {} 个 proxies 在园区(id:{}) 中，机架机器数达到或超过限制 {}\n" "超限机架: {}\n详情: {}").format(
                        sub_proxy_count, subzone_id, limit, _("机架ID {} 有 {} 台").format(r_id, cnt), proxies_info
                    )
                else:
                    msg = _("亲和性违规: {} 个 proxies 在园区(id:{}) 中分布不符合要求\n详情: {}").format(
                        sub_proxy_count, subzone_id, proxies_info
                    )
                return msg, ReportStateType.WARNING

        return None, ReportStateType.NORMAL

    @classmethod
    def _check_proxies_cross_rack(cls, racks_map: dict, machines_map: dict, ips_map: dict, proxy_instances) -> tuple:
        """检查 CROSS_RACK 级别的 proxy 分布"""
        msg = ""
        for subzone_id, rack_set in racks_map.items():
            rack_count = len(rack_set)
            sub_proxy_count = machines_map[subzone_id]

            # 计算该园区内每个机架的机器数量
            rack_machine_counts = {}
            for (sz_id, r_id), ips in ips_map.items():
                if sz_id == subzone_id:
                    rack_machine_counts[r_id] = len(ips)

            ok, limit, violating_rack = cls._cross_rack_check_and_get_limits(
                sub_proxy_count, rack_count, rack_machine_counts
            )
            if not ok:
                # 收集该园区内的 proxy 详细信息
                proxy_details = []
                for proxy_obj in proxy_instances:
                    if proxy_obj.machine.bk_sub_zone_id == subzone_id:
                        city_name = proxy_obj.machine.bk_city.bk_idc_city_name
                        subzone = proxy_obj.machine.bk_sub_zone or _("未知园区")
                        rack_id = proxy_obj.machine.bk_rack_id
                        proxy_details.append(f"{proxy_obj.machine.ip} ({city_name}/{subzone}/{_('机架ID')}:{rack_id})")
                proxies_info = ", ".join(proxy_details)

                if rack_count < limit:
                    msg += _("亲和性违规: {} 个 proxies 在园区(id:{}) 中分布在 {} 个机架，期望至少 {} 个机架\n详情: {}\n").format(
                        sub_proxy_count, subzone_id, rack_count, limit, proxies_info
                    )
                elif violating_rack:
                    r_id, cnt = violating_rack
                    msg += _("亲和性违规: {} 个 proxies 在园区(id:{}) 中，机架机器数达到或超过限制 {}\n" "超限机架: {}\n详情: {}\n").format(
                        sub_proxy_count, subzone_id, limit, _("机架ID {} 有 {} 台").format(r_id, cnt), proxies_info
                    )
                else:
                    msg += _("亲和性违规: {} 个 proxies 在园区(id:{}) 中分布不符合要求\n详情: {}\n").format(
                        sub_proxy_count, subzone_id, proxies_info
                    )
        return msg, ReportStateType.ABNORMAL if msg else ReportStateType.NORMAL

    @classmethod
    def _cross_rack_check_and_get_limits(
        cls, n_proxy: int, n_rack: int, rack_machine_counts: Optional[Dict[any, int]] = None
    ) -> tuple:
        """
        基于 proxy 数量和机架信息，判断是否满足跨机架要求

        检查两个条件：
        1. 机架数量 >= limit (n_proxy // 2 + 1)
        2. 每个机架的机器数量 <= limit (n_proxy // 2 + 1)

        Args:
            n_proxy: proxy 总数
            n_rack: 机架数量
            rack_machine_counts: 每个机架的机器数量字典 {rack_id: count}，可选

        Returns:
            tuple: (is_ok, limit, violating_rack)
            - is_ok: 是否满足所有要求
            - limit: 限制值 (n_proxy // 2 + 1)，既是最小机架数，也是每个机架最大机器数
            - violating_rack: 第一个违规的机架 (rack_id, count)，无违规时为 None
        """
        limit = n_proxy // 2 + 1

        # 检查机架数量是否足够
        if n_rack < limit:
            return False, limit, None

        # 检查每个机架的机器数量是否超限，发现第一个违规即返回
        if rack_machine_counts:
            for rack_id, count in rack_machine_counts.items():
                if count > limit:
                    return False, limit, (rack_id, count)

        return True, limit, None

    @classmethod
    def _validate_backends_affinity(
        cls, master_instances, affinity_level: str, expected_city_ids: Set[int]
    ) -> Dict[str, Dict[str, any]]:
        """
        检查 master-slave pairs 是否满足亲和性要求

        Returns:
            Dict {<master_ip>: {msg: str, state: ReportStateType}}
        """
        backend_results = {}
        for master_obj in master_instances:
            machine_ip = master_obj.machine.ip
            if machine_ip in backend_results:
                continue

            backend_result = cls._check_master_slave_affinity(
                master_obj=master_obj, affinity_level=affinity_level, expected_city_ids=expected_city_ids
            )
            backend_results[machine_ip] = backend_result

        return backend_results

    @classmethod
    def _check_master_slave_affinity(
        cls, master_obj: StorageInstance, affinity_level: str, expected_city_ids: Set[int]
    ) -> Dict[str, any]:
        """检查单个 master-slave pair 的亲和性"""
        result = {
            "msg": "",
            "state": ReportStateType.NORMAL.value,
        }

        try:
            # 只检查 is_stand_by=True 的 slave（一主多从情况下的主备）
            tuple_obj = master_obj.as_ejector.filter(receiver__is_stand_by=True).first()
            if not tuple_obj:
                # 没有配置 standby slave，跳过检查
                logger.debug(_("亲和性检查: Master {} 没有配置 standby slave，跳过检查").format(master_obj.machine.ip))
                return result
            slave_obj = tuple_obj.receiver
        except Exception as e:
            # 查询出错，跳过检查
            logger.debug(_("亲和性检查: 获取 Master {} 的 slave 时发生错误，跳过检查: {}").format(master_obj.machine.ip, str(e)))
            return result

        msg = None
        if affinity_level == AffinityEnum.SAME_SUBZONE_CROSS_SWTICH.value:
            msg = cls._check_backend_same_subzone(master_obj, slave_obj)
        elif affinity_level == AffinityEnum.CROS_SUBZONE.value:
            msg = cls._check_backend_cross_subzone(master_obj, slave_obj, expected_city_ids)
        elif affinity_level == AffinityEnum.CROSS_RACK.value:
            msg = cls._check_backend_cross_rack(master_obj, slave_obj)

        if msg:
            result["msg"] = msg
            result["state"] = ReportStateType.ABNORMAL.value
        else:
            result["msg"] = _("Master: {} 和 Slave: {} 符合亲和性级别 '{}'").format(
                master_obj.machine.ip, slave_obj.machine.ip, affinity_level
            )

        return result

    @classmethod
    def _check_backend_same_subzone(
        cls,
        master_obj: StorageInstance,
        slave_obj: StorageInstance,
    ) -> Optional[str]:
        """检查 SAME_SUBZONE_CROSS_SWTICH 级别的 master-slave pair"""
        if master_obj.machine.bk_sub_zone_id != slave_obj.machine.bk_sub_zone_id:
            master_info = cls._format_machine_info(master_obj.machine)
            slave_info = cls._format_machine_info(slave_obj.machine)
            return _("亲和性违规: Master 和 Slave 在不同的园区，期望在同一园区\nMaster: {}\nSlave: {}").format(master_info, slave_info)

        return cls._check_backend_cross_rack(master_obj, slave_obj)

    @classmethod
    def _check_backend_cross_subzone(
        cls, master_obj: StorageInstance, slave_obj: StorageInstance, expected_city_ids: Set[int]
    ) -> Optional[str]:
        """检查 CROS_SUBZONE 级别的 master-slave pair"""
        # 检查是否在不同园区
        if master_obj.machine.bk_sub_zone_id == slave_obj.machine.bk_sub_zone_id:
            master_info = cls._format_machine_info(master_obj.machine)
            slave_info = cls._format_machine_info(slave_obj.machine)
            return _("亲和性违规: Master 和 Slave 在同一园区，期望在不同园区\nMaster: {}\nSlave: {}").format(master_info, slave_info)

        # 检查城市ID是否一致
        if expected_city_ids:
            master_city_id = master_obj.machine.bk_city.bk_idc_city_id
            slave_city_id = slave_obj.machine.bk_city.bk_idc_city_id

            if master_city_id not in expected_city_ids:
                master_info = cls._format_machine_info(master_obj.machine)
                return _("亲和性违规: Master 的城市ID {} 不在集群期望的城市ID集合 {} 中\nMaster: {}").format(
                    master_city_id, expected_city_ids, master_info
                )

            if slave_city_id not in expected_city_ids:
                slave_info = cls._format_machine_info(slave_obj.machine)
                return _("亲和性违规: Slave 的城市ID {} 不在集群期望的城市ID集合 {} 中\nSlave: {}").format(
                    slave_city_id, expected_city_ids, slave_info
                )

        return None

    @classmethod
    def _check_backend_cross_rack(
        cls,
        master_obj: StorageInstance,
        slave_obj: StorageInstance,
    ) -> Optional[str]:
        """检查 CROSS_RACK 级别的 master-slave pair"""
        # 如果在不同园区，自动满足
        if master_obj.machine.bk_sub_zone_id != slave_obj.machine.bk_sub_zone_id:
            return None

        # 同一园区，必须在不同机架
        if master_obj.machine.bk_rack_id == slave_obj.machine.bk_rack_id:
            master_info = cls._format_machine_info(master_obj.machine)
            slave_info = cls._format_machine_info(slave_obj.machine)
            return _("亲和性违规: Master 和 Slave 在同一机架，期望在不同机架\nMaster: {}\nSlave: {}").format(master_info, slave_info)
        return None

    @classmethod
    def _format_machine_info(cls, machine) -> str:
        """格式化机器位置信息"""
        city_name = machine.bk_city.bk_idc_city_name
        subzone = machine.bk_sub_zone or _("未知园区")
        subzone_id = machine.bk_sub_zone_id
        rack = machine.bk_rack or _("未知机架")
        rack_id = machine.bk_rack_id
        return f"{machine.ip} ({_('城市')}:{city_name}, {_('园区')}:{subzone}[ID:{subzone_id}], {_('机架')}:{rack}[ID:{rack_id}])"

    @classmethod
    def _create_affinity_reports(
        cls,
        cluster: Cluster,
        affinity_level: str,
        check_results: List[Dict],
        creator: str = "admin",
    ) -> None:
        """创建亲和性检查报告"""
        # 统计失败的检查
        failed_checks = [result for result in check_results if result["state"] != ReportStateType.NORMAL.value]
        has_violations = len(failed_checks) > 0

        # 计算总机器数
        total_machines = 0
        backend_pair_count = 0
        for result in check_results:
            if result["result_type"] in [cls.PROXY_DISTRIBUTION_CHECK, cls.SPIDER_DISTRIBUTION_CHECK]:
                total_machines += result.get("proxy_count", 0)
            elif result["result_type"] in [cls.BACKEND_PAIRS_CHECK, cls.REMOTE_PAIRS_CHECK]:
                backend_pair_count += 1
        total_machines += backend_pair_count * 2

        if not has_violations:
            msg = _("亲和性检查通过: 所有 {} 台机器符合亲和性级别 '{}'").format(total_machines, affinity_level)
            logger.info(_("亲和性检查: 集群 {} 通过亲和性检查").format(cluster.immute_domain))

            create_or_update_affinity_report(
                cluster=cluster,
                affinity_type=affinity_level,
                msg=msg,
                state=ReportStateType.NORMAL.value,
                creator=creator,
            )
        else:
            total_warnings = sum(1 for result in failed_checks if result["state"] == ReportStateType.WARNING.value)
            total_violations = len(failed_checks) - total_warnings

            logger.warning(
                _("亲和性检查: 集群 {} 有 {} 个违规和 {} 个警告").format(cluster.immute_domain, total_violations, total_warnings)
            )

            # 合并所有失败检查的消息
            all_msgs = []
            for result in failed_checks:
                result_type_name = result["result_type"]
                identifier = result["identifier"]
                msg = result["msg"]
                all_msgs.append(f"[{result_type_name}:{identifier}] {msg}")

            combined_msg = "\n".join(all_msgs)

            # 选择最严重的状态
            if any(result["state"] == ReportStateType.ABNORMAL.value for result in failed_checks):
                final_state = ReportStateType.ABNORMAL.value
            else:
                final_state = ReportStateType.WARNING.value

            create_or_update_affinity_report(
                cluster=cluster,
                affinity_type=affinity_level,
                msg=combined_msg,
                state=final_state,
                creator=creator,
            )
