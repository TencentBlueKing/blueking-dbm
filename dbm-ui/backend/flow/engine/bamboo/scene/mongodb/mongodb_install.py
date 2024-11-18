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
import logging.config
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.db_meta.enums.cluster_type import ClusterType
from backend.flow.consts import DEPENDENCIES_PLUGINS, MongoDBClusterRole
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.mongodb.mongodb_install_dbmon import add_install_dbmon
from backend.flow.engine.bamboo.scene.mongodb.sub_task.mongos_install import mongos_install
from backend.flow.engine.bamboo.scene.mongodb.sub_task.replicaset_install import replicaset_install
from backend.flow.plugins.components.collections.common.install_nodeman_plugin import (
    InstallNodemanPluginServiceComponent,
)
from backend.flow.plugins.components.collections.mongodb.add_domain_to_dns import ExecAddDomainToDnsOperationComponent
from backend.flow.plugins.components.collections.mongodb.add_relationship_to_meta import (
    ExecAddRelationshipOperationComponent,
)
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job import ExecuteDBActuatorJobComponent
from backend.flow.plugins.components.collections.mongodb.get_manager_user_password import (
    ExecGetPasswordOperationComponent,
)
from backend.flow.plugins.components.collections.mongodb.send_media import ExecSendMediaOperationComponent
from backend.flow.utils.mongodb.calculate_cluster import calculate_cluster
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs

logger = logging.getLogger("flow")


def install_plugin(pipeline: Builder, get_kwargs: ActKwargs, new_cluster: bool):
    """安装蓝鲸插件"""

    acts_list = []
    for plugin_name in DEPENDENCIES_PLUGINS:
        acts_list.append(
            {
                "act_name": _("安装[{}]插件".format(plugin_name)),
                "act_component_code": InstallNodemanPluginServiceComponent.code,
                "kwargs": get_kwargs.get_install_plugin_kwargs(plugin_name=plugin_name, new_cluster=new_cluster),
            }
        )
    pipeline.add_parallel_acts(acts_list=acts_list)


class MongoDBInstallFlow(object):
    """MongoDB安装flow"""

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        传入参数
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """

        self.root_id = root_id
        # 计算cluster分布
        payload_clusters = calculate_cluster(data)
        self.data = payload_clusters
        self.get_kwargs = ActKwargs()
        self.get_kwargs.payload = payload_clusters
        self.get_kwargs.get_init_info()
        self.get_kwargs.get_file_path()

    def prepare_job(self, pipeline: Builder):
        """
        准备工作
        """

        # 获取appdba和appmonitor密码
        self.get_kwargs.get_app_dba_monitor_pwd()

        # 安装蓝鲸插件
        install_plugin(pipeline=pipeline, get_kwargs=self.get_kwargs, new_cluster=True)

        # 介质下发——job的api可以多个IP并行执行
        kwargs = self.get_kwargs.get_send_media_kwargs(media_type="all")
        pipeline.add_act(
            act_name=_("MongoDB-介质下发"), act_component_code=ExecSendMediaOperationComponent.code, kwargs=kwargs
        )

        # 创建原子任务执行目录
        kwargs = self.get_kwargs.get_create_dir_kwargs()
        pipeline.add_act(
            act_name=_("MongoDB-创建原子任务执行目录"), act_component_code=ExecuteDBActuatorJobComponent.code, kwargs=kwargs
        )

        # 机器初始化——job的api可以多个IP并行执行
        kwargs = self.get_kwargs.get_os_init_kwargs()
        pipeline.add_act(
            act_name=_("MongoDB-机器初始化"), act_component_code=ExecuteDBActuatorJobComponent.code, kwargs=kwargs
        )

    def install_dbmon(self, data: dict, pipeline: Builder):
        """
        install_dbmon, please run this after add_relationship_to_meta
        """
        ip_list = self.get_kwargs.payload["hosts"]
        exec_ips = [host["ip"] for host in ip_list]
        bk_cloud_id = ip_list[0]["bk_cloud_id"]
        add_install_dbmon(self.root_id, data, pipeline, exec_ips, bk_cloud_id, allow_empty_instance=True)

    def multi_replicaset_install_flow(self):
        """
        multi replicaset install流程
        """

        # 创建流程实例
        pipeline = Builder(root_id=self.root_id, data=self.data)

        # 下发介质和os初始化
        self.prepare_job(pipeline=pipeline)

        # 复制集安装——子流程并行
        sub_pipelines = []
        for replicaset_info in self.data["sets"]:
            self.get_kwargs.replicaset_info = replicaset_info
            sub_pipline = replicaset_install(
                root_id=self.root_id,
                ticket_data=self.data,
                sub_kwargs=self.get_kwargs,
                cluster=False,
                cluster_role="",
                config_svr=False,
            )
            sub_pipelines.append(sub_pipline)
        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        # 复制集关系写入meta
        for replicaset_info in self.data["sets"]:
            kwargs = self.get_kwargs.get_add_relationship_to_meta_kwargs(replicaset_info=replicaset_info)
            pipeline.add_act(
                act_name=_("MongoDB--添加复制集{}关系到meta".format(replicaset_info["set_id"])),
                act_component_code=ExecAddRelationshipOperationComponent.code,
                kwargs=kwargs,
            )

        # 安装dbmon
        self.install_dbmon(data=self.data, pipeline=pipeline)

        # 运行流程
        pipeline.run_pipeline()

    def cluster_install_flow(self):
        """
        cluster install流程
        """

        # 创建流程实例
        pipeline = Builder(root_id=self.root_id, data=self.data)

        # 下发介质和os初始化
        self.prepare_job(pipeline=pipeline)

        # 保存配置到dbconfig
        self.get_kwargs.save_conf(namespace=ClusterType.MongoShardedCluster.value)
        # 密码服务获取管理用户密码 shard，config的密码保持一致
        kwargs = self.get_kwargs.get_get_manager_password_kwargs()
        pipeline.add_act(
            act_name=_("MongoDB--获取管理员用户密码"), act_component_code=ExecGetPasswordOperationComponent.code, kwargs=kwargs
        )

        # cluster安装
        # config和shard安装——子流程并行
        sub_pipelines = []
        # 安装shard
        for replicaset_info in self.data["shards"]:
            self.get_kwargs.replicaset_info = replicaset_info
            sub_pipline = replicaset_install(
                root_id=self.root_id,
                ticket_data=self.data,
                sub_kwargs=self.get_kwargs,
                cluster=True,
                cluster_role=MongoDBClusterRole.ShardSvr,
                config_svr=False,
            )
            sub_pipelines.append(sub_pipline)
        # 安装config
        self.get_kwargs.replicaset_info = self.data["config"]
        sub_pipline = replicaset_install(
            root_id=self.root_id,
            ticket_data=self.data,
            sub_kwargs=self.get_kwargs,
            cluster=True,
            cluster_role=MongoDBClusterRole.ConfigSvr,
            config_svr=True,
        )
        sub_pipelines.append(sub_pipline)
        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        # mongos安装——子流程并行
        self.get_kwargs.mongos_info = self.data["mongos"]
        sub_pipline = mongos_install(
            root_id=self.root_id, ticket_data=self.data, sub_kwargs=self.get_kwargs, increase_mongos=False
        )
        pipeline.add_sub_pipeline(sub_flow=sub_pipline)

        # 添加shard到cluster
        kwargs = self.get_kwargs.get_add_shard_to_cluster_kwargs()
        pipeline.add_act(
            act_name=_("MongoDB--添加shards到cluster"),
            act_component_code=ExecuteDBActuatorJobComponent.code,
            kwargs=kwargs,
        )

        # cluster关系写入meta
        kwargs = self.get_kwargs.get_add_relationship_to_meta_kwargs(replicaset_info={})
        pipeline.add_act(
            act_name=_("MongoDB--添加关系到meta"),
            act_component_code=ExecAddRelationshipOperationComponent.code,
            kwargs=kwargs,
        )
        # 域名写入dns
        kwargs = self.get_kwargs.get_add_domain_to_dns_kwargs(cluster=True)
        pipeline.add_act(
            act_name=_("MongoDB--添加domain到dns"),
            act_component_code=ExecAddDomainToDnsOperationComponent.code,
            kwargs=kwargs,
        )

        # 安装dbmon
        self.install_dbmon(data=self.data, pipeline=pipeline)

        # 运行流程
        pipeline.run_pipeline()
