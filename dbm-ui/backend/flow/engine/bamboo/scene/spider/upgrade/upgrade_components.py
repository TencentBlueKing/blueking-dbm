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
import datetime
from collections import defaultdict
from dataclasses import asdict
from datetime import timedelta
from typing import Dict, List

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterEntryRole, InstancePhase, InstanceStatus, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster
from backend.flow.consts import DnsOpType
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.entrys_manager import BuildEntrysManageSubflow
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.common.mysql_upgrade_subflow import mysql_upgrade_subflow
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.subflow import standardize_mysql_cluster_subflow
from backend.flow.plugins.components.collections.common.add_alarm_shield import AddAlarmShieldComponent
from backend.flow.plugins.components.collections.common.disable_alarm_shield import DisableAlarmShieldComponent
from backend.flow.plugins.components.collections.mysql.check_client_connections import CheckClientConnComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.spider.upgrade_key_word_check import UpgradeKeyWordCheckComponent
from backend.flow.utils.mysql.mysql_act_dataclass import (
    CheckClientConnKwargs,
    DBMetaOPKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
    UpgradeKeyWordCheckKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta
from backend.flow.utils.spider.spider_check_constants import BASIC_CHECK_TYPES


def build_mysql_upgrade_pipelines(
    master_slave_pairs: List[Dict],
    role_type: str,
    action_name: str,
    is_same_tmysql_version: bool,
    root_id: str,
    ticket_data: Dict,
    pkg_id: int,
    new_mysql_version: str,
    cluster: Cluster,
    is_check_process: bool,
) -> List:
    """
    构建MySQL升级子流程列表

    Args:
        master_slave_pairs:
            - master: 主实例信息字典
                - ip: 主实例IP地址 (str)
                - port: 主实例端口号 (int)
                - instance: 主实例StorageInstance对象
            - slave: 从实例信息字典
                - ip: 从实例IP地址 (str)
                - port: 从实例端口号 (int)
                - instance: 从实例StorageInstance对象
            - shard_id: shard的ID (int)
        role_type: 角色类型，'master' 或 'slave'
        action_name: 操作名称，用于日志记录
        is_same_tmysql_version: 是否相同tmysql版本
        root_id: 根ID
        ticket_data: 单据数据
        pkg_id: 包ID
        cluster: 集群对象

    Returns:
        list: 升级子流程列表
    """
    upgrade_pipelines = []
    processed_instances = []

    # 按IP分组，收集同一IP的所有端口
    ip_ports_map = defaultdict(list)
    ip_shard_map = defaultdict(list)
    for pair in master_slave_pairs:
        instance_info = pair.get(role_type)
        if instance_info:
            ip = instance_info["ip"]
            port = instance_info["port"]
            ip_ports_map[ip].append(port)
            ip_shard_map[ip].append(pair["shard_id"])
    # 为每个IP创建升级子流程
    for ip, ports in ip_ports_map.items():
        # 构建子流程名称
        if len(ports) == 1:
            sub_name = _("{} shards:{} {}:{}").format(action_name, ",".join(map(str, ip_shard_map[ip])), ip, ports[0])
        else:
            sub_name = _("{} shards:{} {}:{}").format(
                action_name, ",".join(map(str, ip_shard_map[ip])), ip, ",".join(map(str, ports))
            )

        # 创建升级子流程，传递所有端口
        upgrade_pipeline = build_upgrade_mysql_subflow(
            ip, ports, sub_name, is_same_tmysql_version, root_id, ticket_data, pkg_id, cluster, is_check_process
        )
        upgrade_pipelines.append(upgrade_pipeline)
        processed_instances.append(f"{ip}:{','.join(map(str, ports))}")

    if processed_instances:
        import logging

        logger = logging.getLogger("flow")
        logger.info(_("构建了 {} 个{}升级子流程: {}").format(len(upgrade_pipelines), role_type, ", ".join(processed_instances)))
    else:
        import logging

        logger = logging.getLogger("flow")
        logger.warning(_("没有找到需要升级的{}实例").format(role_type))

    return upgrade_pipelines


def build_upgrade_mysql_subflow(
    ip: str,
    ports: List[int],
    sub_name: str,
    is_same_tmysql_version: bool,
    root_id: str,
    ticket_data: Dict,
    pkg_id: int,
    new_mysql_version: str,
    cluster: Cluster,
    is_check_process: bool,
):
    """
    构建MySQL升级子流程

    Args:
        ip: IP地址
        ports: 端口列表
        sub_name: 子流程名称
        is_same_tmysql_version: 是否相同tmysql版本
        root_id: 根ID
        ticket_data: 单据数据
        pkg_id: 包ID
        cluster: 集群对象

    Returns:
        SubBuilder: 升级子流程
    """
    sub_pipeline = SubBuilder(root_id=root_id, data=copy.deepcopy(ticket_data))
    bk_cloud_id = cluster.bk_cloud_id
    if is_check_process:
        sub_pipeline.add_act(
            act_name=_("检查{}的Mysql{}连接情况").format(ip, ",".join(map(str, ports))),
            act_component_code=CheckClientConnComponent.code,
            kwargs=asdict(
                CheckClientConnKwargs(
                    bk_cloud_id=bk_cloud_id,
                    check_instances=[f"{ip}:{port}" for port in ports],
                    is_filter_sleep=True,
                )
            ),
        )
    sub_pipeline.add_sub_pipeline(
        sub_flow=mysql_upgrade_subflow(
            uid=ticket_data.get("uid"),
            root_id=root_id,
            parent_global_data=copy.deepcopy(ticket_data),
            bk_cloud_id=bk_cloud_id,
            ip=ip,
            mysql_ports=ports,
            pkg_id=pkg_id,
            sub_flow_name=sub_name,
            skip_send_pkg=True,  # 如果跳过预检查，通常也跳过发包
            is_same_tmysql_version=is_same_tmysql_version,
        )
    )
    # 更新mysql instance version信息
    sub_pipeline.add_act(
        act_name=_("更新mysql instance version meta信息 {}").format(ip),
        act_component_code=MySQLDBMetaComponent.code,
        kwargs=asdict(
            DBMetaOPKwargs(
                db_meta_class_func=MySQLDBMeta.update_mysql_instance_version.__name__,
                cluster={"ip": ip, "version": new_mysql_version},
            )
        ),
    )

    return sub_pipeline.build_sub_process(sub_name=sub_name)


def build_spider_upgrade_subflow(
    ip: str,
    bk_cloud_id: int,
    pkg_id: int,
    spider_version: str,
    spider_port: int,
    spider_role: str,
    cluster_id: int,
    force_upgrade: bool,
    sub_flow_context: Dict,
    root_id: str,
):
    """
    定义upgrade tendbcluster spider 本地升级 的flow

    Args:
        ip: IP地址
        bk_cloud_id: 云区域ID
        pkg_id: 包ID
        domain: 域名
        spider_version: spider版本
        spider_port: spider端口
        force_upgrade: 是否强制升级
        sub_flow_context: 子流程上下文
        root_id: 根ID

    Returns:
        SubBuilder: spider升级子流程
    """
    sub_pipeline = SubBuilder(root_id=root_id, data=copy.deepcopy(sub_flow_context))

    # 执行本地升级
    # 回收对应的域名关系
    entry_role = ClusterEntryRole.MASTER_ENTRY.value
    if spider_role == TenDBClusterSpiderRole.SPIDER_SLAVE.value:
        entry_role = ClusterEntryRole.SLAVE_ENTRY.value

    disable_entry_process = BuildEntrysManageSubflow(
        root_id=root_id,
        ticket_data=copy.deepcopy(sub_flow_context),
        op_type=DnsOpType.DISABLE,
        param={
            "cluster_id": cluster_id,
            "port": spider_port,
            "del_ips": [ip],
        },
    )
    enable_entry_process = BuildEntrysManageSubflow(
        root_id=root_id,
        ticket_data=copy.deepcopy(sub_flow_context),
        op_type=DnsOpType.ENABLE,
        param={
            "cluster_id": cluster_id,
            "port": spider_port,
            "add_ips": [ip],
            "entry_role": [entry_role],
        },
    )
    sub_pipeline.add_sub_pipeline(sub_flow=disable_entry_process)
    cluster = {"proxy_ports": [spider_port], "pkg_id": pkg_id, "force_upgrade": force_upgrade}
    exec_act_kwargs = ExecActuatorKwargs(cluster=cluster, bk_cloud_id=bk_cloud_id)
    exec_act_kwargs.exec_ip = ip
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_spider_upgrade_payload.__name__

    sub_pipeline.add_act(
        act_name=_("更新spider instance status -> upgrade"),
        act_component_code=MySQLDBMetaComponent.code,
        kwargs=asdict(
            DBMetaOPKwargs(
                db_meta_class_func=MySQLDBMeta.update_proxy_instance_status.__name__,
                cluster={"proxy_ip": ip, "phase": InstancePhase.UPGRADING, "status": InstanceStatus.UPGRADING},
            )
        ),
    )

    sub_pipeline.add_act(
        act_name=_("执行本地升级"),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
    )

    # 更新proxy instance version 信息
    act_list = []
    act_list.append(
        {
            "act_name": _("更新spider version meta信息"),
            "act_component_code": MySQLDBMetaComponent.code,
            "kwargs": asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=MySQLDBMeta.update_proxy_instance_version.__name__,
                    cluster={"proxy_ip": ip, "version": spider_version},
                )
            ),
        }
    )
    act_list.append(
        {
            "act_name": _("更新spider instance status -> online"),
            "act_component_code": MySQLDBMetaComponent.code,
            "kwargs": asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=MySQLDBMeta.update_proxy_instance_status.__name__,
                    cluster={"proxy_ip": ip, "phase": InstancePhase.ONLINE, "status": InstanceStatus.RUNNING},
                )
            ),
        }
    )
    sub_pipeline.add_parallel_acts(act_list)

    sub_pipeline.add_sub_pipeline(sub_flow=enable_entry_process)
    return sub_pipeline.build_sub_process(sub_name=_("[{}]{}升级").format(spider_role, ip))


def add_spider_alarm_shield_act(sub_pipeline, cluster: Cluster, shield_hours: int = 2) -> None:
    """
    添加spider告警屏蔽活动

    Args:
        sub_pipeline: 子流程
        cluster: 集群对象
        shield_hours: 屏蔽小时数
    """
    # 获取集群的所有spider实例IP
    spider_ips = list(cluster.proxyinstance_set.values_list("machine__ip", flat=True).distinct())

    sub_pipeline.add_act(
        act_name=_("屏蔽集群 {} spider节点告警{}小时").format(cluster.name, shield_hours),
        act_component_code=AddAlarmShieldComponent.code,
        kwargs={
            "begin_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": (datetime.datetime.now() + timedelta(hours=shield_hours)).strftime("%Y-%m-%d %H:%M:%S"),
            "description": _("集群 {} spider节点升级操作").format(cluster.immute_domain),
            "dimensions": [
                {
                    "name": "instance_host",
                    "values": spider_ips,
                }
            ],
        },
    )


def add_spider_disable_alarm_shield_act(sub_pipeline) -> None:
    """
    添加解除spider告警屏蔽活动

    Args:
        sub_pipeline: 子流程
    """
    sub_pipeline.add_act(act_name=_("解除告警屏蔽"), act_component_code=DisableAlarmShieldComponent.code, kwargs={})


def add_spider_upgrade_check_act(sub_pipeline, spider_master_ins: List, bk_cloud_id: int, check_process: bool) -> None:
    """
    添加spider升级检查活动

    Args:
        sub_pipeline: 子流程
        cluster_id: 集群ID
        spider_master_ins: spider master实例列表
        bk_cloud_id: 云区域ID
        force_upgrade: 是否强制升级
    """
    if check_process:
        sub_pipeline.add_act(
            act_name=_("检查Master Spider端连接情况"),
            act_component_code=CheckClientConnComponent.code,
            kwargs=asdict(
                CheckClientConnKwargs(
                    bk_cloud_id=bk_cloud_id,
                    check_instances=spider_master_ins,
                )
            ),
        )


def add_spider_media_download_act(sub_pipeline, spider_ips: List, pkg_id: int, bk_cloud_id: int) -> None:
    """
    添加spider介质下发活动

    Args:
        sub_pipeline: 子流程
        spider_ips: spider IP列表
        pkg_id: 包ID
        bk_cloud_id: 云区域ID
    """
    sub_pipeline.add_act(
        act_name=_("下发升级的安装包"),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(
            DownloadMediaKwargs(
                bk_cloud_id=bk_cloud_id,
                exec_ip=spider_ips,
                file_list=GetFileList(db_type=DBType.MySQL).spider_upgrade_package(pkg_id=pkg_id),
            )
        ),
    )


def add_spider_keyword_check_act(
    sub_pipeline, cluster_id: int, from_version_map: Dict, to_version: str, force_upgrade: bool
) -> None:
    """
    添加spider关键字检查活动

    Args:
        sub_pipeline: 子流程
        cluster_id: 集群ID
        from_version_map: 源版本映射
        to_version: 目标版本
        force_upgrade: 是否强制升级
    """
    sub_pipeline.add_act(
        act_name=_("升级前关键字检查"),
        act_component_code=UpgradeKeyWordCheckComponent.code,
        kwargs=asdict(
            UpgradeKeyWordCheckKwargs(
                cluster_id=cluster_id,
                from_version_map=from_version_map,
                to_version=to_version,
                check_types=BASIC_CHECK_TYPES,
                fail_on_conflict=not force_upgrade,
            )
        ),
    )


def add_standardize_act(sub_pipeline, instances: List, root_id: str, ticket_data: Dict, cluster: Cluster) -> None:
    """
    添加标准化活动

    Args:
        sub_pipeline: 子流程
        instances: 实例列表
        root_id: 根ID
        ticket_data: 单据数据
        cluster: 集群对象
    """
    sub_pipeline.add_sub_pipeline(
        sub_flow=standardize_mysql_cluster_subflow(
            root_id=root_id,
            data=copy.deepcopy(ticket_data),
            bk_cloud_id=cluster.bk_cloud_id,
            bk_biz_id=cluster.bk_biz_id,
            instances=[f"{instance.machine.ip}:{instance.port}" for instance in instances],
            with_actuator=False,
            with_bk_plugin=False,
            with_collect_sysinfo=False,
            with_cc_standardize=False,
            with_instance_standardize=False,
        )
    )


def add_cluster_module_update_act(sub_pipeline, cluster_id: int, new_db_module_id: int) -> None:
    """
    添加集群模块更新活动

    Args:
        sub_pipeline: 子流程
        cluster_id: 集群ID
        new_db_module_id: 新数据库模块ID
    """
    sub_pipeline.add_act(
        act_name=_("更新集群db模块信息"),
        act_component_code=MySQLDBMetaComponent.code,
        kwargs=asdict(
            DBMetaOPKwargs(
                db_meta_class_func=MySQLDBMeta.update_cluster_module.__name__,
                cluster={
                    "cluster_ids": [cluster_id],
                    "new_module_id": new_db_module_id,
                },
            )
        ),
    )
