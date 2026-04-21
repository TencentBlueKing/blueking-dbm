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
from typing import Dict, Optional

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import InstancePhase, InstanceStatus
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import Cluster, ProxyInstance
from backend.flow.consts import DnsOpType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.entrys_manager import BuildEntrysManageSubflow
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.mysql.check_client_connections import CheckClientConnComponent
from backend.flow.plugins.components.collections.mysql.clone_proxy_client_in_backend import (
    CloneProxyUsersInBackendComponent,
)
from backend.flow.plugins.components.collections.mysql.clone_proxy_user_in_cluster import (
    CloneProxyUsersInClusterComponent,
)
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import (
    CheckClientConnKwargs,
    CloneProxyClientInBackendKwargs,
    CloneProxyUsersKwargs,
    DBMetaOPKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
)
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta
from backend.flow.utils.mysql.proxy_act_payload import ProxyActPayload

logger = logging.getLogger("flow")


class MySQLProxyRebuildFlow(object):
    """
    构建 mysql 集群 proxy 实例原地重建流程抽象类。

    重建场景说明：
        所谓"重建 proxy 实例"，是指在不改变 proxy 对应机器元数据（Machine/ProxyInstance 本身
        以及其对集群的归属关系）的前提下，对指定 proxy 实例做"后端 MySQL 再配置 + 权限白名单
        再克隆 + 域名映射重置"的原地修复。常用于 proxy 进程/配置异常后的快速恢复。

    rebuild 过程（严格串行，单集群维度）：
        1. 修改 proxy 的 instance 状态为 restoring
        2. 检查待重建 proxy 实例连接
        3. 回收 proxy 实例所有的域名映射
        4. 重新配置 proxy 的后端实例
        5. 克隆 proxy 的用户白名单
        6. 在后端 MySQL 上为新 proxy 的 IP 创建访问权限
        7. 添加 proxy 实例和集群主域名的映射关系
        8. 修改 proxy 的 instance 状态为 running

    兼容跨云区域的场景支持。

    ticket_data 参数（按集群维度聚合，rebuild_proxy_hosts 为该集群下需要重建的 proxy 机器列表）：
    {
        "uid": "x",
        "created_by": "x",
        "bk_biz_id": "x",
        "ticket_type": "MYSQL_PROXY_REBUILD",
        "is_safe": true,
        "infos": [
            {
                "cluster_id": 1,
                "rebuild_proxy_hosts": [
                    {"ip": "x", "bk_cloud_id": 0, "bk_host_id": 0, "bk_biz_id": 1},
                    {"ip": "z", "bk_cloud_id": 0, "bk_host_id": 0, "bk_biz_id": 1}
                ]
            }
        ]
    }

    说明：infos 默认已经按 cluster_id 聚合好，本流程不再做聚合处理。
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的 root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data

    def rebuild_mysql_cluster_proxy_flow(self):
        """
        定义 mysql 集群 proxy 实例重建主流程。

        顶层流水线：
        - 先按 bk_cloud_id 对所有待重建 proxy 机器 IP 做【去重聚合】下发 db-actuator 介质
          （同一台机器可能归属多集群或多次出现，只需下发一次）
        - 随后按 self.data["infos"] 的每一项（一个 cluster_id + 一组 rebuild_proxy_hosts）
          构造 cluster 子流程，所有 cluster 子流程之间【并行】执行

        每个 cluster 子流程内部：
        - 按 rebuild_proxy_hosts 中每台 proxy 构造 proxy 子流程，proxy 之间【并行】执行
        - 每个 proxy 子流程严格按 7 步串行
        """
        rebuild_pipeline = Builder(root_id=self.root_id, data=self.data)

        # ----------------------------------------------------------------
        # 阶段0：按 bk_cloud_id 聚合去重，下发 db-actuator 介质
        #   - 同一个云区域下所有待重建 proxy 机器的 IP 聚合成 list，整体一次下发
        #   - 不同云区域之间并行下发
        # ----------------------------------------------------------------
        cloud_ip_map: Dict[int, set] = defaultdict(set)
        for info in self.data["infos"]:
            for rebuild_proxy_host in info["rebuild_proxy_hosts"]:
                cloud_ip_map[int(rebuild_proxy_host["bk_cloud_id"])].add(rebuild_proxy_host["ip"])

        for bk_cloud_id, ip_set in cloud_ip_map.items():
            exec_ips = sorted(ip_set)
            rebuild_pipeline.add_act(
                act_name=_("下发db-actuator介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=bk_cloud_id,
                        exec_ip=exec_ips,
                        file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    )
                ),
            )

        cluster_sub_pipelines = []

        for info in self.data["infos"]:
            # 拼接子流程需要全局参数
            flow_context = copy.deepcopy(self.data)
            flow_context.pop("infos")

            cluster_id = info["cluster_id"]
            try:
                cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=int(self.data["bk_biz_id"]))
            except Cluster.DoesNotExist:
                raise ClusterNotExistException(
                    cluster_id=cluster_id,
                    bk_biz_id=int(self.data["bk_biz_id"]),
                    message=_("集群不存在"),
                )

            # 针对集群维度声明子流程（一个集群下可能有多台 proxy 需要重建）
            cluster_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(flow_context))

            # 按 proxy 机器维度并行构造 rebuild 子流程
            proxy_sub_pipelines = []
            for rebuild_proxy_host in info["rebuild_proxy_hosts"]:
                rebuild_proxy_ip = rebuild_proxy_host["ip"]
                bk_cloud_id = int(rebuild_proxy_host["bk_cloud_id"])

                # 获取待重建的 proxy 实例（取该集群在本机器上的 proxy 实例）
                try:
                    rebuild_proxy = ProxyInstance.objects.get(
                        cluster=cluster,
                        machine__ip=rebuild_proxy_ip,
                        machine__bk_cloud_id=bk_cloud_id,
                    )
                except ProxyInstance.DoesNotExist:
                    raise Exception(
                        _("集群[{}]中找不到IP[{}]对应的proxy实例，请检查元数据").format(cluster.immute_domain, rebuild_proxy_ip)
                    )
                except ProxyInstance.MultipleObjectsReturned:
                    raise Exception(
                        _("集群[{}]中IP[{}]存在多个proxy实例，元数据异常请联系DBA").format(cluster.immute_domain, rebuild_proxy_ip)
                    )

                proxy_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(flow_context))

                # --------------------------------------------------------
                # 步骤1：修改 proxy 的 instance 状态为 restoring
                # --------------------------------------------------------
                proxy_sub_pipeline.add_act(
                    act_name=_("更新proxy实例状态为restoring[{}:{}]").format(rebuild_proxy_ip, rebuild_proxy.port),
                    act_component_code=MySQLDBMetaComponent.code,
                    kwargs=asdict(
                        DBMetaOPKwargs(
                            db_meta_class_func=MySQLDBMeta.update_proxy_instance_status.__name__,
                            cluster={
                                "proxy_ip": rebuild_proxy_ip,
                                "port": rebuild_proxy.port,
                                "phase": InstancePhase.ONLINE,
                                "status": InstanceStatus.RESTORING,
                            },
                        )
                    ),
                )

                # --------------------------------------------------------
                # 步骤2：检查待重建 proxy 实例连接
                #   - 安全模式下做检查，存在业务连接则抛异常终止
                # --------------------------------------------------------
                if self.data.get("is_safe", True):
                    proxy_sub_pipeline.add_act(
                        act_name=_("检测Proxy端连接情况[{}:{}]").format(rebuild_proxy_ip, rebuild_proxy.admin_port),
                        act_component_code=CheckClientConnComponent.code,
                        kwargs=asdict(
                            CheckClientConnKwargs(
                                bk_cloud_id=cluster.bk_cloud_id,
                                check_instances=[f"{rebuild_proxy_ip}{IP_PORT_DIVIDER}{rebuild_proxy.admin_port}"],
                                is_proxy=True,
                            )
                        ),
                    )

                # --------------------------------------------------------
                # 步骤3：回收 proxy 实例所有的域名映射
                #   - 在做"后端再配置 / 白名单再克隆"期间，不希望有业务流量打入该 proxy
                #   - 这里按集群维度调用 BuildEntrysManageSubflow 做 RECYCLE_RECORD
                #     会回收当前 proxy 在该集群上的所有域名/访问入口映射
                # --------------------------------------------------------
                recycle_entry_sub_process = BuildEntrysManageSubflow(
                    root_id=self.root_id,
                    ticket_data=self.data,
                    op_type=DnsOpType.RECYCLE_RECORD,
                    param={
                        "cluster_id": cluster.id,
                        "port": rebuild_proxy.port,
                        "del_ips": [rebuild_proxy_ip],
                    },
                )
                proxy_sub_pipeline.add_sub_pipeline(sub_flow=recycle_entry_sub_process)

                # --------------------------------------------------------
                # 步骤4：重新配置 proxy 的后端实例
                #   - 让 proxy 感知当前集群最新的 backend 信息（主/从）
                # --------------------------------------------------------
                proxy_sub_pipeline.add_act(
                    act_name=_("proxy重新配置后端实例[{}:{}]").format(rebuild_proxy_ip, rebuild_proxy.port),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(
                        ExecActuatorKwargs(
                            bk_cloud_id=cluster.bk_cloud_id,
                            exec_ip=rebuild_proxy_ip,
                            component_kwargs={"cluster_id": cluster.id, "force": True},
                            get_mysql_payload_func=ProxyActPayload.get_set_proxy_backends_in_cluster.__name__,
                        )
                    ),
                )

                # --------------------------------------------------------
                # 步骤5：克隆 proxy 的用户白名单
                #   - 从集群内其它 RUNNING 状态的 proxy 克隆用户白名单到本 proxy
                #   - 注意：组件内部会挑选集群内可用的模板 proxy 作为来源
                # --------------------------------------------------------
                proxy_sub_pipeline.add_act(
                    act_name=_("克隆proxy用户白名单[{}:{}]").format(rebuild_proxy_ip, rebuild_proxy.port),
                    act_component_code=CloneProxyUsersInClusterComponent.code,
                    kwargs=asdict(
                        CloneProxyUsersKwargs(
                            cluster_id=cluster.id,
                            target_proxy_host=rebuild_proxy_ip,
                        )
                    ),
                )

                # --------------------------------------------------------
                # 步骤6：在后端 MySQL 上为新 proxy 的 IP 创建访问权限
                #   - 参考集群内其它 RUNNING 状态的 proxy 的授权，
                #     复制一份给当前重建的 proxy IP，否则后端 MySQL 会拒绝其连接
                #   - origin_proxy_host：取集群内一个非本机的 RUNNING proxy 作为授权模板
                # --------------------------------------------------------
                template_proxy = (
                    ProxyInstance.objects.filter(cluster=cluster, status=InstanceStatus.RUNNING.value)
                    .exclude(machine__ip=rebuild_proxy_ip, machine__bk_cloud_id=bk_cloud_id)
                    .first()
                )
                if not template_proxy:
                    raise Exception(_("集群[{}]中找不到可用的RUNNING状态proxy作为授权克隆来源").format(cluster.immute_domain))
                proxy_sub_pipeline.add_act(
                    act_name=_("集群对重建proxy添加权限[{}:{}]").format(rebuild_proxy_ip, rebuild_proxy.port),
                    act_component_code=CloneProxyUsersInBackendComponent.code,
                    kwargs=asdict(
                        CloneProxyClientInBackendKwargs(
                            cluster_id=cluster.id,
                            target_proxy_host=rebuild_proxy_ip,
                            origin_proxy_host=template_proxy.machine.ip,
                        )
                    ),
                )

                # --------------------------------------------------------
                # 步骤7：添加 proxy 实例和集群主域名的映射关系
                #   - 重建完成后，把 proxy 重新挂回集群访问入口
                # --------------------------------------------------------
                create_entry_sub_process = BuildEntrysManageSubflow(
                    root_id=self.root_id,
                    ticket_data=self.data,
                    op_type=DnsOpType.CREATE,
                    param={
                        "cluster_id": cluster.id,
                        "port": rebuild_proxy.port,
                        "add_ips": [rebuild_proxy_ip],
                    },
                )
                proxy_sub_pipeline.add_sub_pipeline(sub_flow=create_entry_sub_process)

                # --------------------------------------------------------
                # 步骤8：修改 proxy 的 instance 状态为 running
                # --------------------------------------------------------
                proxy_sub_pipeline.add_act(
                    act_name=_("更新proxy实例状态为running[{}:{}]").format(rebuild_proxy_ip, rebuild_proxy.port),
                    act_component_code=MySQLDBMetaComponent.code,
                    kwargs=asdict(
                        DBMetaOPKwargs(
                            db_meta_class_func=MySQLDBMeta.update_proxy_instance_status.__name__,
                            cluster={
                                "proxy_ip": rebuild_proxy_ip,
                                "port": rebuild_proxy.port,
                                "phase": InstancePhase.ONLINE,
                                "status": InstanceStatus.RUNNING,
                            },
                        )
                    ),
                )

                proxy_sub_pipelines.append(
                    proxy_sub_pipeline.build_sub_process(
                        sub_name=_("重建proxy实例[{}:{}]").format(rebuild_proxy_ip, rebuild_proxy.port)
                    )
                )

            # 同一集群下、不同机器上的 proxy 实例重建流程并行
            cluster_sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=proxy_sub_pipelines)

            cluster_sub_pipelines.append(
                cluster_sub_pipeline.build_sub_process(sub_name=_("集群[{}]重建proxy实例").format(cluster.immute_domain))
            )

        rebuild_pipeline.add_parallel_sub_pipeline(sub_flow_list=cluster_sub_pipelines)

        # 启动接入单据值守监听（与 add / reduce / switch 保持一致）
        rebuild_pipeline.run_pipeline_with_sidecar(
            check_ai_monitor_cluster_list=list({info["cluster_id"] for info in self.data["infos"]}),
        )
