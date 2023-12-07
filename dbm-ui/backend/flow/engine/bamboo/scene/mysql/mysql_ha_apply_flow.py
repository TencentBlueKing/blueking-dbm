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
from typing import Dict, Optional, Tuple

from django.utils.translation import ugettext as _

from backend import env
from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.common.common_sub_flow import (
    build_surrounding_apps_sub_flow,
    init_machine_sub_flow,
)
from backend.flow.plugins.components.collections.common.sa_idle_check import CheckMachineIdleComponent
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.mysql.mysql_os_init import MySQLOsInitComponent, SysInitComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import (
    CreateDnsKwargs,
    DBMetaOPKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import HaApplyManualContext
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta

logger = logging.getLogger("flow")


class MySQLHAApplyFlow(object):
    """
    构建mysql主从版申请流程的抽象类
    兼容跨云区域的场景支持
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data

    def __calc_install_ports(self, inst_sum: int = 0) -> Tuple[list, list]:
        """
        计算单据流程需要安装的端口，然后传入到流程的单据信息，ha集群包括有mysql实例和proxy实例
        @param : 代表机器部署实例数量
        """
        install_proxy_ports = []
        install_mysql_ports = []
        for i in range(0, inst_sum):
            install_proxy_ports.append(self.data["start_proxy_port"] + i)
            install_mysql_ports.append(self.data["start_mysql_port"] + i)

        return install_proxy_ports, install_mysql_ports

    def deploy_mysql_ha_flow_with_manual(self):
        """
        定义部署主从版集群的流程，资源是通过手动录入方式，兼容单机多实例的部署
        """
        mysql_ha_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []
        for info in self.data["apply_infos"]:
            # 以机器维度并发处理 内容：比如获取对应节点资源、先发介质、初始化机器、安装实例、安装备份进程

            # 拼接子流程需要全局参数
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("apply_infos")

            # 计算机器需要部署的proxy、mysql的端口列表，集群的依据：MIN(多实例上限,映射的cluster集群数量)
            sub_flow_context["proxy_ports"], sub_flow_context["mysql_ports"] = self.__calc_install_ports(
                min(int(sub_flow_context["inst_num"]), len(info["clusters"]))
            )

            clusters = []
            for number, cluster in enumerate(info["clusters"]):
                # 分配部署proxy_port、mysql_port、ip 、cluster的关系
                cluster["new_master_ip"] = info["mysql_ip_list"][0]["ip"]
                cluster["new_slave_ip"] = info["mysql_ip_list"][1]["ip"]
                cluster["new_proxy_1_ip"] = info["proxy_ip_list"][0]["ip"]
                cluster["new_proxy_2_ip"] = info["proxy_ip_list"][1]["ip"]
                cluster["set_backend_ip"] = cluster["new_master_ip"]
                cluster["mysql_port"] = sub_flow_context["mysql_ports"][number]
                cluster["proxy_port"] = sub_flow_context["proxy_ports"][number]
                clusters.append(cluster)
            sub_flow_context["clusters"] = clusters

            # 声明子流程
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

            # 拼接执行原子任务活动节点需要的通用的私有参数结构体, 减少代码重复率，但引用时注意内部参数值传递的问题
            exec_act_kwargs = ExecActuatorKwargs(
                bk_cloud_id=int(self.data["bk_cloud_id"]),
                cluster_type=ClusterType.TenDBHA,
            )

            # 初始新机器
            sub_pipeline.add_sub_pipeline(
                sub_flow=init_machine_sub_flow(
                    uid=sub_flow_context["uid"],
                    root_id=self.root_id,
                    bk_cloud_id=int(sub_flow_context["bk_cloud_id"]),
                    sys_init_ips=[ip_info["ip"] for ip_info in info["mysql_ip_list"] + info["proxy_ip_list"]],
                    init_check_ips=[ip_info["ip"] for ip_info in info["mysql_ip_list"] + info["proxy_ip_list"]],
                    yum_install_perl_ips=[ip_info["ip"] for ip_info in info["mysql_ip_list"] + info["proxy_ip_list"]],
                )
            )

            # 阶段1 并行分发安装文件
            sub_pipeline.add_parallel_acts(
                acts_list=[
                    {
                        "act_name": _("下发MySQL介质包"),
                        "act_component_code": TransFileComponent.code,
                        "kwargs": asdict(
                            DownloadMediaKwargs(
                                bk_cloud_id=int(self.data["bk_cloud_id"]),
                                exec_ip=[ip_info["ip"] for ip_info in info["mysql_ip_list"]],
                                file_list=GetFileList(db_type=DBType.MySQL).mysql_install_package(
                                    db_version=self.data["db_version"]
                                ),
                            )
                        ),
                    },
                    {
                        "act_name": _("下发Proxy介质包"),
                        "act_component_code": TransFileComponent.code,
                        "kwargs": asdict(
                            DownloadMediaKwargs(
                                bk_cloud_id=int(self.data["bk_cloud_id"]),
                                exec_ip=[ip_info["ip"] for ip_info in info["proxy_ip_list"]],
                                file_list=GetFileList(db_type=DBType.MySQL).mysql_proxy_install_package(),
                            )
                        ),
                    },
                ]
            )

            acts_list = []
            for ip_info in info["mysql_ip_list"] + info["proxy_ip_list"]:
                exec_act_kwargs.exec_ip = ip_info["ip"]
                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_deploy_mysql_crond_payload.__name__
                acts_list.append(
                    {
                        "act_name": _("部署mysql-crond"),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(exec_act_kwargs),
                    }
                )
            sub_pipeline.add_parallel_acts(acts_list=acts_list)

            # 阶段3 并发安装mysql、proxy 实例(一个活动节点部署多实例)
            acts_list = []
            for proxy_ip in info["proxy_ip_list"]:
                exec_act_kwargs.exec_ip = proxy_ip["ip"]
                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_install_proxy_payload.__name__
                acts_list.append(
                    {
                        "act_name": _("安装proxy实例"),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(exec_act_kwargs),
                    }
                )
            for mysql_ip in info["mysql_ip_list"]:
                exec_act_kwargs.exec_ip = mysql_ip["ip"]
                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_install_mysql_payload.__name__
                acts_list.append(
                    {
                        "act_name": _("安装MySQL实例"),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(exec_act_kwargs),
                        "write_payload_var": HaApplyManualContext.get_time_zone_var_name(),
                    }
                )
            sub_pipeline.add_parallel_acts(acts_list=acts_list)

            # 阶段4 以集群维度并发处理 集群内容：比如建立主从、proxy实例配置后端、添加对应的域名等步骤
            build_cluster_sub_list = []
            for cluster in sub_flow_context["clusters"]:

                # 拼接子流程需要全局参数
                cluster_sub_flow_context = copy.deepcopy(self.data)
                cluster_sub_flow_context.pop("apply_infos")

                # 声明子流程
                cluster_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(cluster_sub_flow_context))

                # 拼接子流程支持原子任务的活动节点需要的通用的私有参数结构体
                cluster_act_kwargs = ExecActuatorKwargs(bk_cloud_id=int(self.data["bk_cloud_id"]), cluster=cluster)

                cluster_act_kwargs.exec_ip = cluster["new_master_ip"]
                cluster_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_grant_mysql_repl_user_payload.__name__
                cluster_sub_pipeline.add_act(
                    act_name=_("新增repl帐户"),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(cluster_act_kwargs),
                    write_payload_var=HaApplyManualContext.get_sync_info_var_name(),
                )

                cluster_act_kwargs.exec_ip = cluster["new_slave_ip"]
                cluster_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_change_master_payload.__name__
                cluster_sub_pipeline.add_act(
                    act_name=_("建立主从关系"),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(cluster_act_kwargs),
                )

                acts_list = []
                for proxy_ip in [cluster["new_proxy_1_ip"], cluster["new_proxy_2_ip"]]:
                    cluster_act_kwargs.exec_ip = proxy_ip
                    cluster_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_set_proxy_backends.__name__
                    acts_list.append(
                        {
                            "act_name": _("proxy配置后端实例"),
                            "act_component_code": ExecuteDBActuatorScriptComponent.code,
                            "kwargs": asdict(cluster_act_kwargs),
                        }
                    )
                cluster_sub_pipeline.add_parallel_acts(acts_list=acts_list)

                cluster_sub_pipeline.add_parallel_acts(
                    acts_list=[
                        {
                            "act_name": _("添加主集群域名"),
                            "act_component_code": MySQLDnsManageComponent.code,
                            "kwargs": asdict(
                                CreateDnsKwargs(
                                    bk_cloud_id=self.data["bk_cloud_id"],
                                    add_domain_name=cluster["master"],
                                    dns_op_exec_port=cluster["proxy_port"],
                                    exec_ip=[cluster["new_proxy_1_ip"], cluster["new_proxy_2_ip"]],
                                )
                            ),
                        },
                        {
                            "act_name": _("添加从集群域名"),
                            "act_component_code": MySQLDnsManageComponent.code,
                            "kwargs": asdict(
                                CreateDnsKwargs(
                                    bk_cloud_id=self.data["bk_cloud_id"],
                                    add_domain_name=cluster["slave"],
                                    dns_op_exec_port=cluster["mysql_port"],
                                    exec_ip=cluster["new_slave_ip"],
                                )
                            ),
                        },
                    ]
                )

                build_cluster_sub_list.append(
                    cluster_sub_pipeline.build_sub_process(sub_name=_("{}集群部署").format(cluster["name"]))
                )

            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=build_cluster_sub_list)

            # 阶段6 拼接db-meta的新ip信息到私有变量cluster,为了兼容机器属于多组cluster的录入场景，clusters信息通过子流程的上下文获取即可
            machine_info = {
                "new_master_ip": info["mysql_ip_list"][0]["ip"],
                "new_slave_ip": info["mysql_ip_list"][1]["ip"],
                "new_proxy_1_ip": info["proxy_ip_list"][0]["ip"],
                "new_proxy_2_ip": info["proxy_ip_list"][1]["ip"],
            }

            sub_pipeline.add_act(
                act_name=_("更新DBMeta元信息"),
                act_component_code=MySQLDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.mysql_ha_apply.__name__,
                        cluster=machine_info,
                        is_update_trans_data=True,
                    )
                ),
            )

            # 阶段7 部署周边组件
            sub_pipeline.add_sub_pipeline(
                sub_flow=build_surrounding_apps_sub_flow(
                    bk_cloud_id=int(self.data["bk_cloud_id"]),
                    master_ip_list=[info["mysql_ip_list"][0]["ip"]],
                    slave_ip_list=[info["mysql_ip_list"][1]["ip"]],
                    proxy_ip_list=[ip_info["ip"] for ip_info in info["proxy_ip_list"]],
                    root_id=self.root_id,
                    parent_global_data=copy.deepcopy(sub_flow_context),
                    is_init=True,
                    cluster_type=ClusterType.TenDBHA.value,
                )
            )

            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("部署MySQL高可用集群")))

        mysql_ha_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        mysql_ha_pipeline.run_pipeline(init_trans_data_class=HaApplyManualContext())
