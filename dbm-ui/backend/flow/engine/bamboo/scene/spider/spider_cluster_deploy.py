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
from typing import Dict, List, Optional

from django.utils.crypto import get_random_string
from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType, TenDBClusterSpiderRole
from backend.flow.consts import TDBCTL_USER
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.common.common_sub_flow import (
    build_repl_by_manual_input_sub_flow,
    build_surrounding_apps_sub_flow,
)
from backend.flow.engine.bamboo.scene.spider.common.common_sub_flow import build_apps_for_spider_sub_flow
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.spider.add_system_user_in_cluster import (
    AddSystemUserInClusterComponent,
)
from backend.flow.plugins.components.collections.spider.spider_db_meta import SpiderDBMetaComponent
from backend.flow.utils.mysql.mysql_act_dataclass import (
    AddSpiderSystemUserKwargs,
    CreateDnsKwargs,
    DBMetaOPKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import SpiderApplyManualContext
from backend.flow.utils.spider.spider_act_dataclass import InstanceTuple, ShardInfo
from backend.flow.utils.spider.spider_db_meta import SpiderDBMeta

logger = logging.getLogger("flow")


class TenDBClusterApplyFlow(object):
    """
    构建spider(tenDB cluster)申请流程的抽象类
    单据不考虑支持多集群部署情况
    兼容跨云区域的场景支持
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data

        # 兼容多实例部署mysql的方法，只读上下文定义额外的变量
        self.data["clusters"] = []
        self.data["mysql_ports"] = []
        self.data["spider_ports"] = [self.data["spider_port"]]

        # 集群所有组件统一字符集配置
        self.data["ctl_charset"] = self.data["spider_charset"] = self.data["charset"]

        # 一个单据自动生成同一份随机密码, 中控实例需要，不需要内部来维护
        self.tdbctl_pass = get_random_string(length=10)

        # 声明中控实例的端口
        self.data["ctl_port"] = self.data["spider_port"] + 1000

        if len(self.data["mysql_ip_list"]) % 2 != 0:
            raise Exception(_("存入的存储节点数量不是偶数，请检查！"))

    def __calc_install_ports(self, inst_sum: int) -> list:
        """
        计算单据流程需要安装的端口，然后传入到流程的单据信息，
        @param : 代表机器部署实例数量
        """

        install_mysql_ports = []
        for i in range(0, inst_sum):
            install_mysql_ports.append(self.data["start_mysql_port"] + i)

            # 拼接clusters变量的内容
            self.data["clusters"].append(
                {"mysql_port": self.data["start_mysql_port"] + i, "master": self.data["immutable_domain"]}
            )

        return install_mysql_ports

    def __assign_shard_master_slave(self, install_port_list: list) -> Optional[List[ShardInfo]]:
        """
        根据需求场景，为集群每个分片组分配合适的主从机器
        todo 后续需要在自动分配时保持分片组的主从机器的反亲和性
        @param
        """
        shard_cluster_list = []
        master_ip = ""
        slave_ip = ""
        cycles = 0
        mysql_ip_list = copy.deepcopy(self.data["mysql_ip_list"])
        for key in range(1, self.data["cluster_shard_num"] + 1):

            if len(install_port_list) * cycles < key:
                master_ip = mysql_ip_list.pop(0)["ip"]
                slave_ip = mysql_ip_list.pop(0)["ip"]
                cycles += 1

            inst_tuple = InstanceTuple(
                master_ip=master_ip,
                slave_ip=slave_ip,
                mysql_port=install_port_list[(key - 1) % len(install_port_list)],
            )
            shard_info = ShardInfo(shard_key=key - 1, instance_tuple=inst_tuple)
            shard_cluster_list.append(shard_info)

        return shard_cluster_list

    def __create_cluster_nodes_info(self, shard_infos: Optional[List[ShardInfo]]) -> dict:
        """
        根据预分配好的分片信息，拼接初始化需要的cluster结构体
        """
        info = {
            "mysql_instance_tuples": [],
            "spider_instances": [],
            "ctl_instances": [],
            "tdbctl_user": TDBCTL_USER,
            "tdbctl_pass": self.tdbctl_pass,
        }
        for ip_info in self.data["spider_ip_list"]:
            info["spider_instances"].append({"host": ip_info["ip"], "port": self.data["spider_port"]})
        for ip_info in self.data["spider_ip_list"]:
            info["ctl_instances"].append({"host": ip_info["ip"], "port": self.data["ctl_port"]})
        for tmp in shard_infos:
            info["mysql_instance_tuples"].append(
                {
                    "host": tmp.instance_tuple.master_ip,
                    "port": tmp.instance_tuple.mysql_port,
                    "slave_host": tmp.instance_tuple.slave_ip,
                    "shard_id": tmp.shard_key,
                }
            )
        return info

    def deploy_cluster(self):
        """
        机器通过手动输入IP而触发的场景
        todo 集群所有节点的时区是否需要对比？如果要对比，怎么对比
        todo 补充周边组件部署
        todo 目前bamboo-engine存在bug，不能正常给trans_data初始化值，先用流程套子流程方式来避开这个问题
        """
        # 根据集群总分片数、存储节点数量计算出每个节点需要部署的实例的数量，
        # 比如总分片数是4，存储节点是4，那么每个存储需要部署2个实例(考虑主从)
        inst_sum = int(self.data["cluster_shard_num"] / int((len(self.data["mysql_ip_list"]) / 2)))

        # 计算每个mysql机器需要部署的mysql端口信息
        self.data["mysql_ports"] = self.__calc_install_ports(inst_sum=inst_sum)

        # 先确定谁是中控集群中谁是master，对后续做数据同步依赖和初始化集群路由信息依赖
        ctl_master = self.data["spider_ip_list"][0]
        ctl_slaves = self.data["spider_ip_list"][1:]

        # 初始化流程
        pipeline = Builder(root_id=self.root_id, data=self.data)
        deploy_pipeline = SubBuilder(root_id=self.root_id, data=self.data)

        # 拼接执行原子任务活动节点需要的通用的私有参数结构体, 减少代码重复率，但引用时注意内部参数值传递的问题
        exec_act_kwargs = ExecActuatorKwargs(
            bk_cloud_id=int(self.data["bk_cloud_id"]),
            cluster_type=ClusterType.TenDBCluster,
        )

        # 阶段1 并行分发安装文件
        deploy_pipeline.add_parallel_acts(
            acts_list=[
                {
                    "act_name": _("下发MySQL介质包"),
                    "act_component_code": TransFileComponent.code,
                    "kwargs": asdict(
                        DownloadMediaKwargs(
                            bk_cloud_id=int(self.data["bk_cloud_id"]),
                            exec_ip=[ip_info["ip"] for ip_info in self.data["mysql_ip_list"]],
                            file_list=GetFileList(db_type=DBType.MySQL).mysql_install_package(
                                db_version=self.data["db_version"]
                            ),
                        )
                    ),
                },
                {
                    "act_name": _("下发Spider/tdbCtl介质包"),
                    "act_component_code": TransFileComponent.code,
                    "kwargs": asdict(
                        DownloadMediaKwargs(
                            bk_cloud_id=int(self.data["bk_cloud_id"]),
                            exec_ip=[ip_info["ip"] for ip_info in self.data["spider_ip_list"]],
                            file_list=GetFileList(db_type=DBType.MySQL).spider_master_install_package(
                                spider_version=self.data["spider_version"],
                            ),
                        )
                    ),
                },
            ]
        )

        # 阶段2 批量初始化所有机器,安装crond进程
        exec_act_kwargs.exec_ip = [
            ip_info["ip"] for ip_info in self.data["mysql_ip_list"] + self.data["spider_ip_list"]
        ]
        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_sys_init_payload.__name__
        deploy_pipeline.add_act(
            act_name=_("初始化机器"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(exec_act_kwargs),
        )

        acts_list = []
        for ip_info in self.data["mysql_ip_list"] + self.data["spider_ip_list"]:
            exec_act_kwargs.exec_ip = ip_info["ip"]
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_deploy_mysql_crond_payload.__name__
            acts_list.append(
                {
                    "act_name": _("部署mysql-crond"),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(exec_act_kwargs),
                }
            )
        deploy_pipeline.add_parallel_acts(acts_list=acts_list)

        # 阶段3 并发安装mysql实例(一个活动节点部署多实例)
        acts_list = []
        for mysql_ip in self.data["mysql_ip_list"]:
            exec_act_kwargs.exec_ip = mysql_ip["ip"]
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_install_mysql_payload.__name__
            acts_list.append(
                {
                    "act_name": _("安装MySQL实例"),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(exec_act_kwargs),
                    "write_payload_var": SpiderApplyManualContext.get_time_zone_var_name(),
                }
            )
        deploy_pipeline.add_parallel_acts(acts_list=acts_list)

        acts_list = []
        # 定义每个spider节点auto_incr_mode_value值，单调递增
        auto_incr_value = 1
        for spider_ip in self.data["spider_ip_list"]:
            exec_act_kwargs.exec_ip = spider_ip["ip"]
            exec_act_kwargs.cluster = {
                "immutable_domain": self.data["immutable_domain"],
                "auto_incr_value": auto_incr_value,
            }
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_install_spider_payload.__name__
            acts_list.append(
                {
                    "act_name": _("安装Spider实例"),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(exec_act_kwargs),
                }
            )
            auto_incr_value += 1
        deploy_pipeline.add_parallel_acts(acts_list=acts_list)

        acts_list = []
        # 这里中控实例安装和spider机器复用的
        for ctl_ip in self.data["spider_ip_list"]:
            exec_act_kwargs.exec_ip = ctl_ip["ip"]
            exec_act_kwargs.cluster = {"immutable_domain": self.data["immutable_domain"]}
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_install_spider_ctl_payload.__name__
            acts_list.append(
                {
                    "act_name": _("安装Spider集群中控实例"),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(exec_act_kwargs),
                }
            )
        deploy_pipeline.add_parallel_acts(acts_list=acts_list)

        # 阶段4 为每个分片组建立主从关系
        sub_flow_list = []
        shard_infos = self.__assign_shard_master_slave(install_port_list=copy.deepcopy(self.data["mysql_ports"]))

        for info in shard_infos:
            sub_flow_list.append(
                build_repl_by_manual_input_sub_flow(
                    bk_cloud_id=self.data["bk_cloud_id"],
                    root_id=self.root_id,
                    parent_global_data=self.data,
                    master_ip=info.instance_tuple.master_ip,
                    slave_ip=info.instance_tuple.slave_ip,
                    mysql_port=info.instance_tuple.mysql_port,
                    sub_flow_name=f"Shard{info.shard_key}",
                )
            )
        deploy_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_flow_list)

        # 阶段5 构建spider中控集群
        deploy_pipeline.add_sub_pipeline(
            sub_flow=self.build_ctl_replication_with_gtid(ctl_master=ctl_master, ctl_slaves=ctl_slaves)
        )

        # 阶段6 内部集群节点之间授权
        deploy_pipeline.add_act(
            act_name=_("集群内部节点间授权"),
            act_component_code=AddSystemUserInClusterComponent.code,
            kwargs=asdict(
                AddSpiderSystemUserKwargs(ctl_master_ip=ctl_master["ip"], user=TDBCTL_USER, passwd=self.tdbctl_pass)
            ),
        )

        # 阶段7 在ctl-master节点，生成spider集群路由表信息；添加node信息
        exec_act_kwargs.cluster = self.__create_cluster_nodes_info(shard_infos=shard_infos)
        exec_act_kwargs.exec_ip = ctl_master
        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_init_spider_routing_payload.__name__
        deploy_pipeline.add_act(
            act_name=_("初始化集群节点间关系"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(exec_act_kwargs),
        )

        # 阶段8 添加相关域名
        deploy_pipeline.add_act(
            act_name=_("添加集群域名"),
            act_component_code=MySQLDnsManageComponent.code,
            kwargs=asdict(
                CreateDnsKwargs(
                    bk_cloud_id=self.data["bk_cloud_id"],
                    add_domain_name=self.data["immutable_domain"],
                    dns_op_exec_port=self.data["spider_port"],
                    exec_ip=[ip_info["ip"] for ip_info in self.data["spider_ip_list"]],
                )
            ),
        )
        # 阶段9 添加集群元数据
        deploy_pipeline.add_act(
            act_name=_("更新DBMeta元信息"),
            act_component_code=SpiderDBMetaComponent.code,
            kwargs=asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=SpiderDBMeta.tendb_cluster_apply.__name__,
                    cluster={"shard_infos": shard_infos},
                    is_update_trans_data=True,
                )
            ),
        )
        # 阶段10 remote安装周边组件
        deploy_pipeline.add_sub_pipeline(
            sub_flow=build_surrounding_apps_sub_flow(
                bk_cloud_id=int(self.data["bk_cloud_id"]),
                master_ip_list=list(set([info.instance_tuple.master_ip for info in shard_infos])),
                slave_ip_list=list(set([info.instance_tuple.slave_ip for info in shard_infos])),
                root_id=self.root_id,
                parent_global_data=copy.deepcopy(self.data),
                is_init=True,
                cluster_type=ClusterType.TenDBCluster.value,
            )
        )

        # 阶段11 spider安装周边组件
        deploy_pipeline.add_sub_pipeline(
            sub_flow=build_apps_for_spider_sub_flow(
                bk_cloud_id=int(self.data["bk_cloud_id"]),
                spiders=[spider["ip"] for spider in self.data["spider_ip_list"]],
                root_id=self.root_id,
                parent_global_data=copy.deepcopy(self.data),
                spider_role=TenDBClusterSpiderRole.SPIDER_MASTER,
            )
        )

        pipeline.add_sub_pipeline(
            sub_flow=deploy_pipeline.build_sub_process(sub_name=_("{}集群部署").format(self.data["cluster_name"]))
        )
        pipeline.run_pipeline(init_trans_data_class=SpiderApplyManualContext())

    def build_ctl_replication_with_gtid(self, ctl_master: dict, ctl_slaves: list):
        """
        定义ctl建立基于gtid的主从同步
        """

        cluster = {
            "mysql_port": self.data["ctl_port"],
            "master_ip": ctl_master["ip"],
            "slaves": [ip_info["ip"] for ip_info in ctl_slaves],
        }

        sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
        sub_pipeline.add_act(
            act_name=_("新增repl帐户"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(
                ExecActuatorKwargs(
                    bk_cloud_id=self.data["bk_cloud_id"],
                    exec_ip=ctl_master["ip"],
                    get_mysql_payload_func=MysqlActPayload.get_grant_repl_for_ctl_payload.__name__,
                    cluster=cluster,
                )
            ),
        )
        acts_list = []
        for slave in ctl_slaves:
            acts_list.append(
                {
                    "act_name": _("建立主从关系"),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(
                        ExecActuatorKwargs(
                            bk_cloud_id=self.data["bk_cloud_id"],
                            exec_ip=slave["ip"],
                            get_mysql_payload_func=MysqlActPayload.get_change_master_for_gitd_payload.__name__,
                            cluster=cluster,
                        )
                    ),
                }
            )

        sub_pipeline.add_parallel_acts(acts_list=acts_list)
        return sub_pipeline.build_sub_process(sub_name=_("部署spider-ctl集群"))
