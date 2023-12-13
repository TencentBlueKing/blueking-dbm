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

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterEntryType, ClusterType, InstanceInnerRole, InstanceStatus
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.common.common_sub_flow import init_machine_sub_flow
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mysql.clear_machine import MySQLClearMachineComponent
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import (
    CreateDnsKwargs,
    DBMetaOPKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
    RecycleDnsRecordKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta

logger = logging.getLogger("flow")


class MySQLProxyClusterSwitchFlow(object):
    """
    构建mysql集群替换proxy实例申请流程抽象类
    替换proxy 是属于整机替换，新的机器必须不在dbm系统记录上线过
    兼容跨云区域的场景支持
    todo 后续需要优化实例下架逻辑，避免误报
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data

    @staticmethod
    def __get_switch_cluster_info(cluster_id: int, origin_proxy_ip: str, target_proxy_ip: str) -> dict:
        """
        根据cluster_id 和 proxy_id 获取到集群以及新proxy实例信息
        @param cluster_id: 集群id
        @param origin_proxy_ip:   待替换的proxy_ip机器
        @param target_proxy_ip:   新的proxy_ip机器
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
            "origin_proxy_ip": origin_proxy_ip,
            "target_proxy_ip": target_proxy_ip,
            # 新的proxy配置后端ip
            "set_backend_ip": master.machine.ip,
            "add_domain_list": [i.entry for i in dns_list],
            "is_drop": True,
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

    def switch_mysql_cluster_proxy_flow(self):
        """
        定义mysql集群proxy替换实例流程
        增加单据临时ADMIN账号的添加和删除逻辑
        """
        cluster_ids = []
        for i in self.data["infos"]:
            cluster_ids.extend(i["cluster_ids"])

        mysql_proxy_cluster_add_pipeline = Builder(
            root_id=self.root_id, data=self.data, need_random_pass_cluster_ids=list(set(cluster_ids))
        )
        sub_pipelines = []

        # 多集群操作时循环加入集群proxy替换子流程
        for info in self.data["infos"]:
            # 拼接子流程需要全局参数
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("infos")

            sub_flow_context["proxy_ports"] = self.__get_proxy_install_ports(cluster_ids=info["cluster_ids"])
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

            # 拼接执行原子任务活动节点需要的通用的私有参数结构体, 减少代码重复率，但引用时注意内部参数值传递的问题
            exec_act_kwargs = ExecActuatorKwargs(
                cluster_type=ClusterType.TenDBHA,
                exec_ip=info["target_proxy_ip"]["ip"],
                bk_cloud_id=info["target_proxy_ip"]["bk_cloud_id"],
            )

            # 初始新机器
            sub_pipeline.add_sub_pipeline(
                sub_flow=init_machine_sub_flow(
                    uid=sub_flow_context["uid"],
                    root_id=self.root_id,
                    bk_cloud_id=int(info["target_proxy_ip"]["bk_cloud_id"]),
                    sys_init_ips=[info["target_proxy_ip"]["ip"]],
                    init_check_ips=[info["target_proxy_ip"]["ip"]],
                    yum_install_perl_ips=[info["target_proxy_ip"]["ip"]],
                )
            )

            # 阶段1 已机器维度，安装先上架的proxy实例
            sub_pipeline.add_act(
                act_name=_("下发proxy安装介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=info["target_proxy_ip"]["bk_cloud_id"],
                        exec_ip=info["target_proxy_ip"]["ip"],
                        file_list=GetFileList(db_type=DBType.MySQL).mysql_proxy_install_package(),
                    )
                ),
            )

            # 阶段2 部署mysql-crond
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
            # 后续流程需要在这里加一个暂停节点，让用户在合适的时间执行切换
            sub_pipeline.add_act(act_name=_("人工确认"), act_component_code=PauseComponent.code, kwargs={})

            # 阶段2 根据需要替换的proxy的集群，依次添加
            switch_proxy_sub_list = []
            for cluster_id in info["cluster_ids"]:

                # 拼接子流程需要全局参数
                sub_sub_flow_context = copy.deepcopy(self.data)
                sub_sub_flow_context.pop("infos")

                # 获取集群的实例信息
                cluster = self.__get_switch_cluster_info(
                    cluster_id=cluster_id,
                    target_proxy_ip=info["target_proxy_ip"]["ip"],
                    origin_proxy_ip=info["origin_proxy_ip"]["ip"],
                )

                # 针对集群维度声明替换子流程
                switch_proxy_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_sub_flow_context))

                #  拼接替换proxy节点需要的通用的私有参数结构体, 减少代码重复率，但引用时注意内部参数值传递的问题
                switch_proxy_sub_act_kwargs = ExecActuatorKwargs(
                    bk_cloud_id=cluster["bk_cloud_id"],
                    cluster=cluster,
                )

                switch_proxy_sub_pipeline.add_act(
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

                switch_proxy_sub_act_kwargs.exec_ip = cluster["target_proxy_ip"]
                switch_proxy_sub_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_set_proxy_backends.__name__
                switch_proxy_sub_pipeline.add_act(
                    act_name=_("新的proxy配置后端实例"),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(switch_proxy_sub_act_kwargs),
                )

                switch_proxy_sub_act_kwargs.exec_ip = cluster["template_proxy_ip"]
                switch_proxy_sub_act_kwargs.get_mysql_payload_func = (
                    MysqlActPayload.get_clone_proxy_user_payload.__name__
                )
                switch_proxy_sub_pipeline.add_act(
                    act_name=_("克隆proxy用户白名单"),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(switch_proxy_sub_act_kwargs),
                )

                acts_list = []
                for cluster_mysql_ip in cluster["mysql_ip_list"]:
                    switch_proxy_sub_act_kwargs.exec_ip = cluster_mysql_ip
                    switch_proxy_sub_act_kwargs.get_mysql_payload_func = (
                        MysqlActPayload.get_clone_client_grant_payload.__name__
                    )
                    acts_list.append(
                        {
                            "act_name": _("集群对新的proxy添加权限"),
                            "act_component_code": ExecuteDBActuatorScriptComponent.code,
                            "kwargs": asdict(switch_proxy_sub_act_kwargs),
                        }
                    )
                switch_proxy_sub_pipeline.add_parallel_acts(acts_list=acts_list)

                acts_list = []
                for dns_name in cluster["add_domain_list"]:
                    # 这里的添加域名的方式根据目前集群对应proxy dns域名进行循环添加，这样保证某个域名添加异常时其他域名添加成功
                    acts_list.append(
                        {
                            "act_name": _("增加新proxy域名映射"),
                            "act_component_code": MySQLDnsManageComponent.code,
                            "kwargs": asdict(
                                CreateDnsKwargs(
                                    bk_cloud_id=cluster["bk_cloud_id"],
                                    add_domain_name=dns_name,
                                    dns_op_exec_port=cluster["proxy_port"],
                                    exec_ip=cluster["target_proxy_ip"],
                                )
                            ),
                        }
                    )
                switch_proxy_sub_pipeline.add_parallel_acts(acts_list=acts_list)

                switch_proxy_sub_list.append(
                    switch_proxy_sub_pipeline.build_sub_process(sub_name=_("{}集群替换proxy实例").format(cluster["name"]))
                )

            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=switch_proxy_sub_list)

            # 阶段3 后续流程需要在这里加一个暂停节点，让用户在合适的时间执行下架旧实例操作
            sub_pipeline.add_act(act_name=_("人工确认"), act_component_code=PauseComponent.code, kwargs={})

            # 阶段4 机器维度，下架旧机器节点
            reduce_proxy_sub_list = []
            for cluster_id in info["cluster_ids"]:
                cluster = Cluster.objects.get(id=cluster_id)
                reduce_proxy_sub_list.append(
                    self.proxy_reduce_sub_flow(
                        bk_cloud_id=cluster.bk_cloud_id,
                        origin_proxy_ip=info["origin_proxy_ip"]["ip"],
                        origin_proxy_port=ProxyInstance.objects.filter(cluster=cluster).all()[0].port,
                    )
                )
            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=reduce_proxy_sub_list)

            # 阶段5 按照机器维度变更db-meta数据
            sub_pipeline.add_act(
                act_name=_("变更db_meta元信息"),
                act_component_code=MySQLDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.mysql_proxy_switch.__name__,
                        cluster=info,
                    )
                ),
            )

            # 阶段6 新的proxy添加事件监控
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_deploy_mysql_monitor_payload.__name__
            sub_pipeline.add_act(
                act_name=_("Proxy安装mysql-monitor"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(exec_act_kwargs),
            )

            # 阶段7 清理机器级别的配置
            exec_act_kwargs.exec_ip = info["origin_proxy_ip"]["ip"]
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_clear_machine_crontab.__name__
            sub_pipeline.add_act(
                act_name=_("清理机器配置"),
                act_component_code=MySQLClearMachineComponent.code,
                kwargs=asdict(exec_act_kwargs),
            )

            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("替换proxy子流程")))

        mysql_proxy_cluster_add_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        mysql_proxy_cluster_add_pipeline.run_pipeline(is_drop_random_user=True)

    def proxy_reduce_sub_flow(self, bk_cloud_id: int, origin_proxy_ip: str, origin_proxy_port: int):
        """
        回收proxy实例的子流程
        支持proxy多实例回收场景
        支持跨云操作
        @param bk_cloud_id: 集群所在的云区域
        @param origin_proxy_ip: 回收proxy ip 信息
        @param origin_proxy_port: 回收proxy ip 信息
        """

        # 拼接子流程需要全局参数
        flow_context = copy.deepcopy(self.data)
        flow_context.pop("infos")

        #  拼接替换proxy节点需要的通用的私有参数结构体, 减少代码重复率，但引用时注意内部参数值传递的问题
        reduce_proxy_sub_act_kwargs = ExecActuatorKwargs(
            bk_cloud_id=bk_cloud_id, exec_ip=origin_proxy_ip, cluster={"proxy_port": origin_proxy_port}
        )

        # 针对集群维度声明替换子流程
        sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(flow_context))

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
        )

        reduce_proxy_sub_act_kwargs.get_mysql_payload_func = (
            MysqlActPayload.get_clear_surrounding_config_payload.__name__
        )
        sub_pipeline.add_act(
            act_name=_("清理proxy实例级别周边配置"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(reduce_proxy_sub_act_kwargs),
        )

        reduce_proxy_sub_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_uninstall_proxy_payload.__name__
        sub_pipeline.add_act(
            act_name=_("卸载proxy实例"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(reduce_proxy_sub_act_kwargs),
        )

        sub_pipeline.add_act(
            act_name=_("回收对应proxy集群映射"),
            act_component_code=MySQLDnsManageComponent.code,
            kwargs=asdict(
                RecycleDnsRecordKwargs(
                    bk_cloud_id=bk_cloud_id,
                    dns_op_exec_port=origin_proxy_port,
                    exec_ip=origin_proxy_ip,
                ),
            ),
        )

        return sub_pipeline.build_sub_process(sub_name=_("[{}:{}]下线").format(origin_proxy_ip, origin_proxy_port))
