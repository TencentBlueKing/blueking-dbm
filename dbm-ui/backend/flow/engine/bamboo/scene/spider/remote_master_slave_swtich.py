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
from backend.db_meta.enums import ClusterType, InstanceStatus
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import Cluster, StorageInstanceTuple
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.common.common_sub_flow import (
    build_surrounding_apps_sub_flow,
    check_sub_flow,
)
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.spider.spider_db_meta import SpiderDBMetaComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DBMetaOPKwargs, DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.spider.spider_db_meta import SpiderDBMeta

logger = logging.getLogger("flow")


class RemoteMasterSlaveSwitchFlow(object):
    """
    构建TenDB Cluster集群remote存储对的互切流程，产品形态是整机切换，保证同一台机器的所有实例要不master角色，要不slave角色
    目前集群维度的额互切流程如下：
    1：下发db-actuator介质到中控primary机器
    2：下发中控执行互切逻辑命令，命令包括有：
    2.1：做前置检查
    2.2：中控执行切换主分片
    2.3：断开newMaster同步
    2.4：授权repl账号给oldMaster
    2.3：建立新的复制关系
    2.3：断开newMaster同步
    3: 修改元数据
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data

    def remote_switch(self):
        """
        构建remote互切的流程
        增加单据临时ADMIN账号的添加和删除逻辑
        """
        cluster_ids = [i["cluster_id"] for i in self.data["infos"]]
        switch_pipeline = Builder(
            root_id=self.root_id, data=self.data, need_random_pass_cluster_ids=list(set(cluster_ids))
        )
        sub_pipelines = []

        for info in self.data["infos"]:
            # 拼接子流程需要全局参数
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("infos")

            # 拼接子流程的全局参数
            sub_flow_context.update(info)

            # 获取对应集群相关对象
            try:
                cluster = Cluster.objects.get(id=info["cluster_id"], bk_biz_id=int(self.data["bk_biz_id"]))
            except Cluster.DoesNotExist:
                raise ClusterNotExistException(
                    cluster_id=info["cluster_id"], bk_biz_id=int(self.data["bk_biz_id"]), message=_("集群不存在")
                )

            # 获取所有接入层正在running 状态的spider列表
            spiders = cluster.proxyinstance_set.filter(status=InstanceStatus.RUNNING)

            # 获取中控primary
            ctl_primary = cluster.tendbcluster_ctl_primary_address()

            # 计算预检测需要参数
            check_client_conn_inst = []
            verify_checksum_tuples = []
            if sub_flow_context["is_check_process"]:
                # 需要做客户端连接检测，计算出需要做检查的实例
                check_client_conn_inst = [s.ip_port for s in spiders]

            if sub_flow_context["is_verify_checksum"]:
                # 需要检测checksum结果，计算出需要做checksum结果的存储对
                # 需要做客户端连接检测，计算出需要做检查的实例
                for t in sub_flow_context["switch_tuples"]:
                    objs = cluster.storageinstance_set.filter(machine__ip=t["master"]["ip"])
                    for master in objs:
                        slave = StorageInstanceTuple.objects.get(ejector=master).receiver
                        verify_checksum_tuples.append({"master": master.ip_port, "slave": slave.ip_port})

            # 启动子流程
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

            sub_pipeline.add_act(
                act_name=_("下发db-actuator介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=cluster.bk_cloud_id,
                        exec_ip=ctl_primary.split(":")[0],
                        file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    )
                ),
            )

            # 切换前做预检测
            sub_flow = check_sub_flow(
                uid=self.data["uid"],
                root_id=self.root_id,
                cluster=cluster,
                is_check_client_conn=sub_flow_context["is_check_process"],
                is_verify_checksum=sub_flow_context["is_verify_checksum"],
                check_client_conn_inst=check_client_conn_inst,
                verify_checksum_tuples=verify_checksum_tuples,
            )
            if sub_flow:
                sub_pipeline.add_sub_pipeline(sub_flow=sub_flow)

            sub_pipeline.add_act(
                act_name=_("执行切换"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        bk_cloud_id=cluster.bk_cloud_id,
                        get_mysql_payload_func=MysqlActPayload.tendb_cluster_remote_switch.__name__,
                        exec_ip=ctl_primary.split(":")[0],
                    )
                ),
            )

            sub_pipeline.add_act(
                act_name=_("变更db_meta元信息"),
                act_component_code=SpiderDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=SpiderDBMeta.remote_switch.__name__,
                    )
                ),
            )

            # 阶段7 切换后重建备份程序和数据校验程序
            # 如果旧master机器故障，则重建失败（主故障切换场景）
            sub_pipeline.add_sub_pipeline(
                sub_flow=build_surrounding_apps_sub_flow(
                    bk_cloud_id=cluster.bk_cloud_id,
                    master_ip_list=[info["slave"]["ip"] for info in info["switch_tuples"]],
                    slave_ip_list=[info["master"]["ip"] for info in info["switch_tuples"]],
                    root_id=self.root_id,
                    parent_global_data=copy.deepcopy(sub_flow_context),
                    is_init=False,
                    cluster_type=ClusterType.TenDBCluster.value,
                )
            )

            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("[{}]集群后端切换".format(cluster.name))))

        switch_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        switch_pipeline.run_pipeline(is_drop_random_user=True)
