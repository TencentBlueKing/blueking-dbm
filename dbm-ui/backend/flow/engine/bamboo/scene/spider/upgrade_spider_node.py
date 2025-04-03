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
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterEntryRole, ClusterType, InstanceStatus, TenDBClusterSpiderRole
from backend.db_meta.enums.instance_phase import InstancePhase
from backend.db_meta.exceptions import ClusterNotExistException, DBMetaException
from backend.db_meta.models import Cluster, ProxyInstance
from backend.db_package.models import Package
from backend.flow.consts import DnsOpType, MediumEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.entrys_manager import BuildEntrysManageSubflow
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.spider.spider_add_nodes import TenDBClusterAddNodesFlow
from backend.flow.plugins.components.collections.common.delete_cc_service_instance import DelCCServiceInstComponent
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mysql.check_client_connections import CheckClientConnComponent
from backend.flow.plugins.components.collections.mysql.clear_machine import MySQLClearMachineComponent
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.spider.ctl_drop_routing import CtlDropRoutingComponent
from backend.flow.plugins.components.collections.spider.ctl_switch_to_slave import CtlSwitchToSlaveComponent
from backend.flow.plugins.components.collections.spider.drop_spider_ronting import DropSpiderRoutingComponent
from backend.flow.plugins.components.collections.spider.spider_db_meta import SpiderDBMetaComponent
from backend.flow.utils.mysql.mysql_act_dataclass import (
    CheckClientConnKwargs,
    CreateDnsKwargs,
    DBMetaOPKwargs,
    DelServiceInstKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
    RecycleDnsRecordKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta
from backend.flow.utils.mysql.mysql_version_parse import (
    get_spider_sub_version_by_pkg_name,
    proxy_version_parse,
    tspider_version_parse,
)
from backend.flow.utils.spider.spider_act_dataclass import (
    CtlDropRoutingKwargs,
    CtlSwitchToSlaveKwargs,
    DropSpiderRoutingKwargs,
)
from backend.flow.utils.spider.spider_bk_config import get_spider_version_and_charset
from backend.flow.utils.spider.spider_db_meta import SpiderDBMeta

logger = logging.getLogger("flow")


class UpgradeSpiderFlow(TenDBClusterAddNodesFlow):
    """
    TendbCluster spider节点迁移
        {
            "upgrade_local": True,
            "infos": [
                {
                    "cluster_id": 1,
                    "pkg_id": 123,
                    "new_db_moudule_id": 3334,
                    "spider_master_ip_list": [],
                    "spider_slave_ip_list": []
                }
            ]
        }
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param ticket_data : 单据传递参数
        """
        self.root_id = root_id
        self.uid = data["uid"]
        self.bk_biz_id = data["bk_biz_id"]
        self.force_upgrade = data.get("force", False)
        self.data = data
        self.upgrade_local = data.get("upgrade_local", False)
        self.cluster_ids = list(set([i["cluster_id"] for i in self.data["infos"]]))

    def run(self):
        self.__pre_check()
        if self.upgrade_local:
            self.local_upgrade()
        else:
            self.migrate_upgrade()

    # spider_ins.tendbclusterspiderext.spider_role
    def __pre_check(self):
        """_summary_
        检查升级版本和源版本
        """
        for info in self.data["infos"]:
            pkg_id = info["pkg_id"]
            cluster_id = info["cluster_id"]
            spider_pkg = Package.objects.get(id=pkg_id, pkg_type=MediumEnum.Spider)
            new_spider_version_num = tspider_version_parse(spider_pkg.name)
            cluster = Cluster.objects.get(id=cluster_id)
            spiders = ProxyInstance.objects.filter(cluster=cluster)
            # 元数据版本检查
            for spider_ins in spiders:
                current_version = proxy_version_parse(spider_ins.version)
                if current_version >= new_spider_version_num:
                    logger.error(
                        "the upgrade version {} needs to be larger than the current verion {}".format(
                            new_spider_version_num, current_version
                        )
                    )
                    raise DBMetaException(message=_("待升级版本大于等于新版本，请确认升级的版本"))
            if not self.local_upgrade:
                spider_master_ip_list = info["spider_master_ip_list"]
                spider_slave_ip_list = info.get("spider_slave_ip_list", [])
                master_spiders_count = cluster.proxyinstance_set.filter(
                    tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER
                ).count()
                if master_spiders_count != len(spider_master_ip_list):
                    raise DBMetaException(message=_("待升级spiderMaster节点数传入ip节点数不一致,请确认"))
                slave_spiders_count = cluster.proxyinstance_set.filter(
                    tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE
                ).count()
                if slave_spiders_count > 0 and len(spider_slave_ip_list) < 0:
                    raise DBMetaException(message=_("待升级spiderSlave节点数传入ip节点数不一致,请确认"))

    def migrate_upgrade(self):
        """执行替换spider节点的flow"""
        pipeline = Builder(root_id=self.root_id, data=self.data, need_random_pass_cluster_ids=self.cluster_ids)
        sub_pipelines = []
        for info in self.data["infos"]:
            cluster_id = info["cluster_id"]
            pkg_id = info["pkg_id"]
            spider_master_ip_list = info["spider_master_ip_list"]
            spider_slave_ip_list = info.get("spider_slave_ip_list", [])
            new_db_module_id = info["new_db_module_id"]
            # 拼接子流程需要全局参数
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("infos")
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))
            # 获取对应集群相关对象
            try:
                cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=int(self.data["bk_biz_id"]))
            except Cluster.DoesNotExist:
                raise ClusterNotExistException(
                    cluster_id=cluster_id, bk_biz_id=int(self.data["bk_biz_id"]), message=_("集群不存在")
                )
            add_spider_piplines = []
            # 先扩容spider节点
            spider_charset, spider_version = get_spider_version_and_charset(
                bk_biz_id=cluster.bk_biz_id, db_module_id=new_db_module_id
            )
            sub_flow_context.update(info)
            sub_flow_context["spider_version"] = spider_version
            sub_flow_context["spider_charset"] = spider_charset
            sub_flow_context["spider_ip_list"] = spider_master_ip_list
            sub_flow_context["pkg_id"] = pkg_id
            sub_flow_context["ctl_charset"] = spider_charset
            add_spider_piplines.append(self.add_spider_master_notes(sub_flow_context, cluster))
            if len(spider_slave_ip_list) > 0:
                sub_flow_context["spider_ip_list"] = spider_slave_ip_list
                add_spider_piplines.append(self.add_spider_slave_notes(sub_flow_context, cluster))
            sub_pipeline.add_parallel_sub_pipeline(add_spider_piplines)
            # 先切换主中控到新的spider master 上
            new_priamry_ctl_ip = spider_master_ip_list[0]["ip"]
            ctl_port = cluster.proxyinstance_set.first().admin_port
            sub_pipeline.add_act(
                act_name=_("切换primary中控"),
                act_component_code=CtlSwitchToSlaveComponent.code,
                kwargs=asdict(
                    CtlSwitchToSlaveKwargs(
                        cluster_id=cluster.id,
                        reduce_ctl_primary=cluster.tendbcluster_ctl_primary_address(),
                        new_ctl_primary=f"{new_priamry_ctl_ip}{IP_PORT_DIVIDER}{ctl_port}",
                    )
                ),
            )
            # 后续流程需要在这里加一个暂停节点，让用户在合适的时间执行下架
            sub_pipeline.add_act(act_name=_("人工确认"), act_component_code=PauseComponent.code, kwargs={})
            # 预检测
            reduce_master_spiders = cluster.proxyinstance_set.filter(
                tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER
            )
            reduce_slave_spiders = cluster.proxyinstance_set.filter(
                tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE
            )
            if self.data["is_safe"]:
                sub_pipeline.add_act(
                    act_name=_("检测回收Spider端连接情况"),
                    act_component_code=CheckClientConnComponent.code,
                    kwargs=asdict(
                        CheckClientConnKwargs(
                            bk_cloud_id=cluster.bk_cloud_id,
                            check_instances=["{}:{}".format(s.machine.ip, s.port) for s in reduce_master_spiders],
                        )
                    ),
                )
            # 回收对应的域名关系
            reduce_spiders = [{"ip": s.machine.ip} for s in reduce_master_spiders] + [
                {"ip": s.machine.ip} for s in reduce_slave_spiders
            ]
            # sub_pipeline.add_act(
            #     act_name=_("回收对应spider集群映射"),
            #     act_component_code=MySQLDnsManageComponent.code,
            #     kwargs=asdict(
            #         RecycleDnsRecordKwargs(
            #             bk_cloud_id=cluster.bk_cloud_id,
            #             dns_op_exec_port=cluster.proxyinstance_set.first().port,
            #             exec_ip=[info["ip"] for info in reduce_spiders],
            #         ),
            #     ),
            # )
            entrysub_process = BuildEntrysManageSubflow(
                root_id=self.root_id,
                ticket_data=self.data,
                op_type=DnsOpType.RECYCLE_RECORD,
                param={
                    "cluster_id": cluster.id,
                    "port": cluster.proxyinstance_set.first().port,
                    "del_ips": [info["ip"] for info in reduce_spiders],
                    "entry_role": [ClusterEntryRole.MASTER_ENTRY.value, ClusterEntryRole.SLAVE_ENTRY.value],
                },
            )
            sub_pipeline.add_sub_pipeline(sub_flow=entrysub_process)
            # 删除spider的路由关系
            sub_pipeline.add_act(
                act_name=_("删除spider的路由关系"),
                act_component_code=DropSpiderRoutingComponent.code,
                kwargs=asdict(
                    DropSpiderRoutingKwargs(
                        cluster_id=cluster.id,
                        is_safe=self.data["is_safe"],
                        reduce_spiders=reduce_spiders,
                    )
                ),
            )
            # 更新集群模块信息
            sub_pipeline.add_act(
                act_name=_("更新集群db模块信息"),
                act_component_code=MySQLDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.update_cluster_module.__name__,
                        cluster={
                            "cluster_ids": [cluster_id],
                            "new_module_id": new_db_module_id,
                        },
                    )
                ),
            )
            # 后续流程需要在这里加一个暂停节点，让用户在合适的时间执行下架
            sub_pipeline.add_act(act_name=_("人工确认"), act_component_code=PauseComponent.code, kwargs={})
            # 根据场景执行下架spider子流程
            sub_flow_context["force"] = True
            if len(reduce_slave_spiders) > 0:
                sub_pipeline.add_sub_pipeline(
                    sub_flow=reduce_spider_flow(
                        cluster=cluster,
                        reduce_spiders=[{"ip": s.machine.ip} for s in reduce_slave_spiders],
                        root_id=self.root_id,
                        parent_global_data=sub_flow_context,
                        spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE,
                    )
                )
            sub_pipeline.add_sub_pipeline(
                sub_flow=reduce_spider_flow(
                    cluster=cluster,
                    reduce_spiders=[{"ip": s.machine.ip} for s in reduce_master_spiders],
                    root_id=self.root_id,
                    parent_global_data=sub_flow_context,
                    spider_role=TenDBClusterSpiderRole.SPIDER_MASTER,
                )
            )
            # append sub pipeline
            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("[{}]spider节点迁移升级流程".format(cluster.name))))
        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        pipeline.run_pipeline()
        return

    def local_upgrade(self):
        """
        spider 本地升级场景
        {
            bk_biz_id: 0,
            bk_cloud_id: 0,
            infos:[
                {
                    cluster_id:,
                    pkg_id:  12,
                    "new_db_module_id": 112,
                }
            ]
        }
        """
        spider_upgrade_pipeline = Builder(
            root_id=self.root_id, data=self.data, need_random_pass_cluster_ids=self.cluster_ids
        )
        sub_pipelines = []
        for upgrade_info in self.data["infos"]:
            cluster_id = upgrade_info["cluster_id"]
            pkg_id = upgrade_info["pkg_id"]
            new_db_module_id = upgrade_info["new_db_module_id"]
            spider_pkg = Package.objects.get(id=pkg_id)
            logger.info("param pkg_id:{},get the pkg name: {}".format(pkg_id, spider_pkg.name))
            cluster = Cluster.objects.get(id=cluster_id)
            bk_cloud_id = cluster.bk_cloud_id
            sub_flow_context = copy.deepcopy(self.data)
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))
            spiders = ProxyInstance.objects.filter(cluster=cluster)
            if len(spiders) <= 0:
                raise DBMetaException(message=_("根据cluster ids:{}法找到对应的proxy实例").format(cluster_id))
            spider_ips = []
            spider_master_ins = []
            for spider_ins in spiders:
                spider_ips.append(spider_ins.machine.ip)
                spider_role = spider_ins.tendbclusterspiderext.spider_role
                if spider_role == TenDBClusterSpiderRole.SPIDER_MASTER:
                    spider_master_ins.append(f"{spider_ins.machine.ip}{IP_PORT_DIVIDER}{spider_ins.port}")
            # 切换前做预检测
            if not self.upgrade_local:
                sub_pipeline.add_act(
                    act_name=_("检查Master Spider端连接情况"),
                    act_component_code=CheckClientConnComponent.code,
                    kwargs=asdict(
                        CheckClientConnKwargs(
                            bk_cloud_id=cluster.bk_cloud_id,
                            check_instances=spider_ins,
                        )
                    ),
                )
            # 提前下发文件
            sub_pipeline.add_act(
                act_name=_("下发升级的安装包"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=bk_cloud_id,
                        exec_ip=spider_ips,
                        file_list=GetFileList(db_type=DBType.MySQL).spider_upgrade_package(pkg_id=pkg_id),
                    )
                ),
            )
            spider_slave_upgrade_pipelines = []
            spider_master_upgrade_pipelines = []
            new_spider_version = get_spider_sub_version_by_pkg_name(spider_pkg.name)
            for spider_ins in spiders:
                spider_role = spider_ins.tendbclusterspiderext.spider_role
                spider_ip = spider_ins.machine.ip
                spider_port = spider_ins.port
                if spider_role == TenDBClusterSpiderRole.SPIDER_SLAVE:
                    spider_slave_upgrade_pipelines.append(
                        self.upgrade_spider_subflow(
                            ip=spider_ip,
                            bk_cloud_id=bk_cloud_id,
                            pkg_id=pkg_id,
                            domain=cluster.immute_domain,
                            spider_version=new_spider_version,
                            spider_port=spider_port,
                            force_upgrade=self.force_upgrade,
                            sub_flow_context=sub_flow_context,
                        )
                    )
                if spider_role == TenDBClusterSpiderRole.SPIDER_MASTER:
                    spider_master_upgrade_pipelines.append(
                        self.upgrade_spider_subflow(
                            ip=spider_ip,
                            bk_cloud_id=bk_cloud_id,
                            pkg_id=pkg_id,
                            domain=cluster.immute_domain,
                            spider_version=new_spider_version,
                            spider_port=spider_port,
                            force_upgrade=self.force_upgrade,
                            sub_flow_context=sub_flow_context,
                        )
                    )
            # spider slave 一起升级
            if len(spider_slave_upgrade_pipelines) > 0:
                sub_pipeline.add_parallel_sub_pipeline(spider_slave_upgrade_pipelines)
            # spider master 分两批次升级
            mid = len(spider_master_upgrade_pipelines) // 2  # 整数除法，自动向下取整
            part1 = spider_master_upgrade_pipelines[:mid]
            part2 = spider_master_upgrade_pipelines[mid:]
            sub_pipeline.add_parallel_sub_pipeline(part1)
            sub_pipeline.add_parallel_sub_pipeline(part2)
            # 更新集群模块信息
            sub_pipeline.add_act(
                act_name=_("更新集群db模块信息"),
                act_component_code=MySQLDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.update_cluster_module.__name__,
                        cluster={
                            "cluster_ids": [cluster_id],
                            "new_module_id": new_db_module_id,
                        },
                    )
                ),
            )
            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("本地升级spider版本")))
        spider_upgrade_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        spider_upgrade_pipeline.run_pipeline()
        return

    def upgrade_spider_subflow(
        self,
        ip: str,
        bk_cloud_id: int,
        pkg_id: int,
        domain: str,
        spider_version: str,
        spider_port: int,
        force_upgrade: bool,
        sub_flow_context: dict,
    ):
        """
        定义upgrade tendbcluster spider 本地升级 的flow
        """
        sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))
        # 执行本地升级
        # 回收对应的域名关系
        sub_pipeline.add_act(
            act_name=_("回收对应spider域名解析"),
            act_component_code=MySQLDnsManageComponent.code,
            kwargs=asdict(
                RecycleDnsRecordKwargs(
                    bk_cloud_id=bk_cloud_id,
                    dns_op_exec_port=spider_port,
                    exec_ip=[ip],
                ),
            ),
        )
        cluster = {"proxy_ports": [spider_port], "pkg_id": pkg_id, "force_upgrade": force_upgrade}
        exec_act_kwargs = ExecActuatorKwargs(cluster=cluster, bk_cloud_id=bk_cloud_id)
        exec_act_kwargs.exec_ip = ip
        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_spider_upgrade_payload.__name__
        sub_pipeline.add_act(
            act_name=_("更新spider instance status -> upgrade"),
            act_component_code=MySQLDBMetaComponent.code,
            kwargs=asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=MySQLDBMeta.update_proxy_instance_status.__name__,
                    cluster={"proxy_ip": ip, "phase": InstancePhase.UPGRADING, "status": InstanceStatus.UPGRADING},
                )
            ),
        )
        sub_pipeline.add_act(
            act_name=_("执行本地升级"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(exec_act_kwargs),
        )
        # 更新proxy instance version 信息
        act_list = []
        act_list.append(
            {
                "act_name": _("更新spider version meta信息"),
                "act_component_code": MySQLDBMetaComponent.code,
                "kwargs": asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.update_proxy_instance_version.__name__,
                        cluster={"proxy_ip": ip, "version": spider_version},
                    )
                ),
            }
        )
        act_list.append(
            {
                "act_name": _("更新spider instance status -> online"),
                "act_component_code": MySQLDBMetaComponent.code,
                "kwargs": asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.update_proxy_instance_status.__name__,
                        cluster={"proxy_ip": ip, "phase": InstancePhase.ONLINE, "status": InstanceStatus.RUNNING},
                    )
                ),
            }
        )
        sub_pipeline.add_parallel_acts(act_list)
        sub_pipeline.add_act(
            act_name=_("添加集群域名"),
            act_component_code=MySQLDnsManageComponent.code,
            kwargs=asdict(
                CreateDnsKwargs(
                    bk_cloud_id=bk_cloud_id,
                    add_domain_name=domain,
                    dns_op_exec_port=spider_port,
                    exec_ip=[ip],
                )
            ),
        )
        return sub_pipeline.build_sub_process(sub_name=_("{}spider实例升级").format(ip))


def reduce_spider_flow(
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
                "act_name": _("{}:{} 卸载spider实例".format(spider["ip"], spider_port)),
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
                    "act_name": _("{}:{} 卸载中控实例".format(ctl["ip"], spider_admin_port)),
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
                db_meta_class_func=SpiderDBMeta.del_spider_nodes_meta.__name__,
                cluster={
                    "cluster_id": cluster.id,
                    "spiders": reduce_spiders,
                },
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
    reduce_ctl_secondary_list = []

    # 计算每个待回收的ctl的角色，分配下架行为
    for ctl in reduce_ctls:
        reduce_ctl_secondary_list.append(f"{ctl.machine.ip}{IP_PORT_DIVIDER}{ctl.admin_port}")

    sub_pipeline = SubBuilder(root_id=root_id, data=parent_global_data)

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
    if len(acts_list) > 0:
        sub_pipeline.add_parallel_acts(acts_list=acts_list)

    return sub_pipeline.build_sub_process(sub_name=_("删除中控的路由节点"))
