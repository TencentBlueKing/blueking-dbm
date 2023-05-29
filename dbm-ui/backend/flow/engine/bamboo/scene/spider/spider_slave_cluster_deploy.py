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
from backend.db_meta.enums import ClusterType, InstanceInnerRole, InstanceStatus
from backend.db_meta.models import Cluster
from backend.flow.consts import AUTH_ADDRESS_DIVIDER
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.mysql.clone_user import CloneUserComponent
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
    InstanceUserCloneKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.spider.spider_bk_config import get_spider_version_and_charset
from backend.flow.utils.spider.spider_db_meta import SpiderDBMeta

logger = logging.getLogger("flow")


class TenDBSlaveClusterApplyFlow(object):
    """
    构建spider slave 集群添加流程抽象类
    支持不同云区域的db集群合并下架
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data

    @staticmethod
    def __get_cluster_info(cluster_id: int, new_spider_list: list) -> dict:
        """
        根据cluster_id 获取到单节点集群实例信息，单节点只有一个实例
        @param cluster_id: 需要下架的集群id
        """
        # 定义集群的所有slave实例的列表，添加路由关系需要
        slave_instances = []
        add_spider_slave_instances = []

        cluster = Cluster.objects.get(id=cluster_id)

        # 获取集群的分片信息，过滤具有REPEATER属性的存储对
        remote_tuples = cluster.tendbclusterstorageset_set.exclude(
            storage_instance_tuple__ejector__instance_inner_role=InstanceInnerRole.REPEATER
        )
        spider_port = cluster.proxyinstance_set.first().port

        # 集群中找个running状态的spider节点，作为这次的克隆权限的依据，保证集群内权限同步
        tmp_spider = cluster.proxyinstance_set.filter(status=InstanceStatus.RUNNING)[0]

        for shard in remote_tuples:
            slave_instances.append(
                {
                    "shard_id": shard.shard_id,
                    "host": shard.storage_instance_tuple.receiver.machine.ip,
                    "port": shard.storage_instance_tuple.receiver.port,
                }
            )

        for ip_info in new_spider_list:
            add_spider_slave_instances.append(
                {
                    "host": ip_info["ip"],
                    "port": spider_port,  # 新添加的spider slave 同一套集群统一同一个spider端口
                }
            )

        return {
            "id": cluster_id,
            "bk_cloud_id": cluster.bk_cloud_id,
            "bk_biz_id": cluster.bk_biz_id,
            "db_module_id": cluster.db_module_id,
            "name": cluster.name,
            "immutable_domain": cluster.immute_domain,
            "spider_port": spider_port,
            "slave_instances": slave_instances,
            "spider_slave_instances": add_spider_slave_instances,
            "tmp_spider": tmp_spider.ip_port(),
            "spider_ctl_master": cluster.tendbcluster_ctl_primary_address(),
        }

    def deploy_slave_cluster(self):
        """
        定义spider slave集群部署流程
        目前产品形态 spider专属一套集群，所以流程只支持spider单机单实例安装
        """
        pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        # 机器维度部署spider节点
        for info in self.data["infos"]:
            # 拼接子流程需要全局参数
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("infos")

            cluster = self.__get_cluster_info(
                cluster_id=info["cluster_id"], new_spider_list=info["spider_slave_ip_list"]
            )

            # 计算拼接相互缺失的全局参加
            sub_flow_context.update(info)
            sub_flow_context["spider_ports"] = [cluster["spider_port"]]
            sub_flow_context["spider_charset"], sub_flow_context["spider_version"] = get_spider_version_and_charset(
                bk_biz_id=cluster["bk_biz_id"], db_module_id=cluster["db_module_id"]
            )

            # 启动子流程
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

            # 拼接执行原子任务活动节点需要的通用的私有参数结构体, 减少代码重复率，但引用时注意内部参数值传递的问题
            exec_act_kwargs = ExecActuatorKwargs(
                cluster_type=ClusterType.TenDBCluster,
                bk_cloud_id=cluster["bk_cloud_id"],
            )

            # 阶段1 下发spider安装介质包
            sub_pipeline.add_act(
                act_name=_("下发spider安装介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=cluster["bk_cloud_id"],
                        exec_ip=[ip_info["ip"] for ip_info in info["spider_slave_ip_list"]],
                        file_list=GetFileList(db_type=DBType.MySQL).spider_slave_install_package(
                            spider_version=sub_flow_context["spider_version"]
                        ),
                    )
                ),
            )

            # 阶段2 初始化待安装机器
            exec_act_kwargs.exec_ip = [ip_info["ip"] for ip_info in info["spider_slave_ip_list"]]
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_sys_init_payload.__name__
            sub_pipeline.add_act(
                act_name=_("初始化机器"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(exec_act_kwargs),
            )

            # 阶段3 安装mysql-crond组件
            exec_act_kwargs.exec_ip = [ip_info["ip"] for ip_info in info["spider_slave_ip_list"]]
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_deploy_mysql_crond_payload.__name__
            sub_pipeline.add_act(
                act_name=_("部署mysql-crond"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(exec_act_kwargs),
            )

            # 阶段4 安装spider-slave实例，目前spider-slave机器属于单机单实例部署方式，专属一套集群
            acts_list = []
            for spider_ip in info["spider_slave_ip_list"]:
                exec_act_kwargs.exec_ip = spider_ip["ip"]
                exec_act_kwargs.cluster = {
                    "immutable_domain": cluster["immutable_domain"],
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

            # 阶段5 内部集群节点之间授权
            sub_pipeline.add_act(
                act_name=_("集群内部节点间授权"),
                act_component_code=AddSystemUserInClusterComponent.code,
                kwargs=asdict(AddSpiderSystemUserKwargs(ctl_master_ip=cluster["spider_ctl_master"]["ip"])),
            )

            sub_pipeline.add_act(
                act_name=_("中控Master下发DB-actuator"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=cluster["bk_cloud_id"],
                        exec_ip=cluster["spider_ctl_master"]["ip"],
                        file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    )
                ),
            )

            # 阶段6 spider-slave 路由初始化
            exec_act_kwargs.exec_ip = cluster["spider_ctl_master"]["ip"]
            exec_act_kwargs.cluster = cluster
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.add_spider_slave_routing_payload.__name__
            sub_pipeline.add_act(
                act_name=_("添加对应路由关系"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(exec_act_kwargs),
            )

            # 阶段7 集群的业务账号信息克隆到新的spider实例上, 因为目前spider中控实例无法有克隆权限的操作，只能在这里做
            acts_list = []
            for spider in info["spider_slave_ip_list"]:
                acts_list.append(
                    {
                        "act_name": _("克隆权限到spider节点[{}]".format(spider["ip"])),
                        "act_component_code": CloneUserComponent.code,
                        "kwargs": asdict(
                            InstanceUserCloneKwargs(
                                clone_data=[
                                    {
                                        "source": cluster["tmp_spider"],
                                        "target": f"{spider['ip']}{AUTH_ADDRESS_DIVIDER}{cluster['spider_port']}",
                                        "bk_cloud_id": cluster["bk_cloud_id"],
                                    },
                                ]
                            )
                        ),
                    }
                )
            sub_pipeline.add_parallel_acts(acts_list=acts_list)

            # 阶段8 添加从域名
            sub_pipeline.add_act(
                act_name=_("添加集群域名"),
                act_component_code=MySQLDnsManageComponent.code,
                kwargs=asdict(
                    CreateDnsKwargs(
                        bk_cloud_id=cluster["bk_cloud_id"],
                        add_domain_name=info["slave_domain"],
                        dns_op_exec_port=cluster["spider_port"],
                        exec_ip=[ip_info["ip"] for ip_info in info["spider_slave_ip_list"]],
                    )
                ),
            )

            # 阶段9 添加元数据
            sub_pipeline.add_act(
                act_name=_("更新DBMeta元信息"),
                act_component_code=SpiderDBMetaComponent.code,
                kwargs=asdict(DBMetaOPKwargs(db_meta_class_func=SpiderDBMeta.tendb_cluster_slave_apply.__name__)),
            )

            # 阶段10 spider安装周边组件
            # todo 这里暂时没有开发spider监控组件，暂时不对spider机器安装周边组件，后续补充
            # sub_pipeline.add_sub_pipeline(
            #     sub_flow=build_apps_for_spider_sub_flow(
            #         bk_cloud_id=int(self.data["bk_cloud_id"]),
            #         spiders=[spider["ip"] for spider in self.data["spider_ip_list"]],
            #         root_id=self.root_id,
            #         parent_global_data=copy.deepcopy(self.data),
            #
            #     )
            # )
            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("添加slave集群")))

        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        pipeline.run_pipeline()
