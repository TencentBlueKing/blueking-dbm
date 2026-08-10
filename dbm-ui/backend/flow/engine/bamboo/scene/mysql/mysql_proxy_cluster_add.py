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
from typing import Any, Dict, List, Optional

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterType, InstanceStatus
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
from backend.flow.plugins.components.collections.mysql.clone_proxy_client_in_backend import (
    CloneProxyUsersInBackendComponent,
)
from backend.flow.plugins.components.collections.mysql.clone_proxy_user_in_cluster import (
    CloneProxyUsersInClusterComponent,
)
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.flow_output_summary import MysqlFlowOutputSummaryComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.common.mysql_cluster_info import get_mysql_init_os_timezone_kwargs
from backend.flow.utils.mysql.flow_output_presets import InstanceChangeAction
from backend.flow.utils.mysql.mysql_act_dataclass import (
    CloneProxyClientInBackendKwargs,
    CloneProxyUsersKwargs,
    DBMetaOPKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import SystemInfoContext
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta
from backend.flow.utils.mysql.proxy_act_payload import ProxyActPayload

logger = logging.getLogger("flow")


class MySQLProxyClusterAddFlow(object):
    """
    构建mysql集群添加proxy实例申请流程抽象类
    执行添加proxy 新的proxy机器，必须是不在dbm系统记录上线过
    兼容跨云区域的场景支持
    ticket_data参数：
    {
        "uid": "x", # 单据ID
        "created_by": "x", #提单人
        "bk_biz_id": "x", #业务ID
        "ticket_type": "MYSQL_PROXY_ADD", # 单据类型
        "infos": [ #对应前端每一行的入参信息
            {
                "cluster_ids": [1,2], # 集群列表信息，list
                "new_proxies": [
                {"ip": "1.1.1.1", "bk_cloud_id": 0, "bk_host_id": 1, "bk_biz_id": 0, "spec":{...}},
                ....] # 新加机器信息
              },
            {
                "cluster_ids": [3,4],
                "new_proxies": [
                {"ip": "2.2.2.2", "bk_cloud_id": 0, "bk_host_id": 1, "bk_biz_id": 0, "spec":{...}},
                ....]
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

    @staticmethod
    def get_proxy_pkg_id_for_cluster(cluster_id: int) -> int:
        """
        根据已存在的proxy机器，获取待添加proxy节点版本介质包
        @param cluster_id: 集群ID
        """
        cluster = Cluster.objects.get(id=cluster_id)
        all_proxys = cluster.proxyinstance_set.all()

        no_version_proxys = []
        for proxy in all_proxys:
            if not proxy.version:
                # 有没有写入版本信息proxy实例，收集起来，统一返回
                no_version_proxys.append(proxy.machine.ip)
        if no_version_proxys:
            raise ProxyFlowFailedException(_("检查到以下的proxy机器没有录入到版本信息:{}，请检查".format(no_version_proxys)))

        # 判断版本是否统一
        cluster_proxy_version_set = {p.version for p in all_proxys}
        if len(cluster_proxy_version_set) > 1:
            # 如果返回集合长度大于，则说明集群的proxy的版本存在多个，也需要人为介入
            raise ProxyFlowFailedException(
                _("检查到集群所有的proxy录入多个版本信息:{}，请检查".format([p.machine.ip for p in all_proxys]))
            )

        # 根据参考proxy节点
        # 返回对应的 package id
        return Package.get_package_for_version_no(
            db_type=DBType.MySQL, pkg_type=PackageType.MySQLProxy, version_no=str(cluster_proxy_version_set.pop())
        ).id

    @staticmethod
    def __get_proxy_install_ports(cluster_ids: list) -> list:
        """
        拼接proxy添加流程需要安装的端口，然后传入到流程的单据信息，安装proxy可以直接获取到
        @param: cluster_ids proxy机器需要新加入到集群的id列表，计算需要部署的端口列表
        """
        install_ports = []
        clusters = Cluster.objects.filter(id__in=cluster_ids).all()
        for cluster in clusters:
            cluster_proxy_port = ProxyInstance.objects.filter(cluster=cluster).all()[0].port
            install_ports.append(cluster_proxy_port)

        return install_ports

    @staticmethod
    def _build_add_items_for_info(info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """按单个 info 行装配"proxy 扩容摘要" items（对齐 :class:`InstanceChangeSummarySerializer`）。

        功能说明 / 怎么做：
          - 一个 info 行 = 一组共享 new_proxies × 一组 cluster_ids；产出笛卡尔积展开的摘要行：
            `len(new_proxies) × len(cluster_ids)` 行。
          - 每个集群的 proxy 端口从 db_meta 反查（取该集群任意一个已存在 proxy 的 port，与
            :meth:`__get_proxy_install_ports` 语义一致：同集群 proxy 端口约定一致）。
          - db_meta 约束下同业务同 IP:Port 唯一归属一个集群，因此 `instance` 单键足以承载幂等；
            集群归属通过一等字段 `cluster_domain` 表达。

        :param info: 单个 ``self.data["infos"]`` 元素；至少含 ``new_proxies`` / ``cluster_ids``
        :return: 摘要行列表；结构严格对齐 InstanceChangeSummarySerializer 字段契约。
                 集群或已有 proxy 缺失时该集群不贡献任何行（属于上游数据契约问题，由主流程更早的
                 校验/安装阶段暴露）。

        边界 / 异常：
          - ``new_proxies`` / ``cluster_ids`` 为空 -> 返回空列表；外层调用方对空 items 走 no-op 分支
            不阻塞流程。
          - 某个 cluster_id 在 db_meta 不存在或无任何 ProxyInstance -> 忽略该集群，不产出对应行；
            该场景在主流程"计算安装端口"阶段就会先失败，此处属兜底防御。
        """
        items: List[Dict[str, Any]] = []
        cluster_ids: List[int] = list(info.get("cluster_ids") or [])
        new_proxies: List[Dict[str, Any]] = list(info.get("new_proxies") or [])
        if not cluster_ids or not new_proxies:
            return items

        # 一次性反查涉及的集群，避免 N+1 查询
        cluster_map: Dict[int, Cluster] = {c.id: c for c in Cluster.objects.filter(id__in=cluster_ids)}
        for cluster_id in cluster_ids:
            cluster: Optional[Cluster] = cluster_map.get(cluster_id)
            if cluster is None:
                continue
            proxy_ref: Optional[ProxyInstance] = ProxyInstance.objects.filter(cluster=cluster).first()
            if proxy_ref is None:
                # 该集群尚无 proxy（理论上主流程会更早失败），此处不追加行
                continue
            port: int = int(proxy_ref.port)
            for new_proxy in new_proxies:
                items.append(
                    {
                        "cluster_domain": cluster.immute_domain,
                        "instance": f"{new_proxy['ip']}{IP_PORT_DIVIDER}{port}",
                        "action": InstanceChangeAction.ADD.value,
                        "status": "success",
                        "related_instance": "",
                        "message": "",
                    }
                )
        return items

    def add_mysql_cluster_proxy_flow(self):
        """
        定义mysql集群添加proxy实例流程

        流程设计总览：
        ┌─────────────────────────────────────────────────────────────────────┐
        │ 主流水线：按 self.data["infos"] 的每一行（一组 cluster_ids + 一组   │
        │ new_proxies）构造一个子流程，所有子流程之间【并行】执行。           │
        │                                                                     │
        │ 单个子流程顺序如下：                                                │
        │   0. 准备阶段：                                                     │
        │      - 计算 target_proxy_pkg_id（proxy 安装介质，按集群内已有 proxy│
        │        的版本决定，要求集群内 proxy 版本必须统一）                  │
        │      - 计算 proxy_ports（每个集群已有 proxy 的端口，新 proxy 沿用）│
        │      - init_machine_sub_flow：新机器系统初始化（sys_init / 环境   │
        │        检查 / yum 安装 perl 等）                                    │
        │                                                                     │
        │   阶段1【机器维度】安装 proxy（一次性完成，多个集群共享）：         │
        │      1.1 下发 proxy 安装介质到所有新机器                            │
        │      1.2 在每台新机器上并行安装 proxy 实例（按 proxy_ports 多端口  │
        │          一次性部署，因为这些集群在同一组机器上共享）               │
        │                                                                     │
        │   阶段2【集群维度】把新 proxy 接入每一个集群（集群之间并行）：      │
        │      2.1 set_backend：新 proxy 配置后端 MySQL 实例（写 proxy 的    │
        │          backend 列表）                                             │
        │      2.2 克隆 proxy 用户白名单：从已有 proxy 拷贝用户白名单到新    │
        │          proxy（让新 proxy 接受前端客户端连接）                     │
        │      2.3 集群对新 proxy 添加权限：在后端 MySQL 上为新 proxy 的 IP  │
        │          创建访问账号（让后端允许新 proxy 连入）                    │
        │      2.4 访问入口管理（DNS/CLB/北极星）：把新 proxy IP 加入到集群  │
        │          的访问入口中                                               │
        │                                                                     │
        │   阶段3：写入 db_meta 元信息（把新 proxy 注册到 DBM 元数据中）      │
        │                                                                     │
        │   阶段4：部署周边工具（DBAToolKit / MySQLCrond / MySQLMonitor）     │
        │                                                                     │
        │ 最后通过 run_pipeline_with_sidecar 启动流水线，并开启 AI 监控值守。│
        └─────────────────────────────────────────────────────────────────────┘
        """

        # 构建主流水线
        mysql_proxy_cluster_add_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        # 多集群操作时循环加入集群proxy下架子流程
        # 每个 info 对应前端一行：一组 cluster_ids 共享同一组 new_proxies 机器
        for info in self.data["infos"]:
            # ---------- 准备阶段 ----------
            # 拼接子流程需要全局参数
            # 获取第一个集群信息，作为按照介质包的依据，因为校验通过后 info["cluster_ids"] 属于同组共享集群，理论上版本都一致
            info["target_proxy_pkg_id"] = self.get_proxy_pkg_id_for_cluster(info["cluster_ids"][0])

            # 深拷贝 data 作为子流程上下文，剥离 infos 避免上下文过大
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("infos")

            # 计算它的部署端口范围
            # 新 proxy 机器上需要部署的端口列表 = 所有目标集群已有 proxy 的端口集合
            # 因为同一台新 proxy 机器可能同时加入多个集群，每个集群对应一个端口
            sub_flow_context["proxy_ports"] = self.__get_proxy_install_ports(cluster_ids=info["cluster_ids"])

            # 声明子流程，按照前端每一行的维度，并发执行
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

            # 拼接执行原子任务活动节点需要的通用的私有参数结构体, 减少代码重复率，但引用时注意内部参数值传递的问题
            exec_act_kwargs = ExecActuatorKwargs(
                cluster_type=ClusterType.TenDBHA,
                bk_cloud_id=info["new_proxies"][0]["bk_cloud_id"],
            )

            # 初始新机器
            # 对新加入的 proxy 机器做基础系统初始化：操作系统检查、环境准备、安装 perl 等依赖
            # 同机部署的集群，理论上模块id、业务id、云区域一致，所以取第一个集群的模块id、业务id、云区域即可
            sub_pipeline.add_sub_pipeline(
                sub_flow=init_machine_sub_flow(
                    uid=sub_flow_context["uid"],
                    root_id=self.root_id,
                    bk_cloud_id=int(info["new_proxies"][0]["bk_cloud_id"]),
                    sys_init_ips=[i["ip"] for i in info["new_proxies"]],
                    init_check_ips=[i["ip"] for i in info["new_proxies"]],
                    yum_install_perl_ips=[i["ip"] for i in info["new_proxies"]],
                    bk_host_ids=[i["bk_host_id"] for i in info["new_proxies"]],
                    init_os_tz_kwargs=get_mysql_init_os_timezone_kwargs(
                        cluster=Cluster.objects.get(id=info["cluster_ids"][0]),
                        exec_ip=[i["ip"] for i in info["new_proxies"]],
                    ),
                )
            )

            # ==================== 阶段1：机器维度 安装 proxy ====================
            # 阶段1 已机器维度，安装先上架的proxy实例
            # 获取第一个集群信息，作为按照介质包的依据，因为校验通过后 info["cluster_ids"] 属于同组共享集群，理论上版本都一致
            info["target_proxy_pkg_id"] = self.get_proxy_pkg_id_for_cluster(info["cluster_ids"][0])

            # 阶段1.1：下发 proxy 安装介质（二进制包）到所有新 proxy 机器
            sub_pipeline.add_act(
                act_name=_("下发proxy安装介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=int(info["new_proxies"][0]["bk_cloud_id"]),
                        exec_ip=[i["ip"] for i in info["new_proxies"]],
                        file_list=GetFileList(db_type=DBType.MySQL).mysql_proxy_upgrade_package(
                            info["target_proxy_pkg_id"]
                        ),
                    )
                ),
            )
            # 阶段1.2：安装proxy实例，并发处理
            # 根据计算好的pkg_id，获取介质包
            # 每台新机器上按 proxy_ports 一次性部署多个端口的 proxy 实例（机器之间并行）
            acts_list = []
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_install_proxy_for_add_payload.__name__
            for new_proxy in info["new_proxies"]:
                exec_act_kwargs.exec_ip = new_proxy["ip"]
                exec_act_kwargs.component_kwargs = {"pkg_id": info["target_proxy_pkg_id"]}
                acts_list.append(
                    {
                        "act_name": _("安装proxy实例[{}]".format(new_proxy["ip"])),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(exec_act_kwargs),
                    }
                )

            sub_pipeline.add_parallel_acts(acts_list=acts_list)

            # ==================== 阶段2：集群维度 将新 proxy 接入各集群 ====================
            # 阶段2 根据需要添加的proxy的集群，依次添加
            # 每个集群对应一个独立的子子流程，集群之间【并行】执行
            add_proxy_sub_list = []
            for cluster_id in info["cluster_ids"]:
                # 拼接子流程需要全局参数
                sub_sub_flow_context = copy.deepcopy(self.data)
                sub_sub_flow_context.pop("infos")

                # 获取对应集群相关对象
                try:
                    cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=int(self.data["bk_biz_id"]))
                except Cluster.DoesNotExist:
                    raise ClusterNotExistException(
                        cluster_id=cluster_id, bk_biz_id=int(self.data["bk_biz_id"]), message=_("集群不存在")
                    )
                # 取一个 RUNNING 状态的已有 proxy 作为"模板 proxy"，用于：
                #   - 确定新 proxy 的端口（template_proxy.port）
                #   - 作为克隆白名单 / 克隆后端权限 的来源
                template_proxy = ProxyInstance.objects.filter(
                    cluster=cluster, status=InstanceStatus.RUNNING.value
                ).all()[0]

                # 针对集群维度声明子流程
                add_proxy_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_sub_flow_context))

                # 为当前集群收集 3 组并行动作：
                #   set_backend_acts_list     ：新 proxy 写入 backend 信息
                #   clone_user_acts_list      ：克隆 proxy 层的用户白名单
                #   add_proxy_user_acts_list  ：在后端 MySQL 上授权给新 proxy IP
                set_backend_acts_list = []
                clone_user_acts_list = []
                add_proxy_user_acts_list = []

                for new_proxy in info["new_proxies"]:
                    # 动作A：让新 proxy 感知到后端 MySQL（写 proxy 自己的 backends）
                    set_backend_acts_list.append(
                        {
                            "act_name": _("新的proxy配置后端实例[{}:{}]".format(new_proxy["ip"], template_proxy.port)),
                            "act_component_code": ExecuteDBActuatorScriptComponent.code,
                            "kwargs": asdict(
                                ExecActuatorKwargs(
                                    bk_cloud_id=cluster.bk_cloud_id,
                                    component_kwargs={"cluster_id": cluster.id},
                                    exec_ip=new_proxy["ip"],
                                    get_mysql_payload_func=ProxyActPayload.get_set_proxy_backends_in_cluster.__name__,
                                )
                            ),
                        }
                    )
                    # 动作B：从集群内已有 proxy 克隆用户白名单到新 proxy
                    #        （让前端客户端可以通过新 proxy 访问）
                    clone_user_acts_list.append(
                        {
                            "act_name": _("克隆proxy用户白名单[{}:{}]".format(new_proxy["ip"], template_proxy.port)),
                            "act_component_code": CloneProxyUsersInClusterComponent.code,
                            "kwargs": asdict(
                                CloneProxyUsersKwargs(
                                    cluster_id=cluster.id,
                                    target_proxy_host=new_proxy["ip"],
                                )
                            ),
                        }
                    )

                    # 动作C：在后端 MySQL 上为新 proxy 的 IP 创建访问权限
                    #        （参考 origin_proxy_host 的授权，复制一份给 target_proxy_host）
                    #        否则后端 MySQL 会拒绝新 proxy 的连接
                    add_proxy_user_acts_list.append(
                        {
                            "act_name": _("集群对新的proxy添加权限[{}:{}]".format(new_proxy["ip"], template_proxy.port)),
                            "act_component_code": CloneProxyUsersInBackendComponent.code,
                            "kwargs": asdict(
                                CloneProxyClientInBackendKwargs(
                                    cluster_id=cluster.id,
                                    target_proxy_host=new_proxy["ip"],
                                    origin_proxy_host=template_proxy.machine.ip,
                                )
                            ),
                        }
                    )
                # 阶段2.1: 并行执行新的proxy配置后端实例
                add_proxy_sub_pipeline.add_parallel_acts(acts_list=set_backend_acts_list)
                # 阶段2.2: 并行执行克隆proxy用户白名单
                add_proxy_sub_pipeline.add_parallel_acts(acts_list=clone_user_acts_list)
                # 阶段2.3: 并行执行集群对新的proxy添加权限
                add_proxy_sub_pipeline.add_parallel_acts(acts_list=add_proxy_user_acts_list)

                # 阶段2.4: 新proxy实例，做访问入口添加处理
                # 将新 proxy 的 IP 添加到集群的访问入口（DNS、CLB、北极星等）
                entry_sub_process = BuildEntrysManageSubflow(
                    root_id=self.root_id,
                    ticket_data=self.data,
                    op_type=DnsOpType.CREATE,
                    param={
                        "cluster_id": cluster.id,
                        "port": template_proxy.port,
                        "add_ips": [i["ip"] for i in info["new_proxies"]],
                    },
                )
                add_proxy_sub_pipeline.add_sub_pipeline(entry_sub_process)

                add_proxy_sub_list.append(
                    add_proxy_sub_pipeline.build_sub_process(
                        sub_name=_("集群[{}]添加proxy实例".format(cluster.immute_domain))
                    )
                )

            # 多个集群的"接入"子流程并行执行（互不影响）
            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=add_proxy_sub_list)

            # ==================== 阶段3：写 db_meta 元信息 ====================
            # 阶段3：拼接db-meta的新ip信息到私有变量cluster, 兼容同一台proxy机器属于不同cluster的录入场景
            # 将新增 proxy 实例正式注册到 DBM 元数据中（ProxyInstance、Machine、Cluster 关联等）
            sub_pipeline.add_act(
                act_name=_("添加db_meta元信息"),
                act_component_code=MySQLDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.mysql_proxy_add.__name__,
                        component_kwargs={
                            "new_proxies": info["new_proxies"],
                            "proxy_ports": sub_flow_context["proxy_ports"],
                            "cluster_ids": info["cluster_ids"],
                            "created_by": self.data["created_by"],
                            "target_proxy_pkg_id": info["target_proxy_pkg_id"],
                        },
                    )
                ),
            )

            # ==================== 阶段4：部署周边工具 ====================
            # 阶段4：新proxy实例，添加周边程序
            # 给新 proxy 实例部署周边工具：
            #   - DBAToolKit  ：DBA 工具包
            #   - MySQLCrond  ：定时任务调度器
            #   - MySQLMonitor：监控采集器
            # 注意：with_actuator=False / with_bk_plugin=False / with_collect_sysinfo=False
            # 表示此阶段只装周边，不再重复做 actuator 下发、bk 插件安装、系统信息采集
            sub_pipeline.add_sub_pipeline(
                sub_flow=standardize_mysql_cluster_subflow(
                    root_id=self.root_id,
                    data=copy.deepcopy(self.data),
                    bk_cloud_id=info["new_proxies"][0]["bk_cloud_id"],
                    bk_biz_id=self.data["bk_biz_id"],
                    instances=[
                        f"{new_proxy['ip']}{IP_PORT_DIVIDER}{port}"
                        for new_proxy in info["new_proxies"]
                        for port in sub_flow_context["proxy_ports"]
                    ],
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

            # ==================== 阶段5：写入proxy变更摘要 ====================
            # 外层子流程（按 info 分片）所有变更 act 完成后，一次性写入本 info 涉及的所有
            # (cluster × new_proxy) 摘要行；db_meta / 周边工具已就绪，摘要数据可靠。
            # 幂等由 InstanceChangeSummarySerializer.table_primary_key = "instance" 保证：
            # 同 IP:Port 重复写入 → 后写覆盖前写。
            sub_pipeline.add_act(
                act_name=_("写入proxy变更摘要"),
                act_component_code=MysqlFlowOutputSummaryComponent.code,
                kwargs={
                    "preset": "instance_change",
                    "items": self._build_add_items_for_info(info),
                },
                is_remote_rewritable=True,
            )

            sub_pipelines.append(
                sub_pipeline.build_sub_process(
                    sub_name=_("添加proxy子流程[{}]".format([i["ip"] for i in info["new_proxies"]]))
                )
            )

        # 所有 info 行对应的子流程并行执行
        mysql_proxy_cluster_add_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        # mysql_proxy_cluster_add_pipeline.run_pipeline(init_trans_data_class=SystemInfoContext())
        # 启动接入单据值守监听
        # run_pipeline_with_sidecar：在流水线运行时同时启动 AI 监控 sidecar，
        # 传入受影响的 cluster_id 集合，用于对这些集群做异常监控值守
        mysql_proxy_cluster_add_pipeline.run_pipeline_with_sidecar(
            init_trans_data_class=SystemInfoContext(),
            check_ai_monitor_cluster_list=list({cid for info in self.data["infos"] for cid in info["cluster_ids"]}),
        )
