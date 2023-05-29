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
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster, StorageInstance
from backend.flow.consts import HdfsRoleEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.hdfs.check_cluster_status import CheckClusterStatusComponent
from backend.flow.plugins.components.collections.hdfs.exec_actuator_script import ExecuteHdfsActuatorScriptComponent
from backend.flow.plugins.components.collections.hdfs.get_hdfs_payload import GetHdfsActPayloadComponent
from backend.flow.plugins.components.collections.hdfs.hdfs_db_meta import HdfsDBMetaComponent
from backend.flow.plugins.components.collections.hdfs.trans_flies import TransFileComponent
from backend.flow.utils.hdfs.hdfs_act_playload import HdfsActPayload, get_cluster_all_ip_from_meta
from backend.flow.utils.hdfs.hdfs_context_dataclass import ActKwargs, HdfsApplyContext

logger = logging.getLogger("flow")


class HdfsEnableFlow(object):
    """
    构建HDFS集群重新启用流程
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        :param root_id: 任务流程定义的root_id
        :param data: 单据传递过来的参数列表，字典格式
        """
        self.root_id = root_id
        self.data = data
        self.__init_data_with_role()

    def enable_hdfs_flow(self):
        """
        启用HDFS集群
        """
        # Builder 传参 为封装好角色IP的数据结构
        hdfs_pipeline = Builder(root_id=self.root_id, data=self.data_with_role)
        trans_files = GetFileList(db_type=DBType.Hdfs)

        # 拼接活动节点需要的私有参数
        act_kwargs = ActKwargs(bk_cloud_id=self.data_with_role["bk_cloud_id"])
        act_kwargs.set_trans_data_dataclass = HdfsApplyContext.__name__
        act_kwargs.file_list = trans_files.hdfs_actuator()

        hdfs_pipeline.add_act(
            act_name=_("检查集群状态"), act_component_code=CheckClusterStatusComponent.code, kwargs=asdict(act_kwargs)
        )

        hdfs_pipeline.add_act(
            act_name=_("获取集群部署配置"), act_component_code=GetHdfsActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )

        all_ips = get_cluster_all_ip_from_meta(self.data["cluster_id"])
        act_kwargs.exec_ip = all_ips
        hdfs_pipeline.add_act(
            act_name=_("下发hdfs actuator"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
        )

        zk_acts = []
        for ip in self.data_with_role["zk_ips"]:
            # 启动ZooKeeper
            act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_common_start_component_payload.__name__
            act_kwargs.exec_ip = ip
            act_kwargs.hdfs_role = HdfsRoleEnum.ZooKeeper.value
            zk_act = {
                "act_name": _("启动HDFS集群ZK-{}").format(ip),
                "act_component_code": ExecuteHdfsActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            zk_acts.append(zk_act)
        hdfs_pipeline.add_parallel_acts(acts_list=zk_acts)

        jn_acts = []
        for ip in self.data_with_role["jn_ips"]:
            # 启动JournalNode
            act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_common_start_component_payload.__name__
            act_kwargs.exec_ip = ip
            act_kwargs.hdfs_role = HdfsRoleEnum.JournalNode.value
            jn_act = {
                "act_name": _("启动HDFS集群JN-{}").format(ip),
                "act_component_code": ExecuteHdfsActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            jn_acts.append(jn_act)
        hdfs_pipeline.add_parallel_acts(acts_list=jn_acts)

        sub_pipelines = []
        for ip in self.data_with_role["nn_ips"]:
            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data_with_role)
            # 启动NameNode
            act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_common_start_component_payload.__name__
            act_kwargs.exec_ip = ip
            act_kwargs.hdfs_role = HdfsRoleEnum.NameNode.value
            sub_pipeline.add_act(
                act_name=_("启动HDFS集群NN-{}").format(ip),
                act_component_code=ExecuteHdfsActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )
            # 启动ZKFC
            act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_common_start_component_payload.__name__
            act_kwargs.exec_ip = ip
            act_kwargs.hdfs_role = HdfsRoleEnum.ZKFailController.value
            sub_pipeline.add_act(
                act_name=_("启动HDFS集群ZKFC-{}").format(ip),
                act_component_code=ExecuteHdfsActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )
            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("启动HDFS集群NN服务-{}子流程").format(ip)))
        hdfs_pipeline.add_parallel_sub_pipeline(sub_pipelines)

        dn_acts = []
        for ip in self.data_with_role["dn_ips"]:
            # 启动DataNode
            act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_common_start_component_payload.__name__
            act_kwargs.exec_ip = ip
            act_kwargs.hdfs_role = HdfsRoleEnum.DataNode.value
            dn_act = {
                "act_name": _("启动HDFS集群DN-{}").format(ip),
                "act_component_code": ExecuteHdfsActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            dn_acts.append(dn_act)
        hdfs_pipeline.add_parallel_acts(acts_list=dn_acts)

        # 修改DBMeta
        hdfs_pipeline.add_act(
            act_name=_("修改Meta"), act_component_code=HdfsDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )
        hdfs_pipeline.run_pipeline()

    def __init_data_with_role(self):
        data_with_role = copy.deepcopy(self.data)
        # 从cluster_id 获取cluster
        cluster = Cluster.objects.get(id=self.data["cluster_id"])
        self.cluster = cluster
        data_with_role["cluster_phase"] = cluster.phase
        data_with_role["cluster_name"] = cluster.name
        data_with_role["db_version"] = cluster.major_version
        data_with_role["bk_biz_id"] = cluster.bk_biz_id
        data_with_role["bk_cloud_id"] = cluster.bk_cloud_id

        data_with_role["nn_ips"] = [
            instance.machine.ip
            for instance in StorageInstance.objects.filter(cluster=cluster, instance_role=InstanceRole.HDFS_NAME_NODE)
        ]
        data_with_role["zk_ips"] = [
            instance.machine.ip
            for instance in StorageInstance.objects.filter(cluster=cluster, instance_role=InstanceRole.HDFS_ZOOKEEPER)
        ]
        data_with_role["jn_ips"] = [
            instance.machine.ip
            for instance in StorageInstance.objects.filter(
                cluster=cluster, instance_role=InstanceRole.HDFS_JOURNAL_NODE
            )
        ]
        data_with_role["dn_ips"] = [
            instance.machine.ip
            for instance in StorageInstance.objects.filter(cluster=cluster, instance_role=InstanceRole.HDFS_DATA_NODE)
        ]
        self.data_with_role = data_with_role
