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

from django.utils.translation import ugettext as _

from backend import env
from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterEntryType, ClusterType, InstanceInnerRole, InstanceStatus
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
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
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta

logger = logging.getLogger("flow")


class MySQLProxyClusterAddFlow(object):
    """
    构建mysql集群添加proxy实例申请流程抽象类
    执行添加proxy 新的proxy机器，必须是不在dbm系统记录上线过
    兼容跨云区域的场景支持
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data

    @staticmethod
    def __get_proxy_instance_info(cluster_id: int, proxy_ip: str) -> dict:
        """
        根据cluster_id 和 proxy_id 获取到待回收实例信息
        @param cluster_id: 集群id
        @param proxy_ip:   待添加的proxy_ip 机器
        """
        cluster = Cluster.objects.get(id=cluster_id)
        # 选择集群标记running状态的proxy实例，作为流程中克隆权限的依据
        template_proxy = ProxyInstance.objects.filter(cluster=cluster, status=InstanceStatus.RUNNING.value).all()[0]
        mysql_ip_list = StorageInstance.objects.filter(cluster=cluster).all()
        master = StorageInstance.objects.get(cluster=cluster, instance_inner_role=InstanceInnerRole.MASTER)
        dns_list = template_proxy.bind_entry.filter(cluster_entry_type=ClusterEntryType.DNS.value).all()

        return {
            "id": cluster_id,
            "bk_cloud_id": cluster.bk_cloud_id,
            "name": cluster.name,
            "cluster_type": cluster.cluster_type,
            "template_proxy_ip": template_proxy.machine.ip,
            # 集群所有的backend实例的端口是一致的，获取第一个对象的端口信息即可
            "mysql_ip_list": [m.machine.ip for m in mysql_ip_list],
            "mysql_port": master.port,
            # 每套集群的proxy端口必须是相同的，取第一个proxy的端口信息即可
            "proxy_port": template_proxy.port,
            "target_proxy_ip": proxy_ip,
            # 新的proxy配置后端ip
            "set_backend_ip": master.machine.ip,
            "add_domain_list": [i.entry for i in dns_list],
            "is_drop": False,
        }

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
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("infos")

            sub_flow_context["proxy_ports"] = self.__get_proxy_install_ports(cluster_ids=info["cluster_ids"])
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

            # 拼接执行原子任务活动节点需要的通用的私有参数结构体, 减少代码重复率，但引用时注意内部参数值传递的问题
            exec_act_kwargs = ExecActuatorKwargs(
                cluster_type=ClusterType.TenDBHA,
                exec_ip=info["proxy_ip"]["ip"],
                bk_cloud_id=info["proxy_ip"]["bk_cloud_id"],
            )

            # 初始化机器
            sub_pipeline.add_act(
                act_name=_("初始化机器"),
                act_component_code=SysInitComponent.code,
                kwargs={
                    "exec_ip": info["proxy_ip"]["ip"],
                    "bk_cloud_id": info["proxy_ip"]["bk_cloud_id"],
                },
            )
            # 判断是否需要执行按照MySQL Perl依赖
            if env.YUM_INSTALL_PERL:
                exec_act_kwargs.exec_ip = info["proxy_ip"]["ip"]
                sub_pipeline.add_act(
                    act_name=_("安装MySQL Perl相关依赖"),
                    act_component_code=MySQLOsInitComponent.code,
                    kwargs=asdict(exec_act_kwargs),
                )

            # 阶段1 已机器维度，安装先上架的proxy实例
            sub_pipeline.add_act(
                act_name=_("下发proxy安装介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=info["proxy_ip"]["bk_cloud_id"],
                        exec_ip=info["proxy_ip"]["ip"],
                        file_list=GetFileList(db_type=DBType.MySQL).mysql_proxy_install_package(),
                    )
                ),
            )

            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_deploy_mysql_crond_payload.__name__
            sub_pipeline.add_act(
                act_name=_("部署mysql-crond"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(exec_act_kwargs),
            )

            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_install_proxy_payload.__name__
            sub_pipeline.add_act(
                act_name=_("部署proxy实例"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(exec_act_kwargs),
            )

            # 阶段2 根据需要添加的proxy的集群，依次添加
            add_proxy_sub_list = []
            for cluster_id in info["cluster_ids"]:

                # 拼接子流程需要全局参数
                sub_sub_flow_context = copy.deepcopy(self.data)
                sub_sub_flow_context.pop("infos")

                # 获取对应的集群信息
                cluster = self.__get_proxy_instance_info(cluster_id=cluster_id, proxy_ip=info["proxy_ip"]["ip"])

                # 针对集群维度声明子流程
                add_proxy_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_sub_flow_context))

                #  拼接添加proxy节点需要的通用的私有参数结构体, 减少代码重复率，但引用时注意内部参数值传递的问题
                add_proxy_sub_act_kwargs = ExecActuatorKwargs(
                    bk_cloud_id=cluster["bk_cloud_id"],
                    cluster=cluster,
                )

                add_proxy_sub_pipeline.add_act(
                    act_name=_("下发db-actuator介质"),
                    act_component_code=TransFileComponent.code,
                    kwargs=asdict(
                        DownloadMediaKwargs(
                            bk_cloud_id=cluster["bk_cloud_id"],
                            exec_ip=[cluster["template_proxy_ip"]] + cluster["mysql_ip_list"],
                            file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                        ),
                    ),
                )

                add_proxy_sub_act_kwargs.exec_ip = cluster["target_proxy_ip"]
                add_proxy_sub_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_set_proxy_backends.__name__
                add_proxy_sub_pipeline.add_act(
                    act_name=_("新的proxy配置后端实例"),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(add_proxy_sub_act_kwargs),
                )

                add_proxy_sub_act_kwargs.exec_ip = cluster["template_proxy_ip"]
                add_proxy_sub_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_clone_proxy_user_payload.__name__
                add_proxy_sub_pipeline.add_act(
                    act_name=_("克隆proxy用户白名单"),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(add_proxy_sub_act_kwargs),
                )

                acts_list = []
                for cluster_mysql_ip in cluster["mysql_ip_list"]:
                    add_proxy_sub_act_kwargs.exec_ip = cluster_mysql_ip
                    add_proxy_sub_act_kwargs.get_mysql_payload_func = (
                        MysqlActPayload.get_clone_client_grant_payload.__name__
                    )
                    acts_list.append(
                        {
                            "act_name": _("集群对新的proxy添加权限"),
                            "act_component_code": ExecuteDBActuatorScriptComponent.code,
                            "kwargs": asdict(add_proxy_sub_act_kwargs),
                        }
                    )
                add_proxy_sub_pipeline.add_parallel_acts(acts_list=acts_list)

                acts_list = []
                for name in cluster["add_domain_list"]:
                    # 这里的添加域名的方式根据目前集群对应proxy dns域名进行循环添加，这样保证某个域名添加异常时其他域名添加成功
                    acts_list.append(
                        {
                            "act_name": _("增加新proxy域名映射"),
                            "act_component_code": MySQLDnsManageComponent.code,
                            "kwargs": asdict(
                                CreateDnsKwargs(
                                    bk_cloud_id=cluster["bk_cloud_id"],
                                    add_domain_name=name,
                                    dns_op_exec_port=cluster["proxy_port"],
                                    exec_ip=cluster["target_proxy_ip"],
                                )
                            ),
                        }
                    )
                add_proxy_sub_pipeline.add_parallel_acts(acts_list=acts_list)

                add_proxy_sub_list.append(
                    add_proxy_sub_pipeline.build_sub_process(sub_name=_("{}集群添加proxy实例").format(cluster["name"]))
                )

            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=add_proxy_sub_list)

            # 拼接db-meta的新ip信息到私有变量cluster, 兼容同一台proxy机器属于不同cluster的录入场景
            sub_pipeline.add_act(
                act_name=_("添加db_meta元信息"),
                act_component_code=MySQLDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.mysql_proxy_add.__name__,
                        cluster=info,
                    )
                ),
            )

            exec_act_kwargs.exec_ip = info["proxy_ip"]["ip"]
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_deploy_mysql_monitor_payload.__name__
            sub_pipeline.add_act(
                act_name=_("Proxy安装mysql-monitor"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(exec_act_kwargs),
            )

            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("添加proxy子流程")))

        mysql_proxy_cluster_add_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        mysql_proxy_cluster_add_pipeline.run_pipeline()
