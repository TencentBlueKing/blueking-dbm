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
from backend.db_meta.enums import ClusterType
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import Cluster, ProxyInstance
from backend.db_package.constants import PackageType
from backend.db_package.models import Package
from backend.flow.consts import DnsOpType, InstanceStatus
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.entrys_manager import BuildEntrysManageSubflow
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.common.common_sub_flow import init_machine_sub_flow
from backend.flow.engine.bamboo.scene.mysql.common.exceptions import ProxyFlowFailedException
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.departs import DeployPeripheralToolsDepart
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.subflow import standardize_mysql_cluster_subflow
from backend.flow.plugins.components.collections.common.add_unlock_ticket_type_config import (
    AddUnlockTicketTypeConfigComponent,
)
from backend.flow.plugins.components.collections.common.delete_cc_service_instance import DelCCServiceInstComponent
from backend.flow.plugins.components.collections.common.pause_with_ticket_lock_check import (
    PauseWithTicketLockCheckComponent,
)
from backend.flow.plugins.components.collections.mysql.check_client_connections import CheckClientConnComponent
from backend.flow.plugins.components.collections.mysql.clear_machine import MySQLClearMachineComponent
from backend.flow.plugins.components.collections.mysql.clone_proxy_client_in_backend import (
    CloneProxyUsersInBackendComponent,
)
from backend.flow.plugins.components.collections.mysql.clone_proxy_user_in_cluster import (
    CloneProxyUsersInClusterComponent,
)
from backend.flow.plugins.components.collections.mysql.drop_proxy_client_in_backend import (
    DropProxyUsersInBackendComponent,
)
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.flow_output_summary import MysqlFlowOutputSummaryComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.base.base_dataclass import AddUnLockTicketTypeKwargs, ReleaseUnLockTicketTypeKwargs
from backend.flow.utils.mysql.common.mysql_cluster_info import get_mysql_init_os_timezone_kwargs
from backend.flow.utils.mysql.flow_output_presets import InstanceChangeAction
from backend.flow.utils.mysql.mysql_act_dataclass import (
    CheckClientConnKwargs,
    CloneProxyClientInBackendKwargs,
    CloneProxyUsersKwargs,
    DBMetaOPKwargs,
    DelServiceInstKwargs,
    DownloadMediaKwargs,
    DropProxyUsersInBackendKwargs,
    ExecActuatorKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import SystemInfoContext
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta
from backend.flow.utils.mysql.proxy_act_payload import ProxyActPayload
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class MySQLProxyClusterSwitchFlow(object):
    """
    构建mysql集群替换proxy实例申请流程抽象类
    替换proxy 是属于整机替换，新的机器必须不在dbm系统记录上线过
    兼容跨云区域的场景支持
    {
        "uid": "x",
        "created_by": "x",
        "bk_biz_id": "x",
        "ticket_type": "MYSQL_PROXY_SWITCH",
        "force": false,
        "infos": [
              {
                "cluster_ids": [1,2],
                "origin_proxies":{"ip": "x", "bk_cloud_id": 0, "bk_host_id": 0, "bk_biz_id": 1, "spec":{}},
                "target_proxies":{"ip": "x", "bk_cloud_id": 0, "bk_host_id": 0, "bk_biz_id": 1, "spec":{}},
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
        self.data = self.tran_ticket_data(data)

    @staticmethod
    def tran_ticket_data(ticket_data: dict) -> dict:
        """
        针对传进来的单据参数，转换成适配flow的参数规则：
        转换规则：
        将每一行的替换信息，按照传入的info["origin_proxies"], 与info["target_proxies"]进行一对一的拆分。
        eg:
        old:
        {
            "cluster_ids": [1,2],
            "origin_proxies": [
                    {"ip": "ip1", "bk_cloud_id": 0, "bk_host_id": 0, "bk_biz_id": 1, "spec":{...}},
                    {"ip": "ip3", "bk_cloud_id": 0, "bk_host_id": 0, "bk_biz_id": 1, "spec":{...}},
                ],
            },
            "target_proxies": [
                {"ip": "ip2", "bk_cloud_id": 0, "bk_host_id": 0, "bk_biz_id": 1, "spec":{...}},
                {"ip": "ip4", "bk_cloud_id": 0, "bk_host_id": 0, "bk_biz_id": 1, "spec":{...}},
            ],
        }
        new:
        [
            {
                "cluster_ids": [1,2],
                "origin_proxy":{"ip": "ip1", "bk_cloud_id": 0, "bk_host_id": 0, "bk_biz_id": 1, "spec":{...}},
                "target_proxy":{"ip": "ip2", "bk_cloud_id": 0, "bk_host_id": 0, "bk_biz_id": 1, "spec":{...}},
            },
            {
                "cluster_ids": [1,2],
                "origin_proxy":{"ip": "ip3", "bk_cloud_id": 0, "bk_host_id": 0, "bk_biz_id": 1, "spec":{...}},
                "target_proxy":{"ip": "ip4", "bk_cloud_id": 0, "bk_host_id": 0, "bk_biz_id": 1, "spec":{...}},
            },
        ]
        """
        new_infos = []
        for info in ticket_data["infos"]:
            if len(info["origin_proxies"]) != len(info["target_proxies"]):
                raise ProxyFlowFailedException(_("替换的主机数量和新申请到的主机数量不相等"))

            for index, origin_proxy in enumerate(info["origin_proxies"]):
                # 根据origin_proxy_和target_proxy的维度，拆开重新赋值到new_info列表，
                # 首先要判断每一行origin_proxy/target_proxy的长度是否一致，如果不一致，则代表机器申请资源不对等，抛出异常
                new_info = {
                    "cluster_ids": info["cluster_ids"],
                    "origin_proxy": origin_proxy,
                    "target_proxy": info["target_proxies"][index],
                }
                new_infos.append(new_info)

        # 返回更新后的数据
        return {**ticket_data, "infos": new_infos}

    @staticmethod
    def get_proxy_pkg_id_for_origin_proxy(origin_proxy_ip: str, bk_cloud_id: int):
        """
        根据已存在的proxy机器，获取待添加proxy节点版本介质包
        @param origin_proxy_ip: 参考proxy ip, 必须参数
        @param bk_cloud_id: 云区域ID
        """

        # 根据参考proxy节点
        # 返回对应的 package id
        version_no = (
            ProxyInstance.objects.filter(machine__ip=origin_proxy_ip, machine__bk_cloud_id=bk_cloud_id).first().version
        )
        return Package.get_package_for_version_no(
            db_type=DBType.MySQL, pkg_type=PackageType.MySQLProxy, version_no=version_no
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
    def _build_switch_items_for_info(info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """按单个 info 行装配"proxy 替换摘要" items（对齐 :class:`InstanceChangeSummarySerializer`）。

        功能说明 / 怎么做：
          - 一个 info 行 = 一对一替换（origin_proxy → target_proxy） × 一组 cluster_ids；
            产出 `len(cluster_ids)` 行摘要，每行 action=SWITCH。
          - "一次替换一行"的表达方式：``instance`` 记新上线的 target_proxy:port（前端点进去能看到活着的实例），
            ``related_instance`` 记被替换下架的 origin_proxy:port；由 :class:`InstanceChangeAction`
            的 SWITCH 值隐含表达"这是替换动作"，无需拆两行。
          - 每个集群的 proxy 端口沿用替换前后一致的原则从 db_meta 反查（取该集群任意一个 ProxyInstance
            的 port）。

        :param info: 单个 ``self.data["infos"]`` 元素（已由 ``tran_ticket_data`` 拆成一对一形态），
                     含 ``cluster_ids`` / ``origin_proxy`` / ``target_proxy``
        :return: 摘要行列表；结构严格对齐 InstanceChangeSummarySerializer 字段契约

        边界 / 异常：
          - ``cluster_ids`` 为空 -> 返回空列表；
          - 某个 cluster_id 在 db_meta 不存在或无 ProxyInstance -> 忽略该集群，不产出对应行；
            该场景在主流程更早的端口计算阶段就会先失败，此处属兜底防御。
        """
        items: List[Dict[str, Any]] = []
        cluster_ids: List[int] = list(info.get("cluster_ids") or [])
        origin_proxy: Dict[str, Any] = info.get("origin_proxy") or {}
        target_proxy: Dict[str, Any] = info.get("target_proxy") or {}
        if not cluster_ids or not origin_proxy or not target_proxy:
            return items

        cluster_map: Dict[int, Cluster] = {c.id: c for c in Cluster.objects.filter(id__in=cluster_ids)}
        for cluster_id in cluster_ids:
            cluster: Optional[Cluster] = cluster_map.get(cluster_id)
            if cluster is None:
                continue
            proxy_ref: Optional[ProxyInstance] = ProxyInstance.objects.filter(cluster=cluster).first()
            if proxy_ref is None:
                continue
            port: int = int(proxy_ref.port)
            items.append(
                {
                    "cluster_domain": cluster.immute_domain,
                    "instance": f"{target_proxy['ip']}{IP_PORT_DIVIDER}{port}",
                    "action": InstanceChangeAction.SWITCH.value,
                    "status": "success",
                    "related_instance": f"{origin_proxy['ip']}{IP_PORT_DIVIDER}{port}",
                    "message": "",
                }
            )
        return items

    def switch_mysql_cluster_proxy_flow(self):
        """
        定义mysql集群proxy替换实例流程
        """
        mysql_proxy_cluster_add_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        # DB_HA 自愈复用了这个 flow, 需要禁用人工确认节点才能全自动化
        # 为了不影响已有单据, 增加一个 default = False 的控制变量
        disable_manual_confirm = self.data.get("disable_manual_confirm", False)

        # 多集群操作时循环加入集群proxy替换子流程
        # 这流程一个 info 只处理一个 ip
        # 如果一个集群有 2 个 ip, 会有 2 个 info
        # info 的驱动是 ip, 一个 ip 对应 >= 1 个集群
        for info in self.data["infos"]:
            # 拼接子流程需要全局参数
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("infos")

            sub_flow_context["proxy_ports"] = self.__get_proxy_install_ports(cluster_ids=info["cluster_ids"])
            instances = ["{}:{}".format(info["target_proxy"]["ip"], port) for port in sub_flow_context["proxy_ports"]]
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

            # 拼接执行原子任务活动节点需要的通用的私有参数结构体, 减少代码重复率，但引用时注意内部参数值传递的问题
            exec_act_kwargs = ExecActuatorKwargs(
                cluster_type=ClusterType.TenDBHA,
                exec_ip=info["target_proxy"]["ip"],
                bk_cloud_id=info["target_proxy"]["bk_cloud_id"],
            )

            # 解除对主从迁移的单据互斥锁，这个阶段到下一个暂停节点，允许主从迁移单据进入执行
            # if not disable_manual_confirm:
            sub_pipeline.add_act(
                act_name=_("解锁部分单据互斥锁"),
                act_component_code=AddUnlockTicketTypeConfigComponent.code,
                kwargs=asdict(
                    AddUnLockTicketTypeKwargs(
                        cluster_ids=info["cluster_ids"], unlock_ticket_type_list=[TicketType.MYSQL_MIGRATE_CLUSTER]
                    )
                ),
            )

            # 初始新机器
            sub_pipeline.add_sub_pipeline(
                sub_flow=init_machine_sub_flow(
                    uid=sub_flow_context["uid"],
                    root_id=self.root_id,
                    bk_cloud_id=int(info["target_proxy"]["bk_cloud_id"]),
                    sys_init_ips=[info["target_proxy"]["ip"]],
                    init_check_ips=[info["target_proxy"]["ip"]],
                    yum_install_perl_ips=[info["target_proxy"]["ip"]],
                    bk_host_ids=[info["target_proxy"]["bk_host_id"]],
                    init_os_tz_kwargs=get_mysql_init_os_timezone_kwargs(
                        cluster=Cluster.objects.get(id=info["cluster_ids"][0]),
                        exec_ip=[info["target_proxy"]["ip"]],
                    ),
                )
            )

            # 阶段1 已机器维度，安装先上架的proxy实例
            # 计算出新机器所需要安装的介质包ID，并赋值到info结构体
            info["target_proxy_pkg_id"] = self.get_proxy_pkg_id_for_origin_proxy(
                info["origin_proxy"]["ip"], int(info["origin_proxy"]["bk_cloud_id"])
            )
            sub_pipeline.add_act(
                act_name=_("下发proxy安装介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=info["target_proxy"]["bk_cloud_id"],
                        exec_ip=info["target_proxy"]["ip"],
                        file_list=GetFileList(db_type=DBType.MySQL).mysql_proxy_upgrade_package(
                            pkg_id=info["target_proxy_pkg_id"]
                        ),
                    )
                ),
            )

            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_install_proxy_for_add_payload.__name__
            exec_act_kwargs.component_kwargs = {"pkg_id": info["target_proxy_pkg_id"]}
            sub_pipeline.add_act(
                act_name=_("部署proxy实例"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(exec_act_kwargs),
            )
            # 后续流程需要在这里加一个暂停节点，让用户在合适的时间执行切换
            # 这里会释放前一阶段解除对主从迁移的单据互斥锁，这个阶段不允许主从迁移单据进入执行
            if not disable_manual_confirm:
                sub_pipeline.add_act(
                    act_name=_("人工确认，判断互斥条件"),
                    act_component_code=PauseWithTicketLockCheckComponent.code,
                    kwargs=asdict(
                        ReleaseUnLockTicketTypeKwargs(
                            cluster_ids=info["cluster_ids"],
                            release_unlock_ticket_type_list=[TicketType.MYSQL_MIGRATE_CLUSTER],
                        )
                    ),
                )

            # 阶段2 根据需要替换的proxy的集群，依次添加
            switch_proxy_sub_list = []
            for cluster_id in info["cluster_ids"]:
                # 拼接子流程需要全局参数
                sub_sub_flow_context = copy.deepcopy(self.data)
                sub_sub_flow_context.pop("infos")

                # 获取集群的实例信息
                # 获取对应集群相关对象
                try:
                    cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=int(self.data["bk_biz_id"]))
                except Cluster.DoesNotExist:
                    raise ClusterNotExistException(
                        cluster_id=cluster_id, bk_biz_id=int(self.data["bk_biz_id"]), message=_("集群不存在")
                    )
                # 获取proxy端口
                proxy_port = ProxyInstance.objects.filter(cluster=cluster).first().port

                # 针对集群维度声明替换子流程
                switch_proxy_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_sub_flow_context))

                switch_proxy_sub_pipeline.add_act(
                    act_name=_("新的proxy配置后端实例[{}:{}]".format(info["target_proxy"]["ip"], proxy_port)),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(
                        ExecActuatorKwargs(
                            bk_cloud_id=cluster.bk_cloud_id,
                            component_kwargs={"cluster_id": cluster.id},
                            exec_ip=info["target_proxy"]["ip"],
                            get_mysql_payload_func=ProxyActPayload.get_set_proxy_backends_in_cluster.__name__,
                        )
                    ),
                )

                switch_proxy_sub_pipeline.add_act(
                    act_name=_("克隆proxy用户白名单"),
                    act_component_code=CloneProxyUsersInClusterComponent.code,
                    kwargs=asdict(
                        CloneProxyUsersKwargs(
                            cluster_id=cluster.id,
                            target_proxy_host=info["target_proxy"]["ip"],
                        )
                    ),
                )

                switch_proxy_sub_pipeline.add_act(
                    act_name=_("集群对新的proxy添加权限"),
                    act_component_code=CloneProxyUsersInBackendComponent.code,
                    kwargs=asdict(
                        CloneProxyClientInBackendKwargs(
                            cluster_id=cluster.id,
                            target_proxy_host=info["target_proxy"]["ip"],
                            origin_proxy_host=info["origin_proxy"]["ip"],
                        )
                    ),
                )

                create_entry_sub_process = BuildEntrysManageSubflow(
                    root_id=self.root_id,
                    ticket_data=self.data,
                    op_type=DnsOpType.CREATE,
                    param={
                        "cluster_id": cluster.id,
                        "port": proxy_port,
                        "add_ips": [info["target_proxy"]["ip"]],
                    },
                )
                switch_proxy_sub_pipeline.add_sub_pipeline(create_entry_sub_process)
                recycle_entry_sub_process = BuildEntrysManageSubflow(
                    root_id=self.root_id,
                    ticket_data=self.data,
                    op_type=DnsOpType.RECYCLE_RECORD,
                    param={
                        "cluster_id": cluster.id,
                        "port": proxy_port,
                        "del_ips": [info["origin_proxy"]["ip"]],
                    },
                )
                switch_proxy_sub_pipeline.add_sub_pipeline(recycle_entry_sub_process)

                switch_proxy_sub_list.append(
                    switch_proxy_sub_pipeline.build_sub_process(
                        sub_name=_("{}集群替换proxy实例").format(cluster.immute_domain)
                    )
                )

            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=switch_proxy_sub_list)

            # 先把新的节点数据写入
            sub_pipeline.add_act(
                act_name=_("新proxy记录元数据"),
                act_component_code=MySQLDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.mysql_proxy_add.__name__,
                        component_kwargs={
                            "new_proxies": [info["target_proxy"]],
                            "proxy_ports": sub_flow_context["proxy_ports"],
                            "cluster_ids": info["cluster_ids"],
                            "created_by": self.data["created_by"],
                            "target_proxy_pkg_id": info["target_proxy_pkg_id"],
                            "template_proxy_ip": info["origin_proxy"]["ip"],
                        },
                    )
                ),
            )

            # 不能放在最后
            # 不然一直不点确认就不会安装监控, 有危险
            # 这里所在的循环是按 ip 来发起 subflow
            # 所以肯定只有一个 bk cloud id
            sub_pipeline.add_sub_pipeline(
                sub_flow=standardize_mysql_cluster_subflow(
                    root_id=self.root_id,
                    data=copy.deepcopy(self.data),
                    bk_cloud_id=info["target_proxy"]["bk_cloud_id"],
                    bk_biz_id=self.data["bk_biz_id"],
                    instances=instances,
                    departs=[
                        DeployPeripheralToolsDepart.DBAToolKit,
                        DeployPeripheralToolsDepart.MySQLCrond,
                        DeployPeripheralToolsDepart.MySQLMonitor,
                    ],
                    with_actuator=False,
                    with_bk_plugin=False,
                    with_collect_sysinfo=True,
                )
            )

            # 阶段4 后续流程需要在这里加一个暂停节点，让用户在合适的时间执行下架旧实例操作
            if not disable_manual_confirm:
                sub_pipeline.add_act(
                    act_name=_("人工确认，判断互斥条件"),
                    act_component_code=PauseWithTicketLockCheckComponent.code,
                    kwargs=asdict(
                        ReleaseUnLockTicketTypeKwargs(
                            cluster_ids=info["cluster_ids"],
                            release_unlock_ticket_type_list=[],
                        )
                    ),
                )

            # 阶段5 机器维度，下架旧机器节点
            reduce_proxy_sub_list = []
            has_unavailable_instance = False
            for cluster_id in info["cluster_ids"]:
                cluster = Cluster.objects.get(id=cluster_id)
                proxyinstance_obj = ProxyInstance.objects.get(cluster=cluster, machine__ip=info["origin_proxy"]["ip"])

                has_unavailable_instance |= proxyinstance_obj.status == InstanceStatus.UNAVAILABLE
                reduce_proxy_sub_list.append(
                    self.proxy_reduce_sub_flow(
                        cluster_id=cluster.id,
                        bk_cloud_id=cluster.bk_cloud_id,
                        origin_proxy_ip=info["origin_proxy"]["ip"],
                        origin_proxy_port=proxyinstance_obj.port,
                        admin_proxy_port=proxyinstance_obj.admin_port,
                        disable_manual_confirm=disable_manual_confirm,
                        error_ignorable=proxyinstance_obj.status == InstanceStatus.UNAVAILABLE,
                    )
                )
            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=reduce_proxy_sub_list)

            # 阶段6 按照机器维度变更db-meta数据
            sub_pipeline.add_act(
                act_name=_("回收旧proxy机器的元数据信息"),
                act_component_code=MySQLDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.mysql_proxy_reduce.__name__,
                        component_kwargs={
                            "cluster_ids": info["cluster_ids"],
                            "origin_proxy_ip": info["origin_proxy"]["ip"],
                        },
                    )
                ),
            )

            # 阶段7 清理机器级别的配置
            exec_act_kwargs.exec_ip = info["origin_proxy"]["ip"]
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_clear_machine_crontab.__name__
            sub_pipeline.add_act(
                act_name=_("清理机器配置"),
                act_component_code=MySQLClearMachineComponent.code,
                kwargs=asdict(exec_act_kwargs),
                error_ignorable=has_unavailable_instance,
            )

            # ==================== 阶段8：写入proxy变更摘要 ====================
            # 外层子流程（按 origin/target 一对一分片）所有变更 act 完成后，一次性写入本 info 涉及的
            # 所有集群维度的替换摘要行（每集群一行，action=switch，related_instance 指向被替换掉的旧机）。
            # 幂等由 InstanceChangeSummarySerializer.table_primary_key = "instance" 保证。
            sub_pipeline.add_act(
                act_name=_("写入proxy变更摘要"),
                act_component_code=MysqlFlowOutputSummaryComponent.code,
                kwargs={
                    "preset": "instance_change",
                    "items": self._build_switch_items_for_info(info),
                },
                is_remote_rewritable=True,
            )

            sub_pipelines.append(
                sub_pipeline.build_sub_process(
                    sub_name=_("替换proxy子流程[{}]->[{}]".format(info["origin_proxy"]["ip"], info["target_proxy"]["ip"]))
                )
            )

        mysql_proxy_cluster_add_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        # 启动接入单据值守监听
        mysql_proxy_cluster_add_pipeline.run_pipeline_with_sidecar(
            init_trans_data_class=SystemInfoContext(),
            check_ai_monitor_cluster_list=list({cid for info in self.data["infos"] for cid in info["cluster_ids"]}),
        )

    def proxy_reduce_sub_flow(
        self,
        cluster_id: int,
        bk_cloud_id: int,
        origin_proxy_ip: str,
        origin_proxy_port: int,
        admin_proxy_port: int,
        disable_manual_confirm: bool = False,
        # has_unavailable_instance: bool = False,
        error_ignorable: bool = False,
        # proxy_status: InstanceStatus = InstanceStatus.RUNNING,
    ):
        """
        回收proxy实例的子流程
        支持proxy多实例回收场景
        支持跨云操作
        @param cluster_id: 集群id
        @param bk_cloud_id: 集群所在的云区域
        @param origin_proxy_ip: 回收proxy ip 信息
        @param origin_proxy_port: 回收proxy 端口
        @param admin_proxy_port: 回收proxy 管理端口
        """

        # 拼接子流程需要全局参数
        flow_context = copy.deepcopy(self.data)
        flow_context.pop("infos")

        #  拼接替换proxy节点需要的通用的私有参数结构体, 减少代码重复率，但引用时注意内部参数值传递的问题
        reduce_proxy_sub_act_kwargs = ExecActuatorKwargs(
            bk_cloud_id=bk_cloud_id,
            exec_ip=origin_proxy_ip,
        )

        # 针对集群维度声明替换子流程
        sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(flow_context))

        # 非强制条件下：检查proxy实例是否在连接，是连接则报异常
        if self.data["is_safe"] and not disable_manual_confirm:
            sub_pipeline.add_act(
                act_name=_("检测Proxy端连接情况"),
                act_component_code=CheckClientConnComponent.code,
                kwargs=asdict(
                    CheckClientConnKwargs(
                        bk_cloud_id=bk_cloud_id,
                        check_instances=[f"{origin_proxy_ip}{IP_PORT_DIVIDER}{admin_proxy_port}"],
                        is_proxy=True,
                    )
                ),
                error_ignorable=error_ignorable,
            )

        # 清理对应的服务实例
        sub_pipeline.add_act(
            act_name=_("删除注册CC系统的服务实例"),
            act_component_code=DelCCServiceInstComponent.code,
            kwargs=asdict(
                DelServiceInstKwargs(
                    cluster_id=cluster_id,
                    del_instance_list=[{"ip": origin_proxy_ip, "port": origin_proxy_port}],
                )
            ),
        )

        # 阶段4 下架旧的proxy实例
        sub_pipeline.add_act(
            act_name=_("下发db-actuator介质"),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(
                DownloadMediaKwargs(
                    bk_cloud_id=bk_cloud_id,
                    exec_ip=origin_proxy_ip,
                    file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                ),
            ),
            error_ignorable=error_ignorable,
        )

        reduce_proxy_sub_act_kwargs.get_mysql_payload_func = (
            MysqlActPayload.get_clear_surrounding_config_payload.__name__
        )
        reduce_proxy_sub_act_kwargs.cluster = {"proxy_port": origin_proxy_port}
        sub_pipeline.add_act(
            act_name=_("清理proxy实例级别周边配置"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(reduce_proxy_sub_act_kwargs),
            error_ignorable=error_ignorable,
        )

        reduce_proxy_sub_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_uninstall_proxy_payload.__name__
        reduce_proxy_sub_act_kwargs.component_kwargs = {
            "proxy_port": origin_proxy_port,
            "force": False,
        }
        sub_pipeline.add_act(
            act_name=_("卸载proxy实例"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(reduce_proxy_sub_act_kwargs),
            error_ignorable=error_ignorable,
        )

        sub_pipeline.add_act(
            act_name=_("回收旧proxy在backend权限"),
            act_component_code=DropProxyUsersInBackendComponent.code,
            kwargs=asdict(
                DropProxyUsersInBackendKwargs(
                    cluster_id=cluster_id,
                    origin_proxy_host=origin_proxy_ip,
                ),
            ),
        )

        return sub_pipeline.build_sub_process(sub_name=_("[{}:{}]下线").format(origin_proxy_ip, origin_proxy_port))
