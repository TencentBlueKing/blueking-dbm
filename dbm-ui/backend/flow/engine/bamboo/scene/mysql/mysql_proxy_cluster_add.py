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
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
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
                {"ip": "1.1.1.1", "bk_cloud_id": 0, "bk_host_id": 1, "bk_biz_id": 0, "spce":{...}},
                ....] # 新加机器信息
              },
            {
                "cluster_ids": [3,4],
                "new_proxies": [
                {"ip": "2.2.2.2", "bk_cloud_id": 0, "bk_host_id": 1, "bk_biz_id": 0, "spce":{...}},
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

    def add_mysql_cluster_proxy_flow(self):
        """
        定义mysql集群添加proxy实例流程
        """

        mysql_proxy_cluster_add_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        # 多集群操作时循环加入集群proxy下架子流程
        for info in self.data["infos"]:
            # 拼接子流程需要全局参数
            # 获取第一个集群信息，作为按照介质包的依据，因为校验通过后 info["cluster_ids"] 属于同组共享集群，理论上版本都一致
            info["target_proxy_pkg_id"] = self.get_proxy_pkg_id_for_cluster(info["cluster_ids"][0])

            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("infos")

            # 计算它的部署端口范围
            sub_flow_context["proxy_ports"] = self.__get_proxy_install_ports(cluster_ids=info["cluster_ids"])

            # 声明子流程，按照前端每一行的维度，并发执行
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

            # 拼接执行原子任务活动节点需要的通用的私有参数结构体, 减少代码重复率，但引用时注意内部参数值传递的问题
            exec_act_kwargs = ExecActuatorKwargs(
                cluster_type=ClusterType.TenDBHA,
                bk_cloud_id=info["new_proxies"][0]["bk_cloud_id"],
            )

            # 初始新机器
            sub_pipeline.add_sub_pipeline(
                sub_flow=init_machine_sub_flow(
                    uid=sub_flow_context["uid"],
                    root_id=self.root_id,
                    bk_cloud_id=int(info["new_proxies"][0]["bk_cloud_id"]),
                    sys_init_ips=[i["ip"] for i in info["new_proxies"]],
                    init_check_ips=[i["ip"] for i in info["new_proxies"]],
                    yum_install_perl_ips=[i["ip"] for i in info["new_proxies"]],
                    bk_host_ids=[i["bk_host_id"] for i in info["new_proxies"]],
                )
            )

            # 阶段1 已机器维度，安装先上架的proxy实例
            # 获取第一个集群信息，作为按照介质包的依据，因为校验通过后 info["cluster_ids"] 属于同组共享集群，理论上版本都一致
            info["target_proxy_pkg_id"] = self.get_proxy_pkg_id_for_cluster(info["cluster_ids"][0])
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
            # 安装proxy实例，并发处理
            # 根据计算好的pkg_id，获取介质包
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

            # 阶段2 根据需要添加的proxy的集群，依次添加
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
                template_proxy = ProxyInstance.objects.filter(
                    cluster=cluster, status=InstanceStatus.RUNNING.value
                ).all()[0]

                # 针对集群维度声明子流程
                add_proxy_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_sub_flow_context))

                set_backend_acts_list = []
                clone_user_acts_list = []
                add_proxy_user_acts_list = []

                for new_proxy in info["new_proxies"]:
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

            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=add_proxy_sub_list)

            # 阶段3：拼接db-meta的新ip信息到私有变量cluster, 兼容同一台proxy机器属于不同cluster的录入场景
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

            # 阶段4：新proxy实例，添加周边程序
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

            sub_pipelines.append(
                sub_pipeline.build_sub_process(
                    sub_name=_("添加proxy子流程[{}]".format([i["ip"] for i in info["new_proxies"]]))
                )
            )

        mysql_proxy_cluster_add_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        mysql_proxy_cluster_add_pipeline.run_pipeline(init_trans_data_class=SystemInfoContext())
