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

from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext as _

from backend.components.db_remote_service.client import DRSApi
from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterType, InstanceInnerRole, TenDBClusterSpiderRole
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import Cluster, StorageInstance
from backend.flow.consts import LONG_JOB_TIMEOUT, PrivRole
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.sync_master import SyncMasterComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.spider.add_system_user_in_cluster import (
    AddSystemUserInClusterComponent,
)
from backend.flow.utils.base.base_dataclass import Instance
from backend.flow.utils.mysql.mysql_act_dataclass import (
    AddSpiderSystemUserKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
    MysqlSyncMasterKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload

logger = logging.getLogger("flow")


class AppendDeployCTLFlow(object):
    """
    migrate cluster from gcs
    1、追加部署中控
    2、授权
    3、导入表结构
    4、检查表结构一致性
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        {
            "bk_cloud_id": <bk_cloud_id>,
            "bk_biz_id": <bk_biz_id>,
            "drop_before": False,
            "use_stream": True,
            "use_mydumper": true,
            "cluster_ids": [1, 2, 3]
        }
        """
        self.root_id = root_id
        self.data = data
        self.cluster_type = ClusterType.TenDBCluster
        self.tdbctl_pass = ""
        self.tdbctl_user = ""
        self.charset = ""
        self.threads = 0
        self.bk_cloud_id = 0
        # stream mydumper & myloader 流式备份导入，否则退化成mysqldump方式
        self.use_mydumper = False
        if self.data.get("use_mydumper"):
            self.use_mydumper = self.data["use_mydumper"]
        self.stream = False
        if self.data.get("use_stream"):
            self.stream = self.data["use_stream"]
        # drop_before 导入到中控是否带上drop语句
        self.drop_before = False
        if self.data.get("drop_before"):
            self.drop_before = self.data["drop_before"]
        if self.data.get("bk_cloud_id"):
            self.bk_cloud_id = self.data["bk_cloud_id"]

    def __get_init_tdbctl_router_payload(self, cluster: Cluster):
        info = {
            "spider_instances": [],
            "spider_slave_instances": [],
            "mnt_spider_instances": [],
            "mnt_spider_slave_instances": [],
            "mysql_instance_tuples": [],
            "ctl_instances": [],
            "tdbctl_user": self.tdbctl_user,
            "tdbctl_pass": self.tdbctl_pass,
            "only_init_ctl": False,
        }
        # create master spiders
        master_spiders = cluster.proxyinstance_set.filter(
            tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER.value
        )

        slave_spiders = cluster.proxyinstance_set.filter(
            tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE.value
        )

        mnt_spiders = cluster.proxyinstance_set.filter(
            tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MNT.value
        )

        mnt_slave_spiders = cluster.proxyinstance_set.filter(
            tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE_MNT.value
        )

        for master_spider in master_spiders:
            # create ctl instances
            info["ctl_instances"].append(
                {"host": master_spider.machine.ip, "port": self.__get_tdbctl_port_by_spider_port(master_spider.port)}
            )
            info["spider_instances"].append({"host": master_spider.machine.ip, "port": master_spider.port})

        # create slave spiders
        for slave_spider in slave_spiders:
            info["spider_slave_instances"].append({"host": slave_spider.machine.ip, "port": slave_spider.port})

        for mnt_spider in mnt_spiders:
            info["mnt_spider_instances"].append({"host": mnt_spider.machine.ip, "port": mnt_spider.port})

        for mnt_spider in mnt_slave_spiders:
            info["mnt_spider_slave_instances"].append({"host": mnt_spider.machine.ip, "port": mnt_spider.port})

        shards = cluster.tendbclusterstorageset_set.filter()
        for shard in shards:
            remote_master = StorageInstance.objects.get(id=shard.storage_instance_tuple.ejector_id)
            remote_slave = StorageInstance.objects.get(id=shard.storage_instance_tuple.receiver_id)
            info["mysql_instance_tuples"].append(
                {
                    "host": remote_master.machine.ip,
                    "port": remote_master.port,
                    "slave_host": remote_slave.machine.ip,
                    "shard_id": shard.shard_id,
                }
            )
        return info

    @staticmethod
    def __get_tdbctl_port_by_spider_port(port: int):
        return port + 1000

    def __get_origin_spider_sys_account(self, spider_ip: str, port: int):
        # 获取集群原来的系统账户和密码
        logger.info(f"param: {spider_ip}:{port}")
        body = {
            "addresses": ["{}{}{}".format(spider_ip, IP_PORT_DIVIDER, port)],
            "cmds": ["select distinct Username,Password from mysql.servers"],
            "force": False,
            "bk_cloud_id": self.bk_cloud_id,
        }
        resp = DRSApi.rpc(body)
        logger.info(f"query spider mysql.servers {resp}")
        if not resp[0]["cmd_results"]:
            raise Exception(_("DRS查询集群系统密码失败:{}").format(resp[0]["error_msg"]))
        accounts = resp[0]["cmd_results"][0]["table_data"]
        if len(accounts) != 1:
            raise Exception(_("查询原系统账户存在多个或者不存在,暂时与dbm系统不兼容"))
        account = accounts[0]
        return account["Username"], account["Password"]

    def __get_spider_charset(self, spider_ip: str, port: int) -> str:
        # 获取远端字符集
        logger.info(f"param: {spider_ip}:{port}")
        body = {
            "addresses": ["{}{}{}".format(spider_ip, IP_PORT_DIVIDER, port)],
            "cmds": ["show global variables like 'character_set_server'"],
            "force": False,
            "bk_cloud_id": self.bk_cloud_id,
        }

        resp = DRSApi.rpc(body)
        logger.info(f"query charset {resp}")

        if not resp[0]["cmd_results"]:
            raise Exception(_("DRS查询字符集失败:{}").format(resp[0]["error_msg"]))

        charset = resp[0]["cmd_results"][0]["table_data"][0]["Value"]
        if not charset:
            logger.error(_("获取字符集为空..."))
            raise Exception(_("获取字符集为空"))
        return charset

    def run(self):
        cluster_ids = self.data["cluster_ids"]
        pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []
        # 拼接执行原子任务活动节点需要的通用的私有参数结构体, 减少代码重复率，但引用时注意内部参数值传递的问题
        exec_act_kwargs = ExecActuatorKwargs(
            bk_cloud_id=int(self.data["bk_cloud_id"]),
            cluster_type=ClusterType.TenDBCluster,
            job_timeout=LONG_JOB_TIMEOUT,
        )

        for cluster_id in cluster_ids:
            try:
                cluster_obj = Cluster.objects.get(
                    pk=cluster_id, bk_biz_id=self.data["bk_biz_id"], cluster_type=self.cluster_type
                )
            except ObjectDoesNotExist:
                raise ClusterNotExistException(cluster_type=self.cluster_type, cluster_id=cluster_id)

            master_spiders = cluster_obj.proxyinstance_set.filter(
                tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER.value
            )
            slave_spiders = cluster_obj.proxyinstance_set.filter(
                tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE.value
            )
            mnt_spiders = cluster_obj.proxyinstance_set.filter(
                tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MNT.value
            )
            mnt_slave_spiders = cluster_obj.proxyinstance_set.filter(
                tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE_MNT.value
            )
            shard0 = cluster_obj.tendbclusterstorageset_set.get(
                shard_id=0, storage_instance_tuple__ejector__instance_inner_role=InstanceInnerRole.MASTER
            )
            shard0_host = shard0.storage_instance_tuple.receiver.machine.ip
            shard0_port = shard0.storage_instance_tuple.receiver.port
            master_spider_ips = [c.machine.ip for c in master_spiders]
            logging.info("master_spider_ips: %s" % [c.machine.ip for c in master_spiders])
            if len(master_spider_ips) < 2:
                raise Exception(_("至少需要2个以上的spider节点"))
            leader_spider = master_spiders[0]
            primary_ctl_ip = master_spider_ips[0]
            slave_ctp_ips = master_spider_ips[1:]
            backends = cluster_obj.storageinstance_set.all()
            if len(backends) < 0:
                raise Exception(_("沒有发现remote节点"))
            # 拿到其中一个remote的instance信息
            mysql_ports = []
            for remote in backends:
                if remote.machine.ip == backends[0].machine.ip:
                    mysql_ports.append(remote.port)
            # 赋值给全局参数
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context["spider_ip_list"] = [
                {"ip": value} for value in list(set([c.machine.ip for c in master_spiders]))
            ]
            if len(mnt_spiders) > 0:
                sub_flow_context["mnt_spider_ip_list"] = [
                    {"ip": value} for value in list(set([c.machine.ip for c in mnt_spiders]))
                ]
                sub_flow_context["mnt_spider_port"] = mnt_spiders[0].port
            if len(mnt_slave_spiders) > 0:
                sub_flow_context["mnt_slave_spider_ip_list"] = [
                    {"ip": value} for value in list(set([c.machine.ip for c in mnt_slave_spiders]))
                ]
                sub_flow_context["mnt_slave_spider_port"] = mnt_slave_spiders[0].port
            # 处理slave spider
            if len(slave_spiders) > 0:
                sub_flow_context["slave_spider_ip_list"] = [
                    {"ip": value} for value in list(set([c.machine.ip for c in slave_spiders]))
                ]
                sub_flow_context["slave_spider_port"] = slave_spiders[0].port
            sub_flow_context["tdbctl_ip_list"] = [
                {"ip": value} for value in list(set([c.machine.ip for c in master_spiders]))
            ]
            sub_flow_context["spider_port"] = leader_spider.port
            sub_flow_context["mysql_ip_list"] = [
                {"ip": value} for value in list(set([c.machine.ip for c in backends]))
            ]
            sub_flow_context["mysql_ports"] = mysql_ports
            ctl_port = self.__get_tdbctl_port_by_spider_port(leader_spider.port)
            sub_flow_context["ctl_port"] = ctl_port
            self.tdbctl_user, self.tdbctl_pass = self.__get_origin_spider_sys_account(
                leader_spider.machine.ip, leader_spider.port
            )
            self.charset = self.__get_spider_charset(leader_spider.machine.ip, leader_spider.port)
            # 本地调试参数
            # self.tdbctl_user="xxx"
            # self.tdbctl_pass="xxx"
            # self.charset = "utf8"
            # 给spider节点下发tdbctl介质, 还一起下发了actor
            migrate_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))
            migrate_pipeline.add_act(
                act_name=_("下发tdbCtl介质包"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=self.bk_cloud_id,
                        exec_ip=master_spider_ips,
                        file_list=GetFileList(db_type=DBType.MySQL).tdbctl_install_package(),
                    )
                ),
            )

            acts_list = [
                {
                    "act_name": _("安装临时备份程序"),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(
                        ExecActuatorKwargs(
                            cluster={},  # 这个理论上应该没有用
                            exec_ip=master_spider_ips,
                            bk_cloud_id=int(self.data["bk_cloud_id"]),
                            cluster_type=ClusterType.TenDBCluster.value,
                            get_mysql_payload_func=MysqlActPayload.get_install_tmp_db_backup_payload.__name__,
                        )
                    ),
                },
            ]

            # 这里中控实例安装和spider机器复用的
            for ctl_ip in master_spider_ips:
                exec_act_kwargs.exec_ip = ctl_ip
                exec_act_kwargs.cluster = {
                    "immutable_domain": cluster_obj.immute_domain,
                    "ctl_port": ctl_port,
                    "ctl_charset": self.charset,
                }
                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_append_deploy_ctl_payload.__name__
                acts_list.append(
                    {
                        "act_name": _("安装Tdbctl集群中控实例"),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(exec_act_kwargs),
                    }
                )

            migrate_pipeline.add_parallel_acts(acts_list=acts_list)
            # 构建spider中控集群
            migrate_pipeline.add_act(
                act_name=_("构建spider中控集群同步"),
                act_component_code=SyncMasterComponent.code,
                kwargs=asdict(
                    MysqlSyncMasterKwargs(
                        bk_biz_id=int(self.data["bk_biz_id"]),
                        bk_cloud_id=int(self.data["bk_cloud_id"]),
                        priv_role=PrivRole.TDBCTL.value,
                        master=Instance(host=primary_ctl_ip, port=ctl_port),
                        slaves=[Instance(host=slave_ip, port=ctl_port) for slave_ip in slave_ctp_ips],
                        is_gtid=True,
                        is_add_any=True,
                    )
                ),
            )
            # 内部集群节点之间授权
            migrate_pipeline.add_act(
                act_name=_("集群内部节点间授权"),
                act_component_code=AddSystemUserInClusterComponent.code,
                kwargs=asdict(
                    AddSpiderSystemUserKwargs(
                        ctl_master_ip=primary_ctl_ip,
                        user=self.tdbctl_user,
                        passwd=self.tdbctl_pass,
                        is_append_deploy=True,
                    )
                ),
            )
            # 阶段7 在ctl-master节点，仅仅添加中控的路由关系,导入需要该信息
            cluster_info = self.__get_init_tdbctl_router_payload(cluster=cluster_obj)
            cluster_info["only_init_ctl"] = True
            exec_act_kwargs.cluster = cluster_info
            exec_act_kwargs.exec_ip = primary_ctl_ip
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_init_tdbctl_routing_payload.__name__
            migrate_pipeline.add_act(
                act_name=_("初始化中控tdbctl节点间关系"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(exec_act_kwargs),
            )

            # 从spider节点dump出表结构导入到tdbctl master节点
            exec_act_kwargs.cluster = {
                "ctl_port": ctl_port,
                "spider_port": leader_spider.port,
                "stream": self.stream,
                "use_mydumper": self.use_mydumper,
                "drop_before": self.drop_before,
                "threads": self.threads,
                "shard_0_host": shard0_host,
                "shard_0_port": shard0_port,
                "tdbctl_user": self.tdbctl_user,
                "tdbctl_pass": self.tdbctl_pass,
            }
            exec_act_kwargs.exec_ip = primary_ctl_ip
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_import_schema_to_tdbctl_payload.__name__
            migrate_pipeline.add_act(
                act_name=_("从本地spider复制表结构到Master中控节点"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(exec_act_kwargs),
            )
            # 校验spider节点和tdbctldb表的数量
            exec_act_kwargs.cluster = {"ctl_port": ctl_port, "spider_port": leader_spider.port}
            exec_act_kwargs.exec_ip = primary_ctl_ip
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_check_schema_payload.__name__
            migrate_pipeline.add_act(
                act_name=_("校验spider和tdbctl节点表的数量"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(exec_act_kwargs),
            )

            # 最后刷新其他路由，这样做的目标的是安全起见
            cluster_info["only_init_ctl"] = False
            exec_act_kwargs.cluster = cluster_info
            exec_act_kwargs.exec_ip = primary_ctl_ip
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_init_tdbctl_routing_payload.__name__
            migrate_pipeline.add_act(
                act_name=_("初始化中控节与spider,remote点间关系"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(exec_act_kwargs),
            )
            sub_pipelines.append(
                migrate_pipeline.build_sub_process(
                    sub_name=_("[{}]追加部署tdbctl&迁移表结构").format(cluster_obj.immute_domain)
                )
            )
        # 运行流程
        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        pipeline.run_pipeline()
