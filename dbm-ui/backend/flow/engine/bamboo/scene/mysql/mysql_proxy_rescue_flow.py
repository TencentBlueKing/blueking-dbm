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
import copy
import logging.config
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterType, InstanceRole, InstanceStatus
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import Cluster, ProxyInstance
from backend.db_package.constants import PackageType
from backend.db_package.models import Package
from backend.flow.consts import DnsOpType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.entrys_manager import BuildEntrysManageSubflow
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.common.common_sub_flow import init_machine_sub_flow
from backend.flow.engine.bamboo.scene.mysql.common.exceptions import ProxyFlowFailedException
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.departs import DeployPeripheralToolsDepart
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.subflow import standardize_mysql_cluster_subflow
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mysql.clone_proxy_client_in_backend import (
    CloneProxyUsersInBackendComponent,
)
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import (
    CloneProxyClientInBackendKwargs,
    DBMetaOPKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import SystemInfoContext
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta
from backend.flow.utils.mysql.proxy_act_payload import ProxyActPayload

logger = logging.getLogger("flow")


class MySQLProxyRescueFlow(object):
    """
    TendbHA Proxy 救援流程

    用于所有 Proxy 都故障无法恢复的极端情况，通过以下步骤恢复集群可用性：
    1. 上架新 Proxy 实例
    2. 配置 Proxy 后端（连接到 Master）
    3. 从 Master 恢复白名单权限
    4. 更新域名/CLB 解析
    5. 部署周边程序
    6. 人工确认新 Proxy 工作正常
    7. （可选）下架旧的故障 Proxy

    ⚠️ 安全限制: 前置校验确保所有原 Proxy 都处于 UNAVAILABLE 状态

    ticket_data 参数结构：
    {
        "uid": "xxx",
        "created_by": "xxx",
        "bk_biz_id": 123,
        "ticket_type": "MYSQL_PROXY_RESCUE",
        "cluster_id": 456,
        "new_proxies": [
            {"ip": "127.0.0.1", "bk_host_id": 1, "bk_cloud_id": 0, "bk_biz_id": 123, "spec": {...}},
            {"ip": "127.0.0.2", "bk_host_id": 2, "bk_cloud_id": 0, "bk_biz_id": 123, "spec": {...}}
        ],
        "auto_cleanup_old_proxies": true
    }
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data

    @staticmethod
    def get_proxy_pkg_id_for_cluster(cluster_id: int, specified_version: str = None) -> int:
        """
        根据集群已存在的 proxy 获取待安装 proxy 节点版本介质包

        ✅ 改进: 支持三种场景
        1. 指定版本：使用指定的版本（跳过版本一致性检查）
        2. 有旧 Proxy 元数据：使用旧 Proxy 的版本（已在 validator 检查版本一致性）
        3. 没有旧 Proxy 元数据：使用最新版本

        @param cluster_id: 集群ID
        @param specified_version: 用户指定的版本（可选）
        """
        # ✅ 场景1: 如果用户指定了版本，直接使用指定版本
        if specified_version:
            logger.info(_("使用用户指定的 Proxy 版本: {}").format(specified_version))
            return Package.get_package_for_version_no(
                db_type=DBType.MySQL, pkg_type=PackageType.MySQLProxy, version_no=specified_version
            ).id

        cluster = Cluster.objects.get(id=cluster_id)
        all_proxys = cluster.proxyinstance_set.all()

        # ✅ 场景3: 如果没有旧 Proxy 元数据，使用最新版本
        if not all_proxys.exists():
            logger.warning(_("集群没有任何 Proxy 记录，将使用最新版本的 Proxy 介质包"))
            return Package.get_latest_package(version="latest", pkg_type=PackageType.MySQLProxy).id

        # ✅ 场景2: 使用旧 Proxy 的版本
        # 注意：版本一致性已经在 validator 中检查过了，这里直接获取版本
        cluster_proxy_version_set = {p.version for p in all_proxys}
        proxy_version = cluster_proxy_version_set.pop()

        logger.info(_("使用旧 Proxy 的版本: {}").format(proxy_version))

        # 返回对应的 package id
        return Package.get_package_for_version_no(
            db_type=DBType.MySQL, pkg_type=PackageType.MySQLProxy, version_no=str(proxy_version)
        ).id

    def __get_proxy_install_port(self, cluster_id: int) -> int:
        """
        获取 proxy 安装端口

        ✅ 改进: 支持没有旧 Proxy 元数据的场景，从用户参数获取端口
        @param: cluster_id 集群ID
        """
        cluster = Cluster.objects.get(id=cluster_id)
        proxy_instances = ProxyInstance.objects.filter(cluster=cluster).all()

        # ✅ 改进：如果没有旧 Proxy 元数据，从用户参数获取端口
        if not proxy_instances.exists():
            proxy_port = self.data.get("proxy_port")
            if not proxy_port:
                raise ProxyFlowFailedException(_("集群没有任何 Proxy 实例记录，且用户未提供 proxy_port 参数"))
            logger.warning(_("集群没有旧 Proxy 元数据，使用用户提供的端口: {}").format(proxy_port))
            return proxy_port

        # 获取第一个 Proxy 的端口（救援场景下所有 Proxy 端口应该一致）
        proxy_port = proxy_instances.first().port

        # 检查端口是否一致
        port_set = {p.port for p in proxy_instances}
        if len(port_set) > 1:
            raise ProxyFlowFailedException(_("集群 Proxy 使用多个端口: {}，请检查").format(port_set))

        return proxy_port

    def rescue_proxy_flow(self):
        """
        定义 MySQL Proxy 救援流程
        """
        cluster_id = self.data["cluster_id"]
        bk_biz_id = self.data["bk_biz_id"]
        new_proxies = self.data["new_proxies"]
        auto_cleanup_old_proxies = self.data.get("auto_cleanup_old_proxies", True)

        # 获取集群信息
        try:
            cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)
        except Cluster.DoesNotExist:
            raise ClusterNotExistException(cluster_id=cluster_id, bk_biz_id=bk_biz_id, message=_("集群不存在"))

        logger.info(
            _("开始执行 Proxy 救援流程: cluster_id={}, cluster_domain={}, new_proxies={}").format(
                cluster_id, cluster.immute_domain, [p["ip"] for p in new_proxies]
            )
        )

        # 获取 Proxy 版本和端口信息
        specified_version = self.data.get("proxy_version")  # 用户指定的版本（可选）
        target_proxy_pkg_id = self.get_proxy_pkg_id_for_cluster(cluster_id, specified_version)
        proxy_port = self.__get_proxy_install_port(cluster_id)

        # 构建主流程
        rescue_pipeline = Builder(root_id=self.root_id, data=self.data, need_random_pass_cluster_ids=[cluster_id])

        # 准备子流程上下文
        sub_flow_context = copy.deepcopy(self.data)
        sub_flow_context["proxy_ports"] = [proxy_port]
        sub_flow_context["target_proxy_pkg_id"] = target_proxy_pkg_id

        # 声明主子流程
        sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

        # ==================== 阶段1: 上架新 Proxy（子流程）====================
        logger.info(_("阶段1: 初始化和安装新 Proxy"))

        install_sub = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

        # 初始化新机器
        install_sub.add_sub_pipeline(
            sub_flow=init_machine_sub_flow(
                uid=sub_flow_context["uid"],
                root_id=self.root_id,
                bk_cloud_id=new_proxies[0]["bk_cloud_id"],
                sys_init_ips=[p["ip"] for p in new_proxies],
                init_check_ips=[p["ip"] for p in new_proxies],
                yum_install_perl_ips=[p["ip"] for p in new_proxies],
                bk_host_ids=[p["bk_host_id"] for p in new_proxies],
            )
        )

        # 下发 Proxy 介质包
        install_sub.add_act(
            act_name=_("下发 Proxy 安装介质"),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(
                DownloadMediaKwargs(
                    bk_cloud_id=new_proxies[0]["bk_cloud_id"],
                    exec_ip=[p["ip"] for p in new_proxies],
                    file_list=GetFileList(db_type=DBType.MySQL).mysql_proxy_upgrade_package(target_proxy_pkg_id),
                )
            ),
        )

        # 并发安装 Proxy 实例
        install_acts_list = []
        for new_proxy in new_proxies:
            install_acts_list.append(
                {
                    "act_name": _("安装 Proxy 实例[{}]").format(new_proxy["ip"]),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(
                        ExecActuatorKwargs(
                            cluster_type=ClusterType.TenDBHA,
                            bk_cloud_id=new_proxies[0]["bk_cloud_id"],
                            exec_ip=new_proxy["ip"],
                            get_mysql_payload_func=MysqlActPayload.get_install_proxy_for_add_payload.__name__,
                            component_kwargs={"pkg_id": target_proxy_pkg_id},
                        )
                    ),
                }
            )
        install_sub.add_parallel_acts(acts_list=install_acts_list)

        # ==================== 阶段1.5: 在后端 MySQL 授权新 Proxy IP（子流程）====================
        # 从后端 MySQL 克隆旧 Proxy 的授权到新 Proxy（包括先清理残留账号）
        # 救援场景下旧 Proxy 实例虽然物理故障，但其账号仍存在于后端 MySQL 中
        # 阶段1 与阶段1.5 相互独立，并行执行以缩短整体耗时
        logger.info(_("阶段1.5: 在后端 MySQL 授权新 Proxy IP"))

        old_proxy_instances = list(ProxyInstance.objects.filter(cluster=cluster).all())
        if old_proxy_instances:
            origin_proxy_host = old_proxy_instances[0].machine.ip
            auth_sub = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))
            add_proxy_user_acts_list = []
            for new_proxy in new_proxies:
                add_proxy_user_acts_list.append(
                    {
                        "act_name": _("集群对新的 Proxy 添加后端授权[{}:{}]").format(new_proxy["ip"], proxy_port),
                        "act_component_code": CloneProxyUsersInBackendComponent.code,
                        "kwargs": asdict(
                            CloneProxyClientInBackendKwargs(
                                cluster_id=cluster.id,
                                target_proxy_host=new_proxy["ip"],
                                origin_proxy_host=origin_proxy_host,
                            )
                        ),
                    }
                )
            auth_sub.add_parallel_acts(acts_list=add_proxy_user_acts_list)

            # 阶段1（上架Proxy）与阶段1.5（后端授权）并行执行
            sub_pipeline.add_parallel_sub_pipeline(
                sub_flow_list=[
                    install_sub.build_sub_process(sub_name=_("上架新 Proxy")),
                    auth_sub.build_sub_process(sub_name=_("在后端 MySQL 授权新 Proxy IP")),
                ]
            )
        else:
            logger.warning(_("集群没有旧 Proxy 元数据，跳过在后端 MySQL 克隆授权步骤"))
            # 仅执行安装子流程
            sub_pipeline.add_sub_pipeline(sub_flow=install_sub.build_sub_process(sub_name=_("上架新 Proxy")))

        # ==================== 阶段2: 配置 Proxy 后端 ====================
        logger.info(_("阶段2: 配置 Proxy 后端"))

        set_backend_acts_list = []
        for new_proxy in new_proxies:
            exec_act_kwargs = ExecActuatorKwargs(
                bk_cloud_id=cluster.bk_cloud_id,
                component_kwargs={"cluster_id": cluster.id, "proxy_port": proxy_port},
                exec_ip=new_proxy["ip"],
                get_mysql_payload_func=ProxyActPayload.get_set_proxy_backends_in_cluster.__name__,
            )
            set_backend_acts_list.append(
                {
                    "act_name": _("新的 Proxy 配置后端实例[{}:{}]").format(new_proxy["ip"], proxy_port),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(exec_act_kwargs),
                }
            )
        sub_pipeline.add_parallel_acts(acts_list=set_backend_acts_list)

        # ==================== 阶段3: 恢复白名单权限 ====================
        # 在 Master 节点上执行：Proxy 账号支持远程连接，MySQL 账号仅本地连接
        # 因此需要在 Master 本地执行，由 actuator 本地读白名单表后远程写入 Proxy
        logger.info(_("阶段3: 恢复白名单权限"))

        master_instance = cluster.storageinstance_set.filter(instance_role=InstanceRole.BACKEND_MASTER).first()

        restore_whitelist_acts_list = []
        for new_proxy in new_proxies:
            exec_act_kwargs = ExecActuatorKwargs(
                bk_cloud_id=cluster.bk_cloud_id,
                component_kwargs={
                    "cluster_id": cluster.id,
                    "target_proxy_host": new_proxy["ip"],
                    "target_proxy_port": proxy_port,
                },
                exec_ip=master_instance.machine.ip,
                get_mysql_payload_func=MysqlActPayload.get_restore_proxy_whitelist_from_backend_payload.__name__,
            )
            restore_whitelist_acts_list.append(
                {
                    "act_name": _("在 Master 节点 {} 操作，恢复 Proxy 白名单[{}:{}]").format(
                        master_instance.machine.ip, new_proxy["ip"], proxy_port
                    ),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(exec_act_kwargs),
                }
            )
        sub_pipeline.add_parallel_acts(acts_list=restore_whitelist_acts_list)

        # ==================== 阶段4: 更新域名/CLB 解析 ====================
        logger.info(_("阶段4: 更新域名/CLB 解析"))

        # 使用 BuildEntrysManageSubflow 统一处理 DNS 和 CLB
        # 该方法会自动检测集群是否配置 CLB 并执行相应操作
        entry_sub_process = BuildEntrysManageSubflow(
            root_id=self.root_id,
            ticket_data=self.data,
            op_type=DnsOpType.CREATE,
            param={
                "cluster_id": cluster.id,
                "port": proxy_port,
                "add_ips": [p["ip"] for p in new_proxies],
            },
        )
        sub_pipeline.add_sub_pipeline(entry_sub_process)

        # ==================== 阶段5: 更新元数据 ====================
        logger.info(_("阶段5: 更新元数据"))

        sub_pipeline.add_act(
            act_name=_("添加 db_meta 元信息"),
            act_component_code=MySQLDBMetaComponent.code,
            kwargs=asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=MySQLDBMeta.mysql_proxy_add.__name__,
                    component_kwargs={
                        "new_proxies": new_proxies,
                        "proxy_ports": [proxy_port],
                        "cluster_ids": [cluster_id],
                        "created_by": self.data["created_by"],
                        "target_proxy_pkg_id": target_proxy_pkg_id,
                    },
                )
            ),
        )

        # ==================== 阶段6: 部署周边程序 ====================
        logger.info(_("阶段6: 部署周边程序"))

        sub_pipeline.add_sub_pipeline(
            sub_flow=standardize_mysql_cluster_subflow(
                root_id=self.root_id,
                data=copy.deepcopy(self.data),
                bk_cloud_id=new_proxies[0]["bk_cloud_id"],
                bk_biz_id=bk_biz_id,
                instances=[f"{new_proxy['ip']}{IP_PORT_DIVIDER}{proxy_port}" for new_proxy in new_proxies],
                departs=[
                    DeployPeripheralToolsDepart.DBAToolKit,
                    DeployPeripheralToolsDepart.MySQLCrond,
                    DeployPeripheralToolsDepart.MySQLMonitor,
                ],
                with_actuator=False,
                with_bk_plugin=False,
                with_collect_sysinfo=False,
            )
        )

        # ==================== 阶段7: 人工确认新 Proxy 工作正常 ====================
        logger.info(_("阶段7: 人工确认新 Proxy 工作正常"))

        sub_pipeline.add_act(
            act_name=_("人工确认新 Proxy 工作正常"),
            act_component_code=PauseComponent.code,
            kwargs={},
        )

        # ==================== 阶段8: 下架旧 Proxy 实例（可选） ====================
        if auto_cleanup_old_proxies:
            logger.info(_("阶段8: 下架旧 Proxy 实例"))

            # 获取旧的故障 Proxy 列表（状态为 UNAVAILABLE）
            old_proxies = cluster.proxyinstance_set.filter(status=InstanceStatus.UNAVAILABLE)

            if old_proxies.exists():
                # 子流程：下架旧 Proxy
                cleanup_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

                # 1. 从域名/CLB 中移除旧 Proxy
                old_proxy_ips = [p.machine.ip for p in old_proxies]
                logger.info(_("从域名/CLB 中移除旧 Proxy: {}").format(old_proxy_ips))

                entry_remove_process = BuildEntrysManageSubflow(
                    root_id=self.root_id,
                    ticket_data=self.data,
                    op_type=DnsOpType.RECYCLE_RECORD,
                    param={
                        "cluster_id": cluster.id,
                        "port": proxy_port,
                        "del_ips": old_proxy_ips,
                    },
                )
                cleanup_sub_pipeline.add_sub_pipeline(entry_remove_process)

                # 2. 卸载旧 Proxy 实例
                uninstall_acts_list = []
                for old_proxy in old_proxies:
                    uninstall_acts_list.append(
                        {
                            "act_name": _("卸载 Proxy 实例[{}:{}]").format(old_proxy.machine.ip, old_proxy.port),
                            "act_component_code": ExecuteDBActuatorScriptComponent.code,
                            "kwargs": asdict(
                                ExecActuatorKwargs(
                                    bk_cloud_id=cluster.bk_cloud_id,
                                    exec_ip=old_proxy.machine.ip,
                                    get_mysql_payload_func=MysqlActPayload.get_uninstall_proxy_payload.__name__,
                                    component_kwargs={"proxy_port": old_proxy.port, "force": True},
                                )
                            ),
                        }
                    )

                cleanup_sub_pipeline.add_parallel_acts(acts_list=uninstall_acts_list)

                # 3. 更新元数据，移除旧 Proxy 记录
                for old_proxy in old_proxies:
                    cleanup_sub_pipeline.add_act(
                        act_name=_("更新 DBMeta 元信息，移除旧 Proxy[{}]").format(old_proxy.machine.ip),
                        act_component_code=MySQLDBMetaComponent.code,
                        kwargs=asdict(
                            DBMetaOPKwargs(
                                db_meta_class_func=MySQLDBMeta.mysql_proxy_reduce.__name__,
                                component_kwargs={
                                    "cluster_ids": [cluster.id],
                                    "origin_proxy_ip": old_proxy.machine.ip,
                                },
                            )
                        ),
                    )

                sub_pipeline.add_sub_pipeline(cleanup_sub_pipeline.build_sub_process(sub_name=_("下架旧 Proxy 实例")))
                logger.info(_("已添加下架旧 Proxy 实例的子流程"))
            else:
                logger.info(_("没有找到需要下架的旧 Proxy 实例（UNAVAILABLE 状态）"))

        # 构建完整流程
        rescue_pipeline.add_sub_pipeline(sub_flow=sub_pipeline.build_sub_process(sub_name=_("MySQL Proxy 救援流程")))

        # 运行流程
        logger.info(_("启动 MySQL Proxy 救援流程: root_id={}, cluster_id={}").format(self.root_id, cluster_id))
        rescue_pipeline.run_pipeline(init_trans_data_class=SystemInfoContext())
