"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import datetime
import logging
from dataclasses import asdict
from datetime import timedelta
from typing import Dict, List, Tuple

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType, MySQLMonitorPauseTime
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import InstanceInnerRole, InstanceStatus, MachineType, TenDBClusterSpiderRole
from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance, StorageInstanceTuple
from backend.db_package.models import Package
from backend.flow.consts import MediumEnum
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.mysql_upgrade import upgrade_version_check
from backend.flow.plugins.components.collections.common.add_alarm_shield import AddAlarmShieldComponent
from backend.flow.plugins.components.collections.common.disable_alarm_shield import DisableAlarmShieldComponent
from backend.flow.plugins.components.collections.mysql.mysql_crond_control import MysqlCrondMonitorControlComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.common.mysql_cluster_info import get_version_and_charset
from backend.flow.utils.mysql.mysql_act_dataclass import CrondMonitorKwargs, DownloadMediaKwargs
from backend.flow.utils.mysql.mysql_version_parse import (
    get_sub_version_by_pkg_name,
    spider_cross_major_version,
    tspider_version_parse,
)

logger = logging.getLogger("flow")


def filter_spiders_by_version(cluster_id: int, target_version: str) -> Tuple[List, List]:
    """
    过滤掉版本已经等于待升级版本的spider实例

    Args:
        cluster_id: 集群ID
        target_version: 目标升级版本

    Returns:
        tuple: (需要升级的spider实例列表, 已经是目标版本的spider实例列表)
    """
    cluster = Cluster.objects.get(id=cluster_id)
    all_spiders = ProxyInstance.objects.filter(cluster=cluster)

    if len(all_spiders) <= 0:
        raise DBMetaException(message=_("根据cluster ids:{}无法找到对应的proxy实例").format(cluster_id))

    target_version_num = tspider_version_parse(target_version)
    spiders_to_upgrade = []
    spiders_already_target_version = []

    for spider_ins in all_spiders:
        current_version_num = tspider_version_parse(spider_ins.version)
        if current_version_num == target_version_num:
            spiders_already_target_version.append(spider_ins)
            logger.info(
                _("Spider实例 {}:{} 版本 {} 已经是目标版本，跳过升级").format(
                    spider_ins.machine.ip, spider_ins.port, spider_ins.version
                )
            )
        else:
            spiders_to_upgrade.append(spider_ins)

    logger.info(
        _("集群 {} 共有 {} 个spider实例，其中 {} 个需要升级，{} 个已经是目标版本").format(
            cluster.immute_domain, len(all_spiders), len(spiders_to_upgrade), len(spiders_already_target_version)
        )
    )

    return spiders_to_upgrade, spiders_already_target_version


def check_version_compatibility(cluster_id: int, new_mysql_pkg: Package, ticket_data: Dict) -> None:
    """
    检查版本兼容性

    Args:
        cluster_id: 集群ID
        new_mysql_pkg: 新的MySQL包
        ticket_data: 单据数据
    """
    try:
        cluster = Cluster.objects.get(id=cluster_id)

        # 获取当前集群的版本信息
        current_charset, current_mysql_ver = get_version_and_charset(
            cluster.bk_biz_id,
            db_module_id=cluster.db_module_id,
            cluster_type=cluster.cluster_type,
        )

        # 获取目标版本信息 - 如果有新模块ID的话
        new_db_module_id = ticket_data.get("new_db_module_id")
        if new_db_module_id:
            new_charset, new_mysql_ver = get_version_and_charset(
                cluster.bk_biz_id,
                db_module_id=new_db_module_id,
                cluster_type=cluster.cluster_type,
            )

            # 检查字符集一致性
            if new_charset != current_charset:
                raise DBMetaException(
                    message=_("集群 {} 升级前后字符集不一致，原字符集: {}，新模块字符集: {}").format(cluster_id, current_charset, new_charset)
                )

            # 检查版本升级的合法性
            upgrade_version_check(current_mysql_ver, new_mysql_ver)
            logger.info(_("集群 {} 版本兼容性检查通过: {} -> {}").format(cluster_id, current_mysql_ver, new_mysql_ver))
        else:
            # 如果没有指定新模块，检查当前包版本与当前集群版本的兼容性
            pkg_version = get_sub_version_by_pkg_name(new_mysql_pkg.name)
            upgrade_version_check(current_mysql_ver, pkg_version)
            logger.info(_("集群 {} 版本兼容性检查通过: {} -> {}").format(cluster_id, current_mysql_ver, pkg_version))

    except Exception as e:
        raise DBMetaException(message=_("集群 {} 版本兼容性检查失败: {}").format(cluster_id, str(e)))


def group_master_slave_pairs(cluster_id: int):
    """
    将实例按主从配对分组（基于TenDBCluster的shard架构）

    Args:
        cluster_id: 集群ID

    Returns:
        tuple: (pairs, all_instances)
            - pairs: 主从配对列表，每个元素包含以下字段：
                - master: 主实例信息字典
                    - ip: 主实例IP地址 (str)
                    - port: 主实例端口号 (int)
                    - instance: 主实例StorageInstance对象
                - slave: 从实例信息字典
                    - ip: 从实例IP地址 (str)
                    - port: 从实例端口号 (int)
                    - instance: 从实例StorageInstance对象
                - shard_id: shard的ID (int)
            - all_instances: remote存储实例查询集，与get_remote_storage_instances返回类型一致
    """
    pairs = []
    all_instances = []

    # 获取集群对象
    cluster = Cluster.objects.get(id=cluster_id)

    # 获取所有remote存储实例（与get_remote_storage_instances返回类型一致）
    # 通过shard来获取主从配对关系，按shard_id从小到大排序
    shards = cluster.tendbclusterstorageset_set.filter().order_by("shard_id")
    for shard in shards:
        try:
            # 获取master实例
            remote_master = StorageInstance.objects.get(id=shard.storage_instance_tuple.ejector_id)
            # 获取slave实例
            remote_slave = StorageInstance.objects.get(id=shard.storage_instance_tuple.receiver_id)
            all_instances.append(remote_master)
            all_instances.append(remote_slave)
            master_info = {"ip": remote_master.machine.ip, "port": remote_master.port, "instance": remote_master}

            slave_info = {"ip": remote_slave.machine.ip, "port": remote_slave.port, "instance": remote_slave}

            pairs.append({"master": master_info, "slave": slave_info, "shard_id": shard.shard_id})

        except StorageInstance.DoesNotExist:
            logger = logging.getLogger("flow")
            logger.warning(_("shard {} 的主从实例不存在").format(shard.shard_id))
            continue

    return pairs, all_instances


def convert_pairs_to_upgrade_instances(master_slave_pairs):
    """
    将主从配对格式转换为升级检查所需的格式

    Args:
        master_slave_pairs: 主从配对列表，格式：[{"master": {...}, "slave": {...}}]

    Returns:
        list: 升级实例列表，格式：[{"ip": "x.x.x.x", "ports": [3306, 3307]}]
    """
    # 按IP分组收集端口
    ip_ports_map = {}
    instance_count = 0
    for pair_index, pair in enumerate(master_slave_pairs):
        # 处理master实例
        if pair.get("master"):
            master_info = pair["master"]
            ip = master_info["ip"]
            port = master_info["port"]
            if ip not in ip_ports_map:
                ip_ports_map[ip] = []
            if port not in ip_ports_map[ip]:
                ip_ports_map[ip].append(port)
                instance_count += 1
                logger.debug(_("添加master实例: {}:{} (配对#{})").format(ip, port, pair_index + 1))
        # 处理slave实例
        if pair.get("slave"):
            slave_info = pair["slave"]
            ip = slave_info["ip"]
            port = slave_info["port"]
            if ip not in ip_ports_map:
                ip_ports_map[ip] = []
            if port not in ip_ports_map[ip]:
                ip_ports_map[ip].append(port)
                instance_count += 1
                logger.debug(_("添加slave实例: {}:{} (配对#{})").format(ip, port, pair_index + 1))

    # 转换为mysql_cluster_upgrade_check_subflow所需的格式
    upgrade_instances = []
    for ip, ports in ip_ports_map.items():
        upgrade_instances.append({"ip": ip, "ports": sorted(ports)})  # 排序端口列表保证一致性
        logger.debug(_("主机 {} 包含端口: {}").format(ip, sorted(ports)))

    logger.info(_("共收集到 {} 个实例，分布在 {} 个主机上").format(instance_count, len(upgrade_instances)))
    return upgrade_instances


def check_master_slave_pair(pair: Dict, pair_index: int, cluster_id: int) -> None:
    """
    检查单个主从对的健康状态

    Args:
        pair: 主从配对信息
        pair_index: 配对索引
        cluster_id: 集群ID
    """
    master_info = pair.get("master")
    slave_info = pair.get("slave")

    # 检查master实例
    if not master_info:
        raise DBMetaException(message=_("集群 {} 第 {} 个主从对缺少master实例").format(cluster_id, pair_index))

    master_instance = master_info["instance"]
    if master_instance.status != InstanceStatus.RUNNING:
        raise DBMetaException(
            message=_("集群 {} master实例 {}:{} 状态异常: {}").format(
                cluster_id, master_info["ip"], master_info["port"], master_instance.status
            )
        )

    if master_instance.instance_inner_role != InstanceInnerRole.MASTER:
        raise DBMetaException(
            message=_("集群 {} 实例 {}:{} 角色配置错误，期望: {}, 实际: {}").format(
                cluster_id,
                master_info["ip"],
                master_info["port"],
                InstanceInnerRole.MASTER,
                master_instance.instance_inner_role,
            )
        )

    # 检查slave实例
    if not slave_info:
        raise DBMetaException(message=_("集群 {} 第 {} 个主从对缺少slave实例").format(cluster_id, pair_index))

    slave_instance = slave_info["instance"]
    if slave_instance.status != InstanceStatus.RUNNING:
        raise DBMetaException(
            message=_("集群 {} slave实例 {}:{} 状态异常: {}").format(
                cluster_id, slave_info["ip"], slave_info["port"], slave_instance.status
            )
        )

    if slave_instance.instance_inner_role != InstanceInnerRole.SLAVE:
        raise DBMetaException(
            message=_("集群 {} 实例 {}:{} 角色配置错误，期望: {}, 实际: {}").format(
                cluster_id,
                slave_info["ip"],
                slave_info["port"],
                InstanceInnerRole.SLAVE,
                slave_instance.instance_inner_role,
            )
        )

    # 检查主从关系是否正确配置
    check_master_slave_relationship(master_instance, slave_instance, pair_index, cluster_id)

    logger.info(
        _("集群 {} 第 {} 个主从对 {}:{} <-> {}:{} 检查通过").format(
            cluster_id,
            pair_index,
            master_info["ip"],
            master_info["port"],
            slave_info["ip"],
            slave_info["port"],
        )
    )


def check_master_slave_relationship(master_instance, slave_instance, pair_index: int, cluster_id: int) -> None:
    """
    检查主从关系是否正确配置

    Args:
        master_instance: master实例
        slave_instance: slave实例
        pair_index: 配对索引
        cluster_id: 集群ID
    """
    try:
        # 检查是否存在正确的StorageInstanceTuple关系
        StorageInstanceTuple.objects.get(ejector=master_instance, receiver=slave_instance)
        logger.debug(_("集群 {} 第 {} 个主从对的主从关系配置正确").format(cluster_id, pair_index))
    except StorageInstanceTuple.DoesNotExist:
        raise DBMetaException(
            message=_("集群 {} 第 {} 个主从对 {}:{} <-> {}:{} 主从关系配置错误").format(
                cluster_id,
                pair_index,
                master_instance.machine.ip,
                master_instance.port,
                slave_instance.machine.ip,
                slave_instance.port,
            )
        )


def add_alarm_shield_act(sub_pipeline, cluster: Cluster, shield_hours: int = 4) -> None:
    """
    添加告警屏蔽活动

    Args:
        sub_pipeline: 子流程
        cluster: 集群对象
        shield_hours: 屏蔽小时数
    """
    # 获取集群的所有存储实例IP
    storage_ips = list(
        cluster.storageinstance_set.filter(machine_type=MachineType.REMOTE)
        .values_list("machine__ip", flat=True)
        .distinct()
    )

    sub_pipeline.add_act(
        act_name=_("屏蔽集群 {} 告警{}小时").format(cluster.name, shield_hours),
        act_component_code=AddAlarmShieldComponent.code,
        kwargs={
            "begin_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": (datetime.datetime.now() + timedelta(hours=shield_hours)).strftime("%Y-%m-%d %H:%M:%S"),
            "description": _("集群 {} TenDBCluster存储层本地升级操作").format(cluster.immute_domain),
            "dimensions": [
                {
                    "name": "instance_host",
                    "values": storage_ips,
                }
            ],
        },
    )


def add_disable_alarm_shield_act(sub_pipeline) -> None:
    """
    添加解除告警屏蔽活动

    Args:
        sub_pipeline: 子流程
    """
    sub_pipeline.add_act(act_name=_("解除告警屏蔽"), act_component_code=DisableAlarmShieldComponent.code, kwargs={})


def add_monitor_shield_act(sub_pipeline, instances, bk_cloud_id: int) -> None:
    """
    添加监控屏蔽活动

    Args:
        sub_pipeline: 子流程
        instances: 实例列表
        bk_cloud_id: 云区域ID
    """
    ips = list(set([instance.machine.ip for instance in instances]))

    sub_pipeline.add_act(
        act_name=_("屏蔽监控"),
        act_component_code=MysqlCrondMonitorControlComponent.code,
        kwargs=asdict(
            CrondMonitorKwargs(
                bk_cloud_id=bk_cloud_id,
                exec_ips=ips,
                port=0,
                minutes=MySQLMonitorPauseTime.SLAVE_DELAY,
            )
        ),
    )


def add_monitor_unshield_act(sub_pipeline, instances, bk_cloud_id: int) -> None:
    """
    添加解除监控屏蔽活动

    Args:
        sub_pipeline: 子流程
        instances: 实例列表
        bk_cloud_id: 云区域ID
    """
    ips = list(set([instance.machine.ip for instance in instances]))

    sub_pipeline.add_act(
        act_name=_("解除监控屏蔽"),
        act_component_code=MysqlCrondMonitorControlComponent.code,
        kwargs=asdict(
            CrondMonitorKwargs(
                bk_cloud_id=bk_cloud_id,
                exec_ips=ips,
                port=0,
                enable=True,
            )
        ),
    )


def add_mysql_media_download_for_all_hosts(
    sub_pipeline, remote_storage_instances, pkg_id: int, bk_cloud_id: int
) -> None:
    """
    按主机维度统一下发MySQL升级介质

    Args:
        sub_pipeline: 子流程
        remote_storage_instances: remote存储实例
        pkg_id: 包ID
        bk_cloud_id: 云区域ID
    """
    # 收集所有唯一的主机IP
    unique_hosts = set()
    for instance in remote_storage_instances:
        if hasattr(instance, "machine") and hasattr(instance.machine, "ip"):
            unique_hosts.add(instance.machine.ip)
        else:
            logger.warning(_("实例 {} 缺少机器IP信息，跳过").format(instance))

    unique_hosts_list = sorted(list(unique_hosts))  # 排序保证一致性

    if not unique_hosts_list:
        logger.warning(_("没有找到有效的主机IP，跳过介质下发"))
        return

    logger.info(_("开始对 {} 个主机下发MySQL升级介质").format(len(unique_hosts_list)))
    logger.debug(_("目标主机列表: {}").format(",".join(unique_hosts_list)))

    try:
        # 获取升级包文件列表
        file_list = GetFileList(db_type=DBType.MySQL).mysql_upgrade_package(pkg_id=pkg_id, db_version="")
        logger.debug(_("升级包文件列表: {}").format(file_list))

        # 一次性下发介质到所有主机
        sub_pipeline.add_act(
            act_name=_("下发MySQL升级包到所有主机({})").format(len(unique_hosts_list)),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(
                DownloadMediaKwargs(
                    bk_cloud_id=bk_cloud_id,
                    exec_ip=unique_hosts_list,  # 直接传递IP列表
                    file_list=file_list,
                )
            ),
        )
        logger.info(_("成功添加介质下发活动，目标主机数: {}").format(len(unique_hosts_list)))
    except Exception as e:
        logger.error(_("创建介质下发活动失败: {}").format(str(e)))
        raise


def check_spider_upgrade_version_compatibility(data: Dict) -> None:
    """
    检查spider升级版本兼容性

    Args:
        data: 升级数据
    """
    for info in data["infos"]:
        pkg_id = info["pkg_id"]
        cluster_id = info["cluster_id"]
        spider_pkg = Package.objects.get(id=pkg_id, pkg_type=MediumEnum.Spider)
        new_spider_version_num = tspider_version_parse(spider_pkg.name)
        cluster = Cluster.objects.get(id=cluster_id)
        spiders = ProxyInstance.objects.filter(cluster=cluster)

        # 获取当前版本信息用于关键字检查
        current_versions = set()
        for spider_ins in spiders:
            current_version = tspider_version_parse(spider_ins.version)
            current_versions.add(spider_ins.version)
            if current_version >= new_spider_version_num:
                logger.error(_("待升级版本 {} 需要大于当前版本 {}").format(new_spider_version_num, current_version))
                raise DBMetaException(message=_("待升级版本大于等于新版本，请确认升级的版本"))


def check_spider_node_count_compatibility(data: Dict) -> None:
    """
    检查spider节点数量兼容性

    Args:
        data: 升级数据
    """
    for info in data["infos"]:
        cluster_id = info["cluster_id"]
        cluster = Cluster.objects.get(id=cluster_id)

        if not data.get("upgrade_local", False):
            spider_master_ip_list = info["spider_master_ip_list"]
            spider_slave_ip_list = info.get("spider_slave_ip_list", [])
            master_spiders_count = cluster.proxyinstance_set.filter(
                tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER
            ).count()
            if master_spiders_count != len(spider_master_ip_list):
                raise DBMetaException(message=_("待升级spiderMaster节点数传入ip节点数不一致,请确认"))
            slave_spiders_count = cluster.proxyinstance_set.filter(
                tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE
            ).count()
            if slave_spiders_count > 0 and len(spider_slave_ip_list) != slave_spiders_count:
                raise DBMetaException(message=_("待升级spiderSlave节点数传入ip节点数不一致,请确认"))


def get_spider_upgrade_instances(cluster_id: int, target_version: str) -> Tuple[List, List, List]:
    """
    获取spider升级实例信息

    Args:
        cluster_id: 集群ID
        target_version: 目标版本

    Returns:
        tuple: (需要升级的spider实例列表, 已经是目标版本的spider实例列表, spider IP列表)
    """
    spiders_to_upgrade, spiders_already_target_version = filter_spiders_by_version(cluster_id, target_version)

    spider_ips = []
    for spider_ins in spiders_to_upgrade:
        spider_ips.append(spider_ins.machine.ip)

    return spiders_to_upgrade, spiders_already_target_version, spider_ips


def get_spider_master_instances(spiders_to_upgrade: List) -> List:
    """
    获取spider master实例列表

    Args:
        spiders_to_upgrade: 需要升级的spider实例列表

    Returns:
        list: spider master实例列表
    """
    spider_master_ins = []
    for spider_ins in spiders_to_upgrade:
        spider_role = spider_ins.tendbclusterspiderext.spider_role
        if spider_role == TenDBClusterSpiderRole.SPIDER_MASTER:
            spider_master_ins.append(f"{spider_ins.machine.ip}{IP_PORT_DIVIDER}{spider_ins.port}")

    return spider_master_ins


def check_cross_major_version_upgrade(spiders: List, target_version: str) -> Tuple[bool, Dict]:
    """
    检查是否跨主版本升级

    Args:
        spiders: spider实例列表
        target_version: 目标版本

    Returns:
        tuple: (是否跨主版本, 版本映射)
    """
    is_cross_major_version = False
    from_version_map = {}

    for spider_ins in spiders:
        # 判断是否跨主版本
        if spider_cross_major_version(
            tspider_version_parse(target_version), tspider_version_parse(spider_ins.version)
        ):
            is_cross_major_version = True
            # 跨版本时，只需要存一个检查版本的实例
            # spider_ins.version 存的值 1.15
            if not from_version_map:
                from_version_map[spider_ins.version] = [f"{spider_ins.machine.ip}:{spider_ins.port}"]

    return is_cross_major_version, from_version_map
