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
from dataclasses import asdict
from typing import Dict, List, Optional, Tuple

from django.utils.translation import gettext as _

from backend.components.db_remote_service.client import DRSApi
from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterType, TenDBClusterSpiderRole
from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import Cluster
from backend.db_package.models import Package
from backend.db_report.enums import TdbctlInstanceRole, TdbctlUpgradeStatus
from backend.db_report.models import TdbctlUpgradeRecord
from backend.flow.consts import DBA_ROOT_USER, MediumEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.common.delay import DelayComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_check_slave_delay import MySQLCheckSlaveDelayComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.spider.tdbctl_pre_upgrade_check import TdbctlPreUpgradeCheckComponent
from backend.flow.plugins.components.collections.spider.tdbctl_upgrade_status_update import (
    TdbctlUpgradeStatusUpdateComponent,
)
from backend.flow.utils.mysql.mysql_act_dataclass import (
    CheckSlaveStatusKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_version_parse import get_online_mysql_version, tdbctl_version_parse

logger = logging.getLogger("flow")


def _record_upgrade_status(
    cluster: Cluster,
    instances: List[Dict],
    target_version: str,
    pkg_id: int,
    task_id: str,
    status: str,
    batch_id: str = "",
    operator: str = "system",
    error_msg: str = "",
    is_primary_list: List[bool] = None,
    current_versions: List[str] = None,
):
    """
    记录 tdbctl 实例的升级状态

    @param cluster: 集群对象
    @param instances: tdbctl 实例列表，格式：[{"ip": "x.x.x.x", "port": 4306, "spider_port": 3306}]
    @param target_version: 目标版本
    @param pkg_id: 升级包ID
    @param task_id: 关联的flow任务ID
    @param status: 升级状态
    @param batch_id: 批次ID
    @param operator: 操作人
    @param error_msg: 错误信息
    @param is_primary_list: 是否是 primary 的列表（与 instances 对应）
    @param current_versions: 当前版本的列表（与 instances 对应）
    """
    if not instances:
        return

    for idx, instance in enumerate(instances):
        ip = instance["ip"]
        port = instance["port"]
        spider_port = instance.get("spider_port", 0)

        # 确定实例角色
        is_primary = is_primary_list[idx] if is_primary_list and idx < len(is_primary_list) else False
        instance_role = TdbctlInstanceRole.PRIMARY.value if is_primary else TdbctlInstanceRole.SECONDARY.value

        # 获取当前版本
        current_version = current_versions[idx] if current_versions and idx < len(current_versions) else ""

        try:
            # 使用 update_or_create 更新或创建记录
            record, created = TdbctlUpgradeRecord.objects.update_or_create(
                ip=ip,
                port=port,
                defaults={
                    "bk_biz_id": cluster.bk_biz_id,
                    "bk_cloud_id": cluster.bk_cloud_id,
                    "cluster_id": cluster.id,
                    "cluster_domain": cluster.immute_domain,
                    "spider_port": spider_port,
                    "instance_role": instance_role,
                    "current_version": current_version,
                    "target_version": target_version,
                    "status": status,
                    "task_id": task_id,
                    "pkg_id": pkg_id,
                    "batch_id": batch_id,
                    "error_msg": error_msg,
                    "updater": operator,
                },
            )

            # 如果是新创建的记录，设置创建者
            if created:
                record.creator = operator
                record.upgrade_count = 1
                record.save(update_fields=["creator", "upgrade_count"])
            else:
                # 如果是更新记录，增加升级次数（仅当状态从非 RUNNING 变为 RUNNING 时）
                if status == TdbctlUpgradeStatus.RUNNING.value:
                    record.upgrade_count = (record.upgrade_count or 0) + 1
                    record.save(update_fields=["upgrade_count"])

            # 追加历史记录
            record.append_history(
                from_version=current_version,
                to_version=target_version,
                status=status,
                task_id=task_id,
                operator=operator,
                error_msg=error_msg,
            )
            record.save(update_fields=["upgrade_history"])

            action = _("创建") if created else _("更新")
            logger.info(_("{}升级记录: {}:{}, 状态={}, task_id={}").format(action, ip, port, status, task_id))

        except Exception as e:
            logger.error(_("记录升级状态失败: {}:{}, 错误: {}").format(ip, port, str(e)))


def _record_skipped_instances(
    cluster: Cluster,
    instances: List[Dict],
    target_version: str,
    pkg_id: int,
    task_id: str,
    operator: str = "system",
    current_versions: List[str] = None,
):
    """
    记录跳过升级的实例（版本已是最新）

    @param cluster: 集群对象
    @param instances: tdbctl 实例列表
    @param target_version: 目标版本
    @param pkg_id: 升级包ID
    @param task_id: 关联的flow任务ID
    @param operator: 操作人
    @param current_versions: 当前版本列表
    """
    _record_upgrade_status(
        cluster=cluster,
        instances=instances,
        target_version=target_version,
        pkg_id=pkg_id,
        task_id=task_id,
        status=TdbctlUpgradeStatus.SKIPPED.value,
        operator=operator,
        current_versions=current_versions,
    )


def _get_tdbctl_instances(cluster: Cluster) -> List[Dict]:
    """
    获取集群中所有 tdbctl 实例列表
    tdbctl 只部署在 spider master 角色的机器上，端口 = spider_port + 1000

    @param cluster: 集群对象
    @return: tdbctl 实例列表，格式：[{"ip": "x.x.x.x", "port": 4306, "spider_port": 3306}]
    """
    tdbctl_instances = []
    spider_masters = cluster.proxyinstance_set.filter(
        tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER.value
    )
    for spider in spider_masters:
        tdbctl_instances.append(
            {
                "ip": spider.machine.ip,
                "port": spider.port + 1000,  # tdbctl 端口 = spider_port + 1000
                "spider_port": spider.port,
            }
        )
    return tdbctl_instances


def _check_tdbctl_is_primary(ip: str, port: int, bk_cloud_id: int) -> bool:
    """
    检查 tdbctl 实例是否是 primary (master)

    @param ip: tdbctl IP
    @param port: tdbctl 端口
    @param bk_cloud_id: 云区域ID
    @return: True 表示是 primary，False 表示是 slave
    """
    ctl_address = "{}{}{}".format(ip, IP_PORT_DIVIDER, port)
    try:
        res = DRSApi.short_rpc(
            {
                "addresses": [ctl_address],
                "cmds": ["tdbctl get primary"],
                "force": False,
                "bk_cloud_id": bk_cloud_id,
            }
        )
        if res[0]["error_msg"]:
            logger.error(_("执行 tdbctl get primary 失败: {}").format(res[0]["error_msg"]))
            return False

        primary_info_table_data = res[0]["cmd_results"][0]["table_data"]
        if primary_info_table_data:
            # IS_THIS_SERVER 字段为 "1" 表示当前实例是 primary
            is_this_server = primary_info_table_data[0].get("IS_THIS_SERVER", "0")
            return is_this_server == "1"
        return False
    except Exception as e:
        logger.error(_("检查 tdbctl primary 状态失败: {}").format(str(e)))
        return False


def _filter_upgrade_instances(
    tdbctl_instances: List[Dict], pkg_id: int, bk_cloud_id: int
) -> Tuple[List[Dict], List[Dict], str, List[Dict], List[str]]:
    """
    过滤需要升级的 tdbctl 实例，并区分 master 和 slave

    @param tdbctl_instances: tdbctl 实例列表
    @param pkg_id: 升级包ID
    @param bk_cloud_id: 云区域ID
    @return: (需要升级的 slave 实例列表, 需要升级的 master 实例列表, 目标版本, 跳过的实例列表, 跳过实例的当前版本列表)
    """
    # 获取目标包版本
    try:
        pkg = Package.objects.get(id=pkg_id, pkg_type=MediumEnum.tdbCtl, db_type=DBType.MySQL)
        target_version = pkg.name
        target_version_num = tdbctl_version_parse(target_version)
    except Package.DoesNotExist:
        logger.error(_("升级包 {} 不存在").format(pkg_id))
        raise
    except Exception as e:
        logger.error(_("获取升级包信息失败: {}").format(str(e)))
        raise

    slave_instances = []
    master_instances = []
    skipped_instances = []
    skipped_versions = []

    # 用于存储实例的当前版本和是否是 primary
    instance_versions = {}
    instance_is_primary = {}

    for instance in tdbctl_instances:
        ip = instance["ip"]
        port = instance["port"]
        instance_key = f"{ip}:{port}"

        # 查询当前版本
        try:
            current_version = get_online_mysql_version(ip, port, bk_cloud_id)
            if not current_version:
                logger.warning(_("tdbctl 实例 {}:{} 版本查询返回空，跳过").format(ip, port))
                continue

            # mock version for test
            # current_version = "tdbctl-2.4.11"
            instance_versions[instance_key] = current_version

            # 使用 tdbctl_version_parse 解析版本（支持包文件名格式和在线版本格式）
            current_version_num = tdbctl_version_parse(current_version)
            if current_version_num == 0:
                logger.warning(_("tdbctl 实例 {}:{} 版本解析失败: {}，跳过").format(ip, port, current_version))
                continue

            # 如果当前版本 >= 目标版本，跳过
            if current_version_num >= target_version_num:
                logger.info(
                    _("tdbctl 实例 {}:{} 当前版本 {} >= 目标版本 {}，跳过升级").format(ip, port, current_version, target_version)
                )
                skipped_instances.append(instance)
                skipped_versions.append(current_version)
                continue

            logger.info(_("tdbctl 实例 {}:{} 当前版本 {} < 目标版本 {}，需要升级").format(ip, port, current_version, target_version))

            # 检查是否是 primary
            try:
                is_primary = _check_tdbctl_is_primary(ip, port, bk_cloud_id)
                instance_is_primary[instance_key] = is_primary
                instance["current_version"] = current_version
                instance["is_primary"] = is_primary
                if is_primary:
                    master_instances.append(instance)
                    logger.info(_("tdbctl 实例 {}:{} 是 primary (master)").format(ip, port))
                else:
                    slave_instances.append(instance)
                    logger.info(_("tdbctl 实例 {}:{} 是 slave").format(ip, port))
            except Exception as e:
                logger.warning(_("检查 tdbctl 实例 {}:{} primary 状态失败: {}，默认作为 slave 处理").format(ip, port, str(e)))
                # 如果无法判断，默认作为 slave 处理（更安全）
                instance["current_version"] = current_version
                instance["is_primary"] = False
                instance_is_primary[instance_key] = False
                slave_instances.append(instance)

        except Exception as e:
            logger.error(_("查询 tdbctl 实例 {}:{} 版本失败: {}").format(ip, port, str(e)))
            # 如果查询版本失败，为了安全起见，跳过该实例
            continue

    return slave_instances, master_instances, target_version, skipped_instances, skipped_versions


def _get_primary_address_from_cluster(cluster: Cluster) -> Tuple[Optional[str], Optional[int]]:
    """
    从集群获取 primary 地址

    @param cluster: 集群对象
    @return: (primary_ip, primary_port) 或 (None, None)
    """
    try:
        primary_address = cluster.tendbcluster_ctl_primary_address()
        primary_ip, primary_port_str = primary_address.split(IP_PORT_DIVIDER)
        primary_port = int(primary_port_str)
        return primary_ip, primary_port
    except Exception as e:
        logger.warning(_("获取 primary 地址失败: {}").format(str(e)))
        return None, None


def _get_primary_address(
    master_instances: List[Dict], cluster: Cluster, fallback_to_cluster: bool = True
) -> Tuple[Optional[str], Optional[int]]:
    """
    获取主节点地址，优先从 master_instances 获取，如果没有则从集群获取

    @param master_instances: master 实例列表
    @param cluster: 集群对象
    @param fallback_to_cluster: 如果没有 master_instances，是否从集群获取
    @return: (primary_ip, primary_port) 或 (None, None)
    """
    if master_instances:
        return master_instances[0]["ip"], master_instances[0]["port"]
    elif fallback_to_cluster:
        return _get_primary_address_from_cluster(cluster)
    return None, None


def _add_tdbctl_media_download(
    sub_pipeline: SubBuilder,
    instances: List[Dict],
    pkg_id: int,
    bk_cloud_id: int,
):
    """
    统一下发 tdbctl 升级介质到所有需要升级的主机

    @param sub_pipeline: 子流程构建器
    @param instances: tdbctl 实例列表
    @param pkg_id: 升级包ID
    @param bk_cloud_id: 云区域ID
    """
    if not instances:
        return

    # 收集所有唯一的主机IP
    unique_hosts = sorted(set(instance["ip"] for instance in instances))
    if not unique_hosts:
        return

    logger.info(_("统一下发tdbctl升级包到 {} 个主机: {}").format(len(unique_hosts), ", ".join(unique_hosts)))

    sub_pipeline.add_act(
        act_name=_("统一下发tdbctl升级包到所有主机({})").format(len(unique_hosts)),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(
            DownloadMediaKwargs(
                bk_cloud_id=bk_cloud_id,
                exec_ip=unique_hosts,
                file_list=GetFileList(db_type=DBType.MySQL).tdbctl_upgrade_package(pkg_id=pkg_id),
            )
        ),
    )


def _add_upgrade_status_update_act(
    sub_pipeline: SubBuilder,
    cluster_id: int,
    instances: List[Dict],
    target_version: str,
    pkg_id: int,
    task_id: str,
    status: str,
    batch_id: str = "",
    operator: str = "system",
    is_primary_list: List[bool] = None,
    current_versions: List[str] = None,
    act_name: str = None,
):
    """
    添加升级状态更新的 act

    @param sub_pipeline: 子流程构建器
    @param cluster_id: 集群ID
    @param instances: tdbctl 实例列表
    @param target_version: 目标版本
    @param pkg_id: 升级包ID
    @param task_id: 关联的flow任务ID
    @param status: 升级状态
    @param batch_id: 批次ID
    @param operator: 操作人
    @param is_primary_list: 是否是 primary 的列表
    @param current_versions: 当前版本的列表
    @param act_name: act 名称
    """
    if not instances:
        return

    if act_name is None:
        if status == TdbctlUpgradeStatus.RUNNING.value:
            act_name = _("记录升级开始状态")
        elif status == TdbctlUpgradeStatus.SUCCESS.value:
            act_name = _("记录升级成功状态")
        else:
            act_name = _("更新升级状态为{}").format(status)

    sub_pipeline.add_act(
        act_name=act_name,
        act_component_code=TdbctlUpgradeStatusUpdateComponent.code,
        kwargs={
            "cluster_id": cluster_id,
            "instances": instances,
            "target_version": target_version,
            "pkg_id": pkg_id,
            "task_id": task_id,
            "status": status,
            "batch_id": batch_id,
            "operator": operator,
            "is_primary_list": is_primary_list or [],
            "current_versions": current_versions or [],
        },
    )


def _add_pre_upgrade_check(
    sub_pipeline: SubBuilder, primary_ip: Optional[str], primary_port: Optional[int], bk_cloud_id: int
):
    """
    添加升级前检查步骤

    @param sub_pipeline: 子流程构建器
    @param primary_ip: 主节点IP
    @param primary_port: 主节点端口
    @param bk_cloud_id: 云区域ID
    """
    if primary_ip and primary_port:
        sub_pipeline.add_act(
            act_name=_("升级前检查[{}:{}]").format(primary_ip, primary_port),
            act_component_code=TdbctlPreUpgradeCheckComponent.code,
            kwargs={
                "ip": primary_ip,
                "port": primary_port,
                "bk_cloud_id": bk_cloud_id,
            },
        )


def _add_slave_upgrade_steps(
    sub_pipeline: SubBuilder,
    root_id: str,
    parent_global_data: dict,
    bk_cloud_id: int,
    slave_instances: List[Dict],
    master_ip: Optional[str],
    master_port: Optional[int],
    pkg_id: int,
):
    """
    添加 slave 升级步骤

    @param sub_pipeline: 子流程构建器
    @param root_id: flow流程的root_id
    @param parent_global_data: 父流程的全局数据
    @param bk_cloud_id: 云区域ID
    @param slave_instances: slave 实例列表
    @param master_ip: master IP（保留参数，用于后续复制检查）
    @param master_port: master 端口（保留参数，用于后续复制检查）
    @param pkg_id: 升级包ID
    """
    if not slave_instances:
        return

    # 构建所有 slave 的升级子流程
    slave_sub_flows = []
    for slave_instance in slave_instances:
        slave_sub_flow = _build_tdbctl_upgrade_subflow_for_instance(
            root_id=root_id,
            parent_global_data=parent_global_data,
            bk_cloud_id=bk_cloud_id,
            instance=slave_instance,
            pkg_id=pkg_id,
            sub_flow_name=_("tdbctl slave升级[{}:{}]").format(slave_instance["ip"], slave_instance["port"]),
        )
        slave_sub_flows.append(slave_sub_flow)

    # 并行升级所有 slave
    sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=slave_sub_flows)


def _add_master_upgrade_steps(
    sub_pipeline: SubBuilder,
    root_id: str,
    parent_global_data: dict,
    bk_cloud_id: int,
    master_instances: List[Dict],
    pkg_id: int,
):
    """
    添加 master 升级步骤

    @param sub_pipeline: 子流程构建器
    @param root_id: flow流程的root_id
    @param parent_global_data: 父流程的全局数据
    @param bk_cloud_id: 云区域ID
    @param master_instances: master 实例列表
    @param pkg_id: 升级包ID
    """
    if not master_instances:
        return

    if len(master_instances) > 1:
        logger.warning(_("发现多个 master tdbctl 实例，这不应该发生"))

    # 串行升级 master（通常只有一个）
    for master_instance in master_instances:
        master_sub_flow = _build_tdbctl_upgrade_subflow_for_instance(
            root_id=root_id,
            parent_global_data=parent_global_data,
            bk_cloud_id=bk_cloud_id,
            instance=master_instance,
            pkg_id=pkg_id,
            sub_flow_name=_("tdbctl master升级[{}:{}]").format(master_instance["ip"], master_instance["port"]),
        )
        sub_pipeline.add_sub_pipeline(sub_flow=master_sub_flow)


def _add_post_upgrade_checks_parallel(
    sub_pipeline: SubBuilder,
    cluster: Cluster,
    slave_instances: List[Dict],
    master_ip: Optional[str],
    master_port: Optional[int],
    bk_cloud_id: int,
):
    """
    并行添加升级后检查步骤（包括 master 升级后检查和 slave 复制状态检查）

    @param sub_pipeline: 子流程构建器
    @param cluster: 集群对象
    @param slave_instances: slave 实例列表
    @param master_ip: 升级前的 master IP（作为 fallback）
    @param master_port: 升级前的 master 端口（作为 fallback）
    @param bk_cloud_id: 云区域ID
    """
    acts_list = []

    # 1. 添加 master 升级后检查
    # 重新获取 primary 地址（可能因为升级后发生变化）
    post_check_primary_ip, post_check_primary_port = _get_primary_address_from_cluster(cluster)

    # 如果获取失败，使用升级前的地址
    if not (post_check_primary_ip and post_check_primary_port):
        logger.warning(_("升级后获取 primary 地址失败，使用升级前的地址"))
        post_check_primary_ip = master_ip
        post_check_primary_port = master_port

    if post_check_primary_ip and post_check_primary_port:
        acts_list.append(
            {
                "act_name": _("升级后检查[{}:{}]").format(post_check_primary_ip, post_check_primary_port),
                "act_component_code": TdbctlPreUpgradeCheckComponent.code,
                "kwargs": {
                    "ip": post_check_primary_ip,
                    "port": post_check_primary_port,
                    "bk_cloud_id": bk_cloud_id,
                    "check_type": "post_upgrade",
                },
            }
        )

    # 2. 添加 slave 复制状态检查（如果有 slave 实例）
    if slave_instances and master_ip and master_port:
        for slave_instance in slave_instances:
            acts_list.append(
                {
                    "act_name": _("升级后检查tdbctl slave复制状态[{}:{}]").format(slave_instance["ip"], slave_instance["port"]),
                    "act_component_code": MySQLCheckSlaveDelayComponent.code,
                    "kwargs": asdict(
                        CheckSlaveStatusKwargs(
                            bk_cloud_id=bk_cloud_id,
                            instance_ip=slave_instance["ip"],
                            instance_port=slave_instance["port"],
                            master_ip=master_ip,
                            master_port=master_port,
                            slave_delay_threshold=360,
                            rounds=12,
                        )
                    ),
                }
            )

    # 并行执行所有检查
    if acts_list:
        sub_pipeline.add_parallel_acts(acts_list=acts_list)


def _build_tdbctl_upgrade_subflow_for_instance(
    root_id: str,
    parent_global_data: dict,
    bk_cloud_id: int,
    instance: Dict,
    pkg_id: int,
    sub_flow_name: str = None,
) -> SubBuilder:
    """
    为单个 tdbctl 实例构建升级子流程

    注意：此函数不再包含下发介质步骤，介质已由主流程统一下发

    @param root_id: flow流程的root_id
    @param parent_global_data: 父流程的全局数据
    @param bk_cloud_id: 云区域ID
    @param instance: tdbctl 实例信息，格式：{"ip": "x.x.x.x", "port": 4306}
    @param pkg_id: 升级包ID
    @param sub_flow_name: 子流程名称
    @return: SubBuilder对象
    """
    ip = instance["ip"]
    port = instance["port"]

    if sub_flow_name is None:
        sub_flow_name = _("tdbctl升级[{}:{}]").format(ip, port)

    # 创建子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=parent_global_data)

    # ============ 步骤1: MySQL重新链接版本介质 ============
    relink_kwargs = ExecActuatorKwargs(
        bk_cloud_id=bk_cloud_id,
        exec_ip=ip,
        run_as_system_user=DBA_ROOT_USER,
        cluster={
            "pkg_id": pkg_id,
        },
        get_mysql_payload_func=MysqlActPayload.get_tdbctl_upgrade_relink_payload.__name__,
    )
    sub_pipeline.add_act(
        act_name=_("tdbctl重新链接版本介质[{}:{}]").format(ip, port),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(relink_kwargs),
    )

    # ============ 步骤2: upgrade_restart (重启服务) ============
    restart_kwargs = ExecActuatorKwargs(
        bk_cloud_id=bk_cloud_id,
        exec_ip=ip,
        run_as_system_user=DBA_ROOT_USER,
        cluster={
            "port": port,
            "pkg_id": pkg_id,
        },
        get_mysql_payload_func=MysqlActPayload.get_tdbctl_restart_payload.__name__,
    )
    sub_pipeline.add_act(
        act_name=_("重启tdbctl[{}:{}]").format(ip, port),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(restart_kwargs),
    )

    return sub_pipeline.build_sub_process(sub_name=sub_flow_name)


def tdbctl_upgrade_subflow(
    uid: str,
    root_id: str,
    parent_global_data: dict,
    bk_cloud_id: int,
    cluster_id: int,
    pkg_id: int,
    sub_flow_name: str = None,
    batch_id: str = "",
    operator: str = "system",
) -> SubBuilder:
    """
    tdbctl 升级子流程，用于升级 TendbCluster 集群中的 tdbctl（中控）组件

    重要要求：
    - 必须存在 master tdbctl 实例，否则会抛出异常退出

    升级顺序（重要）：
    1. 并行升级所有 tdbctl 从节点（slave）
    2. 升级 tdbctl 主节点（master）

    详细流程：
    1. 获取所有 tdbctl 实例（部署在 spider master 机器上）
    2. 检查版本，过滤掉不需要升级的实例
    3. 区分 master 和 slave
    4. 验证必须存在 master 中控实例，否则抛出异常退出
    5. 【步骤0】记录升级开始状态（通过 act 延迟执行，避免流程构建失败导致状态不一致）
    6. 【步骤1】升级前检查（在主节点上执行）：
       - TDBCTL GET PRIMARY 获取主节点成功，且为当前节点
       - 执行 select * from information_schema.tdbctl_nodes; 检查：
         * 每个节点的 STATUS 均为 Online
         * 每个从 TDBCTL 节点的角色为 Secondary
    7. 【步骤2】统一下发介质到所有主机（一次性下发）
    8. 【步骤3】并行升级所有 slave tdbctl（不再包含下发介质）
    9. 【步骤4】串行升级 master tdbctl（不再包含下发介质）
    10. 【步骤5】并行执行升级后检查：
        - master 升级后检查（在主节点上执行，检查项同步骤1）
        - slave 复制状态检查（并行执行所有 slave，如果有 slave）
    11. 【步骤6】记录升级成功状态（只有流程执行成功才会记录）

    @param uid: 流程单据的uid
    @param root_id: flow流程的root_id
    @param parent_global_data: 父流程的全局数据
    @param bk_cloud_id: 云区域ID
    @param cluster_id: 集群ID
    @param pkg_id: 升级包ID
    @param sub_flow_name: 子流程名称
    @param batch_id: 批次ID（用于全局调度）
    @param operator: 操作人
    @return: SubBuilder对象
    @raises DBMetaException: 如果不存在 master tdbctl 实例
    """
    if sub_flow_name is None:
        sub_flow_name = _("tdbctl升级")

    # 获取集群对象
    cluster = Cluster.objects.get(id=cluster_id)

    # 创建子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=parent_global_data)

    # ============ 步骤1: 获取所有 tdbctl 实例并过滤需要升级的实例 ============
    tdbctl_instances = _get_tdbctl_instances(cluster)
    if not tdbctl_instances:
        logger.warning(_("集群 {} 中没有找到 tdbctl 实例").format(cluster_id))
        return sub_pipeline.build_sub_process(sub_name=sub_flow_name)

    slave_instances, master_instances, target_version, skipped_instances, skipped_versions = _filter_upgrade_instances(
        tdbctl_instances, pkg_id, bk_cloud_id
    )

    # 记录跳过升级的实例（版本已是最新）
    if skipped_instances:
        _record_skipped_instances(
            cluster=cluster,
            instances=skipped_instances,
            target_version=target_version,
            pkg_id=pkg_id,
            task_id=root_id,
            operator=operator,
            current_versions=skipped_versions,
        )

    if not slave_instances and not master_instances:
        logger.info(_("集群 {} 中所有 tdbctl 实例都已是最新版本，无需升级").format(cluster_id))
        return sub_pipeline.build_sub_process(sub_name=sub_flow_name)

    # 检查是否存在 master 中控，如果没有则报错退出
    # 注意：必须存在 master tdbctl 实例才能进行升级，因为升级流程需要 master 进行各种检查和协调
    if not master_instances:
        error_msg = _("集群 {} 中不存在需要升级的 master tdbctl 实例，无法进行升级。tdbctl 升级流程必须存在 master 中控实例").format(cluster_id)
        logger.error(error_msg)
        raise DBMetaException(message=error_msg)

    logger.info(
        _("集群 {} 需要升级的 tdbctl 实例: slave={}, master={}").format(cluster_id, len(slave_instances), len(master_instances))
    )

    # 收集所有需要升级的实例和状态信息（用于后续 act）
    all_upgrade_instances = slave_instances + master_instances
    is_primary_list = [inst.get("is_primary", False) for inst in all_upgrade_instances]
    current_versions = [inst.get("current_version", "") for inst in all_upgrade_instances]

    # ============ 步骤0: 记录升级开始状态（通过 act 延迟执行，避免流程构建失败导致状态不一致） ============
    _add_upgrade_status_update_act(
        sub_pipeline=sub_pipeline,
        cluster_id=cluster_id,
        instances=all_upgrade_instances,
        target_version=target_version,
        pkg_id=pkg_id,
        task_id=root_id,
        status=TdbctlUpgradeStatus.RUNNING.value,
        batch_id=batch_id,
        operator=operator,
        is_primary_list=is_primary_list,
        current_versions=current_versions,
    )

    # ============ 步骤1: 升级前检查（在主节点上执行） ============
    # master_instances 一定存在（前面已校验），可以直接获取主节点地址
    primary_ip, primary_port = _get_primary_address(master_instances, cluster, fallback_to_cluster=False)
    _add_pre_upgrade_check(sub_pipeline, primary_ip, primary_port, bk_cloud_id)

    # ============ 步骤2: 统一下发介质到所有主机 ============
    _add_tdbctl_media_download(sub_pipeline, all_upgrade_instances, pkg_id, bk_cloud_id)

    # ============ 步骤3: 并行升级所有 slave tdbctl ============
    # 获取 master 地址用于检查复制状态（master_instances 一定存在，前面已校验）
    master_ip, master_port = _get_primary_address(master_instances, cluster, fallback_to_cluster=False)
    _add_slave_upgrade_steps(
        sub_pipeline, root_id, parent_global_data, bk_cloud_id, slave_instances, master_ip, master_port, pkg_id
    )

    # ============ 步骤4: 升级 master tdbctl ============
    _add_master_upgrade_steps(sub_pipeline, root_id, parent_global_data, bk_cloud_id, master_instances, pkg_id)

    # ============ 延迟等待节点: 等待60秒 ============
    # 在升级后检查之前等待60秒，确保服务稳定
    sub_pipeline.add_act(
        act_name=_("延迟60秒/等待slave io connecting ..."),
        act_component_code=DelayComponent.code,
        kwargs={
            "delay_seconds": 60,
        },
    )

    # ============ 步骤5: 并行执行升级后检查 ============
    # 并行执行 master 升级后检查和 slave 复制状态检查，提高效率
    # master_instances 一定存在（前面已校验）
    _add_post_upgrade_checks_parallel(sub_pipeline, cluster, slave_instances, master_ip, master_port, bk_cloud_id)

    # ============ 步骤6: 记录升级成功状态 ============
    # 只有流程执行到这一步才会记录成功状态，保证状态与流程执行结果一致
    _add_upgrade_status_update_act(
        sub_pipeline=sub_pipeline,
        cluster_id=cluster_id,
        instances=all_upgrade_instances,
        target_version=target_version,
        pkg_id=pkg_id,
        task_id=root_id,
        status=TdbctlUpgradeStatus.SUCCESS.value,
        batch_id=batch_id,
        operator=operator,
        is_primary_list=is_primary_list,
        current_versions=current_versions,
    )

    logger.info(_("tdbctl升级子流程构建完成，集群ID: {}").format(cluster_id))

    return sub_pipeline.build_sub_process(sub_name=sub_flow_name)


class UpgradeTdbctlFlow(object):
    """
    TendbCluster tdbctl（中控）升级流程

    功能说明：
    1. 升级 TendbCluster 集群中的 tdbctl（中控）组件
    2. tdbctl 只部署在 spider master 角色的机器上
    3. tdbctl 是一主多从的模式
    4. 必须存在 master tdbctl 实例，否则会抛出异常退出
    5. 先升级所有 slave tdbctl，再升级 master tdbctl
    6. 升级后检查 slave 的复制状态（如果有 slave）
    7. 支持 update_all 参数，当为 True 时，自动查询业务下所有的 spider 集群进行升级

    数据格式示例：
        场景1：升级指定集群
        {
            "bk_biz_id": 100,
            "bk_cloud_id": 0,
            "uid": "admin",
            "update_all": False,  # 不开启全量更新，使用 infos 中指定的集群
            "infos": [
                {
                    "cluster_id": 1,       # 集群ID
                    "pkg_id": 123,         # tdbctl 升级包ID
                },
                {
                    "cluster_id": 2,       # 集群ID
                    "pkg_id": 123,         # tdbctl 升级包ID
                }
            ]
        }

        场景2：升级业务下所有 spider 集群
        {
            "bk_biz_id": 100,
            "bk_cloud_id": 0,
            "uid": "admin",
            "update_all": True,   # 开启全量更新，自动查询业务下所有 spider 集群
            "infos": [
                {
                    "pkg_id": 123         # 统一使用的 tdbctl 升级包ID（cluster_id 会自动查询）
                }
            ]
        }
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id: 任务流程定义的root_id
        @param data: 单据传递参数，包含以下字段：
            - bk_biz_id: 业务ID
            - bk_cloud_id: 云区域ID
            - uid: 用户ID
            - update_all: 是否更新业务下所有的 spider 集群（默认 False）
            - infos: 升级信息列表，包含 cluster_id 和 pkg_id
        """
        self.root_id = root_id
        self.data = data
        self.uid = data.get("uid", "")
        self.bk_biz_id = data.get("bk_biz_id", 0)
        self.bk_cloud_id = data.get("bk_cloud_id", 0)
        self.update_all = data.get("update_all", False)

    def _get_upgrade_infos(self) -> List[Dict]:
        """
        获取需要升级的集群信息列表

        如果 update_all=True，则查询业务下所有的 spider 集群，并使用 infos 中指定的 pkg_id
        否则直接使用 infos 中的集群信息

        @return: 升级信息列表，格式为 [{"cluster_id": int, "pkg_id": int}, ...]
        """
        infos = self.data.get("infos", [])

        if not self.update_all:
            # 不是全量更新，直接返回指定的集群信息
            return infos

        # 全量更新：查询业务下所有的 spider 集群
        if not infos:
            logger.error(_("update_all=True 时，infos 不能为空，需要指定 pkg_id"))
            raise ValueError(_("update_all=True 时，infos 不能为空，需要指定 pkg_id"))

        # 从 infos 中获取 pkg_id（全量更新时使用统一的 pkg_id）
        pkg_id = infos[0].get("pkg_id")
        if not pkg_id:
            logger.error(_("update_all=True 时，必须指定 pkg_id"))
            raise ValueError(_("update_all=True 时，必须指定 pkg_id"))

        # 查询业务下所有的 spider (TenDBCluster) 集群
        spider_clusters = Cluster.objects.filter(
            bk_biz_id=self.bk_biz_id, cluster_type=ClusterType.TenDBCluster
        ).values_list("id", flat=True)

        if not spider_clusters:
            logger.warning(_("业务 {} 下没有找到 spider 集群").format(self.bk_biz_id))
            return []

        logger.info(_("业务 {} 下找到 {} 个 spider 集群，将进行全量 tdbctl 升级").format(self.bk_biz_id, len(spider_clusters)))

        # 构建升级信息列表
        upgrade_infos = [{"cluster_id": cluster_id, "pkg_id": pkg_id} for cluster_id in spider_clusters]
        return upgrade_infos

    def run(self):
        """
        执行 tdbctl 升级流程的主入口方法

        执行流程：
        1. 根据 update_all 参数决定升级范围
        2. 如果 update_all=True，查询业务下所有的 spider 集群
        3. 遍历所有需要升级的集群
        4. 为每个集群调用 tdbctl_upgrade_subflow 进行升级
        """
        # 获取需要升级的集群信息
        upgrade_infos = self._get_upgrade_infos()

        if not upgrade_infos:
            logger.warning(_("没有需要升级的集群"))
            return

        cluster_ids = [info["cluster_id"] for info in upgrade_infos]
        # 创建主流程
        pipeline = Builder(root_id=self.root_id, data=self.data, need_random_pass_cluster_ids=list(set(cluster_ids)))

        # 遍历所有需要升级的集群
        sub_pipelines = []
        for upgrade_info in upgrade_infos:
            cluster_id = upgrade_info["cluster_id"]
            pkg_id = upgrade_info["pkg_id"]

            logger.info(_("开始构建集群 {} 的 tdbctl 升级流程，升级包ID: {}").format(cluster_id, pkg_id))

            # 调用 tdbctl 升级子流程
            sub_flow = tdbctl_upgrade_subflow(
                uid=self.uid,
                root_id=self.root_id,
                parent_global_data=self.data,
                bk_cloud_id=self.bk_cloud_id,
                cluster_id=cluster_id,
                pkg_id=pkg_id,
                sub_flow_name=_("集群{} tdbctl升级").format(cluster_id),
            )
            sub_pipelines.append(sub_flow)

        # 运行流程
        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        pipeline.run_pipeline()
