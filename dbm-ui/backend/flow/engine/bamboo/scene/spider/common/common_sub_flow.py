"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from dataclasses import asdict

from django.utils.crypto import get_random_string
from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterType, InstanceStatus, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster
from backend.flow.consts import AUTH_ADDRESS_DIVIDER, DBA_ROOT_USER, TDBCTL_USER
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.common.delete_cc_service_instance import DelCCServiceInstComponent
from backend.flow.plugins.components.collections.mysql.clear_machine import MySQLClearMachineComponent
from backend.flow.plugins.components.collections.mysql.clone_user import CloneUserComponent
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.spider.add_spider_routing import AddSpiderRoutingComponent
from backend.flow.plugins.components.collections.spider.ctl_drop_routing import CtlDropRoutingComponent
from backend.flow.plugins.components.collections.spider.ctl_switch_to_slave import CtlSwitchToSlaveComponent
from backend.flow.plugins.components.collections.spider.spider_db_meta import SpiderDBMetaComponent
from backend.flow.utils.mysql.mysql_act_dataclass import (
    CreateDnsKwargs,
    DBMetaOPKwargs,
    DelServiceInstKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
    InstanceUserCloneKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.spider.get_spider_incr import get_spider_master_incr
from backend.flow.utils.spider.spider_act_dataclass import (
    AddSpiderRoutingKwargs,
    CtlDropRoutingKwargs,
    CtlSwitchToSlaveKwargs,
)
from backend.flow.utils.spider.spider_db_meta import SpiderDBMeta

"""
定义一些TenDB cluster流程上可能会用到的子流程，以便于减少代码的重复率
"""


def add_spider_slaves_sub_flow(
    cluster: Cluster,
    slave_domain: str,
    add_spider_slaves: list,
    root_id: str,
    parent_global_data: dict,
):
    """
    定义对原有的TenDB cluster集群添加spider slave节点的公共子流程
    提供部分需要单据使用：比如添加从集群、扩容接入层等功能
    @param cluster: 待操作的集群
    @param slave_domain: 带添加spider slave节点所要关联的域名
    @param add_spider_slaves: 待添加的slave机器列表信息
    @param root_id: flow流程的root_id
    @param parent_global_data: 本次子流程的对应上层流程的全局只读上下文
    """
    tdbctl_pass = get_random_string(length=10)

    # 获取到集群对应的spider端口，作为这次的安装
    parent_global_data["spider_ports"] = [cluster.proxyinstance_set.first().port]
    sub_pipeline = SubBuilder(root_id=root_id, data=parent_global_data)

    # 拼接执行原子任务活动节点需要的通用的私有参数结构体, 减少代码重复率，但引用时注意内部参数值传递的问题
    exec_act_kwargs = ExecActuatorKwargs(
        cluster_type=ClusterType.TenDBCluster,
        bk_cloud_id=cluster.bk_cloud_id,
    )

    # 阶段1 下发spider安装介质包
    sub_pipeline.add_act(
        act_name=_("下发spider安装介质"),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(
            DownloadMediaKwargs(
                bk_cloud_id=cluster.bk_cloud_id,
                exec_ip=[ip_info["ip"] for ip_info in add_spider_slaves],
                file_list=GetFileList(db_type=DBType.MySQL).spider_slave_install_package(
                    spider_version=parent_global_data["spider_version"]
                ),
            )
        ),
    )

    # 阶段2 初始化待安装机器
    exec_act_kwargs.exec_ip = [ip_info["ip"] for ip_info in add_spider_slaves]
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_sys_init_payload.__name__
    sub_pipeline.add_act(
        act_name=_("初始化机器"),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
    )

    # 阶段3 安装mysql-crond组件
    exec_act_kwargs.exec_ip = [ip_info["ip"] for ip_info in add_spider_slaves]
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_deploy_mysql_crond_payload.__name__
    sub_pipeline.add_act(
        act_name=_("部署mysql-crond"),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
    )

    # 阶段4 安装spider-slave实例，目前spider-slave机器属于单机单实例部署方式，专属一套集群
    acts_list = []
    for spider_ip in add_spider_slaves:
        exec_act_kwargs.exec_ip = spider_ip["ip"]
        exec_act_kwargs.cluster = {
            "immutable_domain": cluster.immute_domain,
            "auto_incr_value": 1,  # spider slave 对这个值不敏感，所有统一设计为1
        }
        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_install_slave_spider_payload.__name__
        acts_list.append(
            {
                "act_name": _("安装Spider_slave实例"),
                "act_component_code": ExecuteDBActuatorScriptComponent.code,
                "kwargs": asdict(exec_act_kwargs),
            }
        )
    sub_pipeline.add_parallel_acts(acts_list=acts_list)

    # 阶段5 集群的业务账号信息克隆到新的spider实例上, 因为目前spider中控实例无法有克隆权限的操作，只能在这里做
    acts_list = []

    # 这里获取集群内running状态的spider节点作为这次克隆权限的依据
    tmp_spider = cluster.proxyinstance_set.filter(status=InstanceStatus.RUNNING)[0]

    for spider in add_spider_slaves:
        acts_list.append(
            {
                "act_name": _("克隆权限到spider节点[{}]".format(spider["ip"])),
                "act_component_code": CloneUserComponent.code,
                "kwargs": asdict(
                    InstanceUserCloneKwargs(
                        clone_data=[
                            {
                                "source": tmp_spider.ip_port,
                                "target": f"{spider['ip']}{AUTH_ADDRESS_DIVIDER}{tmp_spider.port}",
                                "bk_cloud_id": cluster.bk_cloud_id,
                            },
                        ]
                    )
                ),
            }
        )
    sub_pipeline.add_parallel_acts(acts_list=acts_list)

    # 阶段6 下发actor，并执行spider-slave 路由初始化
    sub_pipeline.add_act(
        act_name=_("添加对应路由关系"),
        act_component_code=AddSpiderRoutingComponent.code,
        kwargs=asdict(
            AddSpiderRoutingKwargs(
                cluster_id=cluster.id,
                add_spiders=add_spider_slaves,
                add_spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE.value,
                user=TDBCTL_USER,
                passwd=tdbctl_pass,
            )
        ),
    )

    # 阶段7 添加从域名
    sub_pipeline.add_act(
        act_name=_("添加集群域名"),
        act_component_code=MySQLDnsManageComponent.code,
        kwargs=asdict(
            CreateDnsKwargs(
                bk_cloud_id=cluster.bk_cloud_id,
                add_domain_name=slave_domain,
                dns_op_exec_port=tmp_spider.port,
                exec_ip=[ip_info["ip"] for ip_info in add_spider_slaves],
            )
        ),
    )

    return sub_pipeline.build_sub_process(sub_name=_("集群[{}]添加spider slave节点".format(cluster.name)))


def add_spider_masters_sub_flow(
    cluster: Cluster,
    add_spider_masters: list,
    root_id: str,
    parent_global_data: dict,
    is_add_spider_mnt: bool,
):
    """
    定义对原有的TenDB cluster集群添加spider master节点的公共子流程
    与添加spider slave不同的是：添加spider master实例的同时需要安装中控实例，且spider计算合适的自增列初始值
    提供部分需要单据使用：比如扩容接入层等功能
    @param cluster: 待关联的集群
    @param add_spider_masters: 待添加的slave机器列表信息
    @param root_id: flow流程的root_id
    @param parent_global_data: 本次子流程的对应上层流程的全局只读上下文
    @param is_add_spider_mnt: 表示这次添加spider 运维节点，如果是则True，不是则False
    """
    tdbctl_pass = get_random_string(length=10)

    # 获取到集群对应的spider端口，作为这次的安装
    parent_global_data["spider_ports"] = [cluster.proxyinstance_set.first().port]
    sub_pipeline = SubBuilder(root_id=root_id, data=parent_global_data)

    # 拼接执行原子任务活动节点需要的通用的私有参数结构体, 减少代码重复率，但引用时注意内部参数值传递的问题
    exec_act_kwargs = ExecActuatorKwargs(
        cluster_type=ClusterType.TenDBCluster,
        bk_cloud_id=cluster.bk_cloud_id,
    )

    # 阶段1 下发spider安装介质包
    sub_pipeline.add_act(
        act_name=_("下发spider安装介质"),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(
            DownloadMediaKwargs(
                bk_cloud_id=cluster.bk_cloud_id,
                exec_ip=[ip_info["ip"] for ip_info in add_spider_masters],
                file_list=GetFileList(db_type=DBType.MySQL).spider_slave_install_package(
                    spider_version=parent_global_data["spider_version"]
                ),
            )
        ),
    )

    # 阶段2 初始化待安装机器
    exec_act_kwargs.exec_ip = [ip_info["ip"] for ip_info in add_spider_masters]
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_sys_init_payload.__name__

    sub_pipeline.add_act(
        act_name=_("初始化机器"),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
    )

    # 阶段3 安装mysql-crond组件
    exec_act_kwargs.exec_ip = [ip_info["ip"] for ip_info in add_spider_masters]
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_deploy_mysql_crond_payload.__name__
    sub_pipeline.add_act(
        act_name=_("部署mysql-crond"),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
    )

    # 阶段4 安装spider-master实例，目前spider-master机器属于单机单实例部署方式，专属一套集群
    acts_list = []
    for spider in get_spider_master_incr(cluster, add_spider_masters):
        exec_act_kwargs.exec_ip = spider["ip"]
        exec_act_kwargs.cluster = {
            "immutable_domain": cluster.immute_domain,
            "auto_incr_value": spider["incr_number"],
        }
        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_install_spider_payload.__name__
        acts_list.append(
            {
                "act_name": _("安装Spider实例"),
                "act_component_code": ExecuteDBActuatorScriptComponent.code,
                "kwargs": asdict(exec_act_kwargs),
            }
        )
    sub_pipeline.add_parallel_acts(acts_list=acts_list)

    # 判断添加的角色来是否安装中控实例，spider-mnt不需要安装
    if not is_add_spider_mnt:
        for ctl_ip in add_spider_masters:
            exec_act_kwargs.exec_ip = ctl_ip["ip"]
            exec_act_kwargs.cluster = {"immutable_domain": cluster.immute_domain}
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_install_spider_ctl_payload.__name__
            acts_list.append(
                {
                    "act_name": _("安装Spider集群中控实例"),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(exec_act_kwargs),
                }
            )
        sub_pipeline.add_parallel_acts(acts_list=acts_list)

    # 阶段6 集群的业务账号信息克隆到新的spider实例上, 因为目前spider中控实例无法有克隆权限的操作，只能在这里做
    acts_list = []

    # 这里获取集群内running状态的spider节点作为这次克隆权限的依据
    # todo 这里目前spider节点克隆权限API接口出现异常，需要调整
    tmp_spider = cluster.proxyinstance_set.filter(status=InstanceStatus.RUNNING)[0]

    for spider in add_spider_masters:
        acts_list.append(
            {
                "act_name": _("克隆权限到spider节点[{}]".format(spider["ip"])),
                "act_component_code": CloneUserComponent.code,
                "kwargs": asdict(
                    InstanceUserCloneKwargs(
                        clone_data=[
                            {
                                "source": tmp_spider.ip_port,
                                "target": f"{spider['ip']}{AUTH_ADDRESS_DIVIDER}{tmp_spider.port}",
                                "bk_cloud_id": cluster.bk_cloud_id,
                            },
                        ]
                    )
                ),
            }
        )
    sub_pipeline.add_parallel_acts(acts_list=acts_list)

    # 阶段7 执行spider-master 路由初始化, 内置账号密码随机生成，不需要平台来维护，避免误操作影响
    if is_add_spider_mnt:
        role = TenDBClusterSpiderRole.SPIDER_MNT.value
    else:
        role = TenDBClusterSpiderRole.SPIDER_MASTER.value
    sub_pipeline.add_act(
        act_name=_("添加对应路由关系"),
        act_component_code=AddSpiderRoutingComponent.code,
        kwargs=asdict(
            AddSpiderRoutingKwargs(
                cluster_id=cluster.id,
                add_spiders=add_spider_masters,
                add_spider_role=role,
                user=TDBCTL_USER,
                passwd=tdbctl_pass,
            )
        ),
    )

    if not is_add_spider_mnt:
        # 阶段8 待添加中控实例建立主从数据同步关系
        sub_pipeline.add_sub_pipeline(
            sub_flow=add_ctl_node_with_gtid(
                root_id=root_id,
                parent_global_data=parent_global_data,
                cluster=cluster,
                add_tdbctls=add_spider_masters,
            )
        )
        # 阶段8 添加域名映射关系
        sub_pipeline.add_act(
            act_name=_("添加集群域名"),
            act_component_code=MySQLDnsManageComponent.code,
            kwargs=asdict(
                CreateDnsKwargs(
                    bk_cloud_id=cluster.bk_cloud_id,
                    add_domain_name=cluster.immute_domain,
                    dns_op_exec_port=tmp_spider.port,
                    exec_ip=[ip_info["ip"] for ip_info in add_spider_masters],
                )
            ),
        )

    return sub_pipeline.build_sub_process(sub_name=_("集群[{}]添加spider master节点".format(cluster.name)))


def build_apps_for_spider_sub_flow(
    bk_cloud_id: int,
    spiders: list,
    root_id: str,
    parent_global_data: dict,
    spider_role: TenDBClusterSpiderRole,
):
    """
    定义为spider机器部署周边组件的子流程
    todo 目前spider安装备份有异常，需要调整后再做联调
    @param bk_cloud_id: 操作所属的云区域
    @param spiders: 需要操作的spider机器列表信息
    @param root_id: 整体flow流程的root_id
    @param parent_global_data: 子流程的需要全局只读上下文
    @param spider_role: 这批spider的角色
    """
    sub_pipeline = SubBuilder(root_id=root_id, data=parent_global_data)

    sub_pipeline.add_act(
        act_name=_("下发MySQL周边程序介质"),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(
            DownloadMediaKwargs(
                bk_cloud_id=bk_cloud_id,
                exec_ip=list(filter(None, list(set(spiders)))),
                file_list=GetFileList(db_type=DBType.MySQL).get_spider_apps_package(),
            )
        ),
    )

    acts_list = []
    if isinstance(spiders, list) and len(spiders) != 0:
        for spider_ip in list(set(spiders)):
            acts_list.append(
                {
                    "act_name": _("spider[{}]安装DBATools工具箱".format(spider_ip)),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(
                        ExecActuatorKwargs(
                            bk_cloud_id=bk_cloud_id,
                            exec_ip=spider_ip,
                            get_mysql_payload_func=MysqlActPayload.get_install_dba_toolkit_payload.__name__,
                            cluster_type=ClusterType.TenDBCluster.value,
                            run_as_system_user=DBA_ROOT_USER,
                        )
                    ),
                }
            )

            acts_list.append(
                {
                    "act_name": _("spider[{}]安装mysql-monitor".format(spider_ip)),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(
                        ExecActuatorKwargs(
                            bk_cloud_id=bk_cloud_id,
                            exec_ip=spider_ip,
                            get_mysql_payload_func=MysqlActPayload.get_deploy_mysql_monitor_payload.__name__,
                            cluster_type=ClusterType.TenDBCluster.value,
                            run_as_system_user=DBA_ROOT_USER,
                        )
                    ),
                },
            )
            # 因为同一台机器的只有会有一个spider实例，所以直接根据ip、bk_cloud_id获取对应实例的spider角色，来判断是否安装备份程序
            if spider_role == TenDBClusterSpiderRole.SPIDER_MASTER:
                acts_list.append(
                    {
                        "act_name": _("spider[{}]安装备份程序".format(spider_ip)),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(
                            ExecActuatorKwargs(
                                bk_cloud_id=bk_cloud_id,
                                exec_ip=spider_ip,
                                get_mysql_payload_func=MysqlActPayload.get_install_db_backup_payload.__name__,
                                cluster_type=ClusterType.TenDBCluster.value,
                                run_as_system_user=DBA_ROOT_USER,
                            )
                        ),
                    },
                )
    sub_pipeline.add_parallel_acts(acts_list=acts_list)
    return sub_pipeline.build_sub_process(sub_name=_("安装Spider周边程序"))


def add_ctl_node_with_gtid(
    root_id: str,
    parent_global_data: dict,
    cluster: Cluster,
    add_tdbctls: list,
):
    """
    添加新的定义ctl建立基于gtid的主从同步
    """
    ctl_master = cluster.tendbcluster_ctl_primary_address()
    extend = {
        "mysql_port": ctl_master.split(":")[1],
        "master_ip": ctl_master.split(":")[0],
        "slaves": [ip_info["ip"] for ip_info in add_tdbctls],
    }

    sub_pipeline = SubBuilder(root_id=root_id, data=parent_global_data)
    sub_pipeline.add_act(
        act_name=_("新增repl帐户"),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(
            ExecActuatorKwargs(
                bk_cloud_id=cluster.bk_cloud_id,
                exec_ip=ctl_master.split(":")[0],
                get_mysql_payload_func=MysqlActPayload.get_grant_repl_for_ctl_payload.__name__,
                cluster=extend,
            )
        ),
    )
    acts_list = []
    for tdbctl in add_tdbctls:
        acts_list.append(
            {
                "act_name": _("建立主从关系"),
                "act_component_code": ExecuteDBActuatorScriptComponent.code,
                "kwargs": asdict(
                    ExecActuatorKwargs(
                        bk_cloud_id=cluster.bk_cloud_id,
                        exec_ip=tdbctl["ip"],
                        get_mysql_payload_func=MysqlActPayload.get_change_master_for_gitd_payload.__name__,
                        cluster=extend,
                    )
                ),
            }
        )

    sub_pipeline.add_parallel_acts(acts_list=acts_list)
    return sub_pipeline.build_sub_process(sub_name=_("部署spider-ctl集群"))


def reduce_spider_slaves_flow(
    cluster: Cluster,
    reduce_spiders: list,
    root_id: str,
    parent_global_data: dict,
    spider_role: TenDBClusterSpiderRole,
):
    """
    减少spider节点的子流程, 提供给集群缩容接入层或者替换类单据所用
    @param cluster: 待操作的集群
    @param reduce_spiders: 待卸载的spider节点机器信息
    @param root_id: flow流程的root_id
    @param parent_global_data: 本次子流程的对应上层流程的全局只读上下文
    @param spider_role: 本次操作的spider角色
    """

    sub_pipeline = SubBuilder(root_id=root_id, data=parent_global_data)

    # 拼接执行原子任务活动节点需要的通用的私有参数结构体, 减少代码重复率，但引用时注意内部参数值传递的问题
    exec_act_kwargs = ExecActuatorKwargs(
        cluster_type=ClusterType.TenDBCluster,
        bk_cloud_id=cluster.bk_cloud_id,
    )

    # 获取集群对应的spider端口
    spider_port = cluster.proxyinstance_set.first().port
    spider_admin_port = cluster.proxyinstance_set.first().admin_port

    # 先回收集群所有服务实例内容，避免出现误报监控
    del_instance_list = []
    for spider in reduce_spiders:
        del_instance_list.append({"ip": spider["ip"], "port": spider_port})

    sub_pipeline.add_act(
        act_name=_("删除注册CC系统的服务实例"),
        act_component_code=DelCCServiceInstComponent.code,
        kwargs=asdict(
            DelServiceInstKwargs(
                cluster_id=cluster.id,
                del_instance_list=del_instance_list,
            )
        ),
    )

    # 阶段1 下发spider安装介质包
    sub_pipeline.add_act(
        act_name=_("下发db-actuator介质"),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(
            DownloadMediaKwargs(
                bk_cloud_id=cluster.bk_cloud_id,
                exec_ip=[ip_info["ip"] for ip_info in reduce_spiders],
                file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
            )
        ),
    )

    # 阶段2 卸载相关db组件
    acts_list = []
    for spider in reduce_spiders:
        exec_act_kwargs.exec_ip = spider["ip"]
        exec_act_kwargs.cluster = {"spider_port": spider_port}
        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_uninstall_spider_payload.__name__
        acts_list.append(
            {
                "act_name": _("卸载spider实例"),
                "act_component_code": ExecuteDBActuatorScriptComponent.code,
                "kwargs": asdict(exec_act_kwargs),
            }
        )
    sub_pipeline.add_parallel_acts(acts_list=acts_list)

    # 阶段3 如果这次卸载的是spider-master，需要卸载对应的中控实例
    if spider_role == TenDBClusterSpiderRole.SPIDER_MASTER.value:

        # 回收对应ctl的路由信息，如果涉及到ctl primary，先切换，再回收
        reduce_ctls = cluster.proxyinstance_set.filter(machine__ip__in=[ip_info["ip"] for ip_info in reduce_spiders])
        sub_pipeline.add_sub_pipeline(
            sub_flow=reduce_ctls_routing(
                root_id=root_id, parent_global_data=parent_global_data, cluster=cluster, reduce_ctls=list(reduce_ctls)
            )
        )

        # 卸载ctl的进程
        acts_list = []
        for ctl in reduce_spiders:
            exec_act_kwargs.exec_ip = ctl["ip"]
            exec_act_kwargs.cluster = {"spider_ctl_port": spider_admin_port}
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_uninstall_spider_ctl_payload.__name__
            acts_list.append(
                {
                    "act_name": _("卸载中控实例"),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(exec_act_kwargs),
                }
            )
        sub_pipeline.add_parallel_acts(acts_list=acts_list)

    # 阶段4 清空相关集群元信息；相关的cmdb注册信息
    sub_pipeline.add_act(
        act_name=_("清理db_meta元信息"),
        act_component_code=SpiderDBMetaComponent.code,
        kwargs=asdict(
            DBMetaOPKwargs(
                db_meta_class_func=SpiderDBMeta.reduce_spider_nodes_apply.__name__,
            )
        ),
    )

    # 阶段5 清理机器配置，这里不需要做实例级别的配置清理，因为目前平台spider的单机单实例部署，专属一套集群
    exec_act_kwargs.exec_ip = [ip_info["ip"] for ip_info in reduce_spiders]
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_clear_machine_crontab.__name__
    sub_pipeline.add_act(
        act_name=_("清理机器周边配置"),
        act_component_code=MySQLClearMachineComponent.code,
        kwargs=asdict(exec_act_kwargs),
    )

    return sub_pipeline.build_sub_process(sub_name=_("下架spider节点"))


def reduce_ctls_routing(root_id: str, parent_global_data: dict, cluster: Cluster, reduce_ctls: list):
    """
    根据回收spider-ctl，构建专属的中控实例路由删除的子流程
    """
    reduce_ctl_primary = None
    reduce_ctl_secondary_list = []

    # 计算每个待回收的ctl的角色，分配下架行为
    for ctl in reduce_ctls:
        if f"{ctl.machine.ip}{IP_PORT_DIVIDER}{ctl.admin_port}" == cluster.tendbcluster_ctl_primary_address():
            # 本次回收事件涉及到ctl主节点回收，则加入这次回收流程
            reduce_ctl_primary = f"{ctl.machine.ip}{IP_PORT_DIVIDER}{ctl.admin_port}"
        else:
            reduce_ctl_secondary_list.append(f"{ctl.machine.ip}{IP_PORT_DIVIDER}{ctl.admin_port}")

    sub_pipeline = SubBuilder(root_id=root_id, data=parent_global_data)

    if reduce_ctl_primary:
        # 选择新节点作为primary，过滤待回收的节点
        all_ctl = cluster.proxyinstance_set.filter(
            tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER
        )

        # 因为ctl集群是采用GTID+半同步数据同步，所以理论上选择任意一个从节点作为主，数据不会丢失
        new_ctl_primary = all_ctl.exclude(machine__ip__in=[ip_info["ip"] for ip_info in reduce_ctls]).first()

        sub_pipeline.add_act(
            act_name=_("切换ctl中控集群"),
            act_component_code=CtlSwitchToSlaveComponent.code,
            kwargs=asdict(
                CtlSwitchToSlaveKwargs(
                    cluster_id=cluster.id,
                    reduce_ctl_primary=reduce_ctl_primary,
                    new_ctl_primary=f"{new_ctl_primary.machine.ip}{IP_PORT_DIVIDER}{new_ctl_primary.admin_port}",
                )
            ),
        )

    acts_list = []
    for ctl in reduce_ctl_secondary_list:
        acts_list.append(
            {
                "act_name": _("卸载中控实例路由[{}]".format(ctl)),
                "act_component_code": CtlDropRoutingComponent.code,
                "kwargs": asdict(
                    CtlDropRoutingKwargs(
                        cluster_id=cluster.id,
                        reduce_ctl=ctl,
                    )
                ),
            }
        )
    sub_pipeline.add_parallel_acts(acts_list=acts_list)

    return sub_pipeline.build_sub_process(sub_name=_("删除中控的路由节点"))
