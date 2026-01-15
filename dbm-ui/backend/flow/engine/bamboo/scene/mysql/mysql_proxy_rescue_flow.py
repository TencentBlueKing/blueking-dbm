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
from collections import defaultdict
from dataclasses import asdict
from typing import Dict, List, Optional

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
    TendbHA Proxy 救援流程（多集群并行模式）

    用于所有 Proxy 都故障无法恢复的极端情况，通过以下步骤恢复集群可用性：
    0. 主流程开始前：按云区域下发 db-actuator 介质至新 Proxy 与 Master 所在机器
    1. 上架新 Proxy 实例
    2. 配置 Proxy 后端（连接到 Master）
    3. 从 Master 恢复白名单权限
    4. 更新域名/CLB 解析
    5. 部署周边程序
    6. 人工确认新 Proxy 工作正常（未走自动下架或无可下架旧实例时，在周边程序后暂停）
    7. （可选）下架旧的故障 Proxy（若开启自动下架且存在旧 Proxy，则将人工确认下沉为该子流程首节点后再回收）
    8. 子流程末尾：根据实例元数据同步 Cluster.status（normal/abnormal）

    ⚠️ 安全限制: 前置校验确保所有原 Proxy 都处于 UNAVAILABLE 状态

    ticket_data 参数结构（多集群模式）：
    {
        "uid": "xxx",
        "created_by": "xxx",
        "bk_biz_id": 123,
        "ticket_type": "MYSQL_PROXY_RESCUE",
        "infos": [
            {
                "cluster_id": 456,
                "new_proxies": [
                    {"ip": "127.0.0.1", "bk_host_id": 1, "bk_cloud_id": 0, "bk_biz_id": 123, "spec": {...}},
                    {"ip": "127.0.0.2", "bk_host_id": 2, "bk_cloud_id": 0, "bk_biz_id": 123, "spec": {...}}
                ],
                "proxy_port": 10000,
                "proxy_version": "",
                "auto_cleanup_old_proxies": true
            }
        ]
    }
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data

    def _collect_dbactuator_exec_ips_by_cloud(self, infos: List[dict]) -> Dict[int, set]:
        """
        收集本单据需要执行 db-actuator 的机器 IP，按 bk_cloud_id 分组（新 Proxy + 各集群 Master）。
        """
        cloud_to_ips: Dict[int, set] = defaultdict(set)
        bk_biz_id = self.data["bk_biz_id"]
        for info in infos:
            for p in info.get("new_proxies", []):
                cloud_to_ips[p["bk_cloud_id"]].add(p["ip"])
            cluster = Cluster.objects.get(id=info["cluster_id"], bk_biz_id=bk_biz_id)
            master = cluster.storageinstance_set.filter(instance_role=InstanceRole.BACKEND_MASTER).first()
            if master:
                cloud_to_ips[cluster.bk_cloud_id].add(master.machine.ip)
        return cloud_to_ips

    # ------------------------------------------------------------------ #
    #  辅助静态方法
    # ------------------------------------------------------------------ #

    @staticmethod
    def _get_proxy_pkg_id(cluster_id: int, specified_version: str = None) -> int:
        """
        根据集群已存在的 proxy 获取待安装 proxy 节点版本介质包

        支持三种场景：
        1. 指定版本：使用指定的版本
        2. 有旧 Proxy 元数据：使用旧 Proxy 的版本
        3. 没有旧 Proxy 元数据：使用最新版本

        @param cluster_id: 集群ID
        @param specified_version: 用户指定的版本（可选）
        """
        if specified_version:
            logger.info(_("使用用户指定的 Proxy 版本: {}").format(specified_version))
            return Package.get_package_for_version_no(
                db_type=DBType.MySQL, pkg_type=PackageType.MySQLProxy, version_no=specified_version
            ).id

        cluster = Cluster.objects.get(id=cluster_id)
        all_proxies = cluster.proxyinstance_set.all()

        if not all_proxies.exists():
            logger.warning(_("集群没有任何 Proxy 记录，将使用最新版本的 Proxy 介质包"))
            return Package.get_latest_package(version="latest", pkg_type=PackageType.MySQLProxy).id

        cluster_proxy_version_set = {p.version for p in all_proxies}
        proxy_version = cluster_proxy_version_set.pop()
        logger.info(_("使用旧 Proxy 的版本: {}").format(proxy_version))

        return Package.get_package_for_version_no(
            db_type=DBType.MySQL, pkg_type=PackageType.MySQLProxy, version_no=str(proxy_version)
        ).id

    @staticmethod
    def _get_proxy_port(cluster_id: int, info: dict) -> int:
        """
        获取 proxy 安装端口

        有旧 Proxy 元数据时从元数据读取，否则从 info 参数中获取。

        @param cluster_id: 集群ID
        @param info: 单条救援参数字典（包含 proxy_port 等字段）
        """
        cluster = Cluster.objects.get(id=cluster_id)
        proxy_instances = ProxyInstance.objects.filter(cluster=cluster).all()

        if not proxy_instances.exists():
            proxy_port = info.get("proxy_port")
            if not proxy_port:
                raise ProxyFlowFailedException(_("集群 {} 没有任何 Proxy 实例记录，且未提供 proxy_port 参数").format(cluster_id))
            logger.warning(_("集群 {} 没有旧 Proxy 元数据，使用参数提供的端口: {}").format(cluster_id, proxy_port))
            return proxy_port

        port_set = {p.port for p in proxy_instances}
        if len(port_set) > 1:
            raise ProxyFlowFailedException(_("集群 {} Proxy 使用多个端口: {}，请检查").format(cluster_id, port_set))

        return proxy_instances.first().port

    # ------------------------------------------------------------------ #
    #  单集群子流程
    # ------------------------------------------------------------------ #

    def _build_cluster_sub_flow(self, info: dict) -> object:
        """
        构建单个集群的 Proxy 救援子流程

        @param info: 单条救援参数字典，包含 cluster_id/new_proxies/proxy_port/proxy_version/auto_cleanup_old_proxies
        @return: 构建好的子流程 process（可传入 add_parallel_sub_pipeline）
        """
        cluster_id = info["cluster_id"]
        new_proxies: List[dict] = info["new_proxies"]
        auto_cleanup_old_proxies = info.get("auto_cleanup_old_proxies", True)
        specified_version = info.get("proxy_version") or None

        bk_biz_id = self.data["bk_biz_id"]

        try:
            cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)
        except Cluster.DoesNotExist:
            raise ClusterNotExistException(cluster_id=cluster_id, bk_biz_id=bk_biz_id, message=_("集群不存在"))

        logger.info(
            _("构建集群 {} (domain={}) 的 Proxy 救援子流程，新 Proxy: {}").format(
                cluster_id, cluster.immute_domain, [p["ip"] for p in new_proxies]
            )
        )

        target_proxy_pkg_id = self._get_proxy_pkg_id(cluster_id, specified_version)
        proxy_port = self._get_proxy_port(cluster_id, info)

        # 子流程上下文：合并顶层参数与本 info（info 字段优先），并移除 infos 键
        sub_ctx = copy.deepcopy(self.data)
        sub_ctx.update(info)
        sub_ctx.pop("infos", None)
        sub_ctx["proxy_ports"] = [proxy_port]
        sub_ctx["target_proxy_pkg_id"] = target_proxy_pkg_id

        sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_ctx))

        # ---------- 阶段1 + 1.5: 上架新 Proxy & 后端授权（并行）----------
        install_sub = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_ctx))

        install_sub.add_sub_pipeline(
            sub_flow=init_machine_sub_flow(
                uid=sub_ctx["uid"],
                root_id=self.root_id,
                bk_cloud_id=new_proxies[0]["bk_cloud_id"],
                sys_init_ips=[p["ip"] for p in new_proxies],
                init_check_ips=[p["ip"] for p in new_proxies],
                yum_install_perl_ips=[p["ip"] for p in new_proxies],
                bk_host_ids=[p["bk_host_id"] for p in new_proxies],
            )
        )

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

        old_proxy_instances = list(ProxyInstance.objects.filter(cluster=cluster).all())
        if old_proxy_instances:
            origin_proxy_host = old_proxy_instances[0].machine.ip
            auth_sub = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_ctx))
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

            sub_pipeline.add_parallel_sub_pipeline(
                sub_flow_list=[
                    install_sub.build_sub_process(sub_name=_("上架新 Proxy")),
                    auth_sub.build_sub_process(sub_name=_("在后端 MySQL 授权新 Proxy IP")),
                ]
            )
        else:
            logger.warning(_("集群 {} 没有旧 Proxy 元数据，跳过在后端 MySQL 克隆授权步骤").format(cluster_id))
            sub_pipeline.add_sub_pipeline(sub_flow=install_sub.build_sub_process(sub_name=_("上架新 Proxy")))

        # ---------- 阶段2: 配置 Proxy 后端 ----------
        set_backend_acts_list = []
        for new_proxy in new_proxies:
            set_backend_acts_list.append(
                {
                    "act_name": _("新的 Proxy 配置后端实例[{}:{}]").format(new_proxy["ip"], proxy_port),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(
                        ExecActuatorKwargs(
                            bk_cloud_id=cluster.bk_cloud_id,
                            component_kwargs={"cluster_id": cluster.id, "proxy_port": proxy_port},
                            exec_ip=new_proxy["ip"],
                            get_mysql_payload_func=ProxyActPayload.get_set_proxy_backends_in_cluster.__name__,
                        )
                    ),
                }
            )
        sub_pipeline.add_parallel_acts(acts_list=set_backend_acts_list)

        # ---------- 阶段3: 恢复白名单权限（单次调用批量恢复所有新 Proxy）----------
        master_instance = cluster.storageinstance_set.filter(instance_role=InstanceRole.BACKEND_MASTER).first()

        sub_pipeline.add_act(
            act_name=_("在 Master 节点 {} 操作，批量恢复 {} 个新 Proxy 的白名单").format(master_instance.machine.ip, len(new_proxies)),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(
                ExecActuatorKwargs(
                    bk_cloud_id=cluster.bk_cloud_id,
                    component_kwargs={
                        "cluster_id": cluster.id,
                        "target_proxies": [{"host": p["ip"], "port": proxy_port} for p in new_proxies],
                    },
                    exec_ip=master_instance.machine.ip,
                    get_mysql_payload_func=MysqlActPayload.get_restore_proxy_whitelist_from_backend_payload.__name__,
                )
            ),
        )

        # ---------- 阶段4: 更新域名/CLB 解析 ----------
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

        # ---------- 阶段5: 更新元数据 ----------
        # 救援场景旧 Proxy 均为 UNAVAILABLE，mysql_proxy_add 需显式传入 template_proxy_ip 才能复制入口绑定（见 tendbha.switch_proxy.add_proxy）
        db_meta_kwargs = {
            "new_proxies": new_proxies,
            "proxy_ports": [proxy_port],
            "cluster_ids": [cluster_id],
            "created_by": self.data["created_by"],
            "target_proxy_pkg_id": target_proxy_pkg_id,
        }
        if old_proxy_instances:
            db_meta_kwargs["template_proxy_ip"] = old_proxy_instances[0].machine.ip

        sub_pipeline.add_act(
            act_name=_("添加 db_meta 元信息"),
            act_component_code=MySQLDBMetaComponent.code,
            kwargs=asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=MySQLDBMeta.mysql_proxy_add.__name__,
                    component_kwargs=db_meta_kwargs,
                )
            ),
        )

        # ---------- 阶段6: 部署周边程序 ----------
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

        # ---------- 阶段7: 人工确认（未走「下架旧 Proxy」子流程时在此暂停；否则下沉为子流程首节点）----------
        old_proxies_for_cleanup = None
        if auto_cleanup_old_proxies:
            old_proxies_for_cleanup = cluster.proxyinstance_set.filter(status=InstanceStatus.UNAVAILABLE)
        pause_inside_cleanup_subflow = (
            auto_cleanup_old_proxies and old_proxies_for_cleanup is not None and old_proxies_for_cleanup.exists()
        )
        if not pause_inside_cleanup_subflow:
            sub_pipeline.add_act(
                act_name=_("人工确认新 Proxy 工作正常"),
                act_component_code=PauseComponent.code,
                kwargs={},
            )

        # ---------- 阶段8: 下架旧 Proxy 实例（可选）----------
        if auto_cleanup_old_proxies:
            old_proxies = (
                old_proxies_for_cleanup
                if old_proxies_for_cleanup is not None
                else cluster.proxyinstance_set.filter(status=InstanceStatus.UNAVAILABLE)
            )

            if old_proxies.exists():
                cleanup_sub = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_ctx))

                if pause_inside_cleanup_subflow:
                    cleanup_sub.add_act(
                        act_name=_("人工确认新 Proxy 工作正常"),
                        act_component_code=PauseComponent.code,
                        kwargs={},
                    )

                old_proxy_ips = [p.machine.ip for p in old_proxies]
                logger.info(_("从域名/CLB 中移除旧 Proxy: {}").format(old_proxy_ips))

                cleanup_sub.add_sub_pipeline(
                    BuildEntrysManageSubflow(
                        root_id=self.root_id,
                        ticket_data=self.data,
                        op_type=DnsOpType.RECYCLE_RECORD,
                        param={
                            "cluster_id": cluster.id,
                            "port": proxy_port,
                            "del_ips": old_proxy_ips,
                        },
                    )
                )

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
                cleanup_sub.add_parallel_acts(acts_list=uninstall_acts_list)

                for old_proxy in old_proxies:
                    cleanup_sub.add_act(
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

                sub_pipeline.add_sub_pipeline(cleanup_sub.build_sub_process(sub_name=_("下架旧 Proxy 实例")))
            else:
                logger.info(_("集群 {} 没有找到需要下架的旧 Proxy 实例（UNAVAILABLE 状态）").format(cluster_id))

        sub_pipeline.add_act(
            act_name=_("同步集群运行状态"),
            act_component_code=MySQLDBMetaComponent.code,
            kwargs=asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=MySQLDBMeta.sync_tendbha_cluster_status.__name__,
                    component_kwargs={"cluster_id": cluster_id},
                )
            ),
        )

        return sub_pipeline.build_sub_process(sub_name=_("[{}] Proxy 救援").format(cluster.immute_domain))

    # ------------------------------------------------------------------ #
    #  入口
    # ------------------------------------------------------------------ #

    def rescue_proxy_flow(self):
        """
        定义 MySQL Proxy 救援流程（多集群并行模式）

        主流程先按云区域下发 db-actuator，再并行执行各集群子流程；子流程末尾同步 Cluster.status。
        """
        infos: List[dict] = self.data["infos"]
        all_cluster_ids = [info["cluster_id"] for info in infos]

        logger.info(_("启动 MySQL Proxy 救援流程（多集群模式）: root_id={}, cluster_ids={}").format(self.root_id, all_cluster_ids))

        rescue_pipeline = Builder(
            root_id=self.root_id,
            data=self.data,
            need_random_pass_cluster_ids=all_cluster_ids,
        )

        cloud_to_ips = self._collect_dbactuator_exec_ips_by_cloud(infos)
        for bk_cloud_id in sorted(cloud_to_ips.keys()):
            ip_list = sorted(cloud_to_ips[bk_cloud_id])
            rescue_pipeline.add_act(
                act_name=_("下发 db-actuator 介质[云区域 {}]").format(bk_cloud_id),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=bk_cloud_id,
                        exec_ip=ip_list,
                        file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    )
                ),
            )

        # 为每个集群构建独立子流程，统一走并行编排（单集群时并行只有一个 flow，行为等价）
        rescue_pipeline.add_parallel_sub_pipeline(sub_flow_list=[self._build_cluster_sub_flow(info) for info in infos])

        rescue_pipeline.run_pipeline_with_sidecar(
            init_trans_data_class=SystemInfoContext(),
            check_ai_monitor_cluster_list=all_cluster_ids,
        )
