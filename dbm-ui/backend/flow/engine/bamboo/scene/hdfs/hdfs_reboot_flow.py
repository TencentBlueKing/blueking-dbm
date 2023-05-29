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
from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.hdfs.exec_actuator_script import ExecuteHdfsActuatorScriptComponent
from backend.flow.plugins.components.collections.hdfs.get_hdfs_payload import GetHdfsActPayloadComponent
from backend.flow.plugins.components.collections.hdfs.trans_flies import TransFileComponent
from backend.flow.utils.hdfs.hdfs_act_playload import HdfsActPayload
from backend.flow.utils.hdfs.hdfs_context_dataclass import ActKwargs, HdfsApplyContext

logger = logging.getLogger("flow")


class HdfsRebootFlow(object):
    """
    构建HDFS集群实例重启流程
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        :param root_id: 任务流程定义的root_id
        :param data: 单据传递过来的参数列表，字典格式
        """
        self.root_id = root_id
        self.data = data
        self.__init_data_with_role()

    def reboot_hdfs_flow(self):
        """
        重启HDFS集群实例
        """
        # Builder 传参 为封装好角色IP的数据结构
        hdfs_pipeline = Builder(root_id=self.root_id, data=self.data_with_role)
        trans_files = GetFileList(db_type=DBType.Hdfs)

        # 拼接活动节点需要的私有参数
        act_kwargs = ActKwargs(bk_cloud_id=self.data_with_role["bk_cloud_id"])
        act_kwargs.set_trans_data_dataclass = HdfsApplyContext.__name__
        act_kwargs.file_list = trans_files.hdfs_actuator()

        hdfs_pipeline.add_act(
            act_name=_("获取集群部署配置"), act_component_code=GetHdfsActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )

        act_kwargs.exec_ip = self.__get_all_reboot_ips()
        hdfs_pipeline.add_act(
            act_name=_("下发hdfs actuator"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
        )

        reboot_acts = []
        # 是否判断实例是否存在
        for instance in self.data["instance_list"]:
            # 启动进程
            act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_common_restart_component_payload.__name__
            act_kwargs.exec_ip = instance["ip"]
            act_kwargs.hdfs_role = instance["instance_name"]
            reboot_act = {
                "act_name": _("重启实例-{}-{}").format(act_kwargs.exec_ip, act_kwargs.hdfs_role),
                "act_component_code": ExecuteHdfsActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            reboot_acts.append(reboot_act)
        # 并发执行所有重启实例
        hdfs_pipeline.add_parallel_acts(acts_list=reboot_acts)

        hdfs_pipeline.run_pipeline()

    def __get_all_reboot_ips(self) -> list:
        return list(set([instance["ip"] for instance in self.data["instance_list"]]))

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

        data_with_role["nn_ips"] = list(
            cluster.storageinstance_set.filter(instance_role=InstanceRole.HDFS_NAME_NODE).values_list(
                "machine__ip", flat=True
            )
        )
        data_with_role["zk_ips"] = list(
            cluster.storageinstance_set.filter(instance_role=InstanceRole.HDFS_ZOOKEEPER).values_list(
                "machine__ip", flat=True
            )
        )
        data_with_role["jn_ips"] = list(
            cluster.storageinstance_set.filter(instance_role=InstanceRole.HDFS_JOURNAL_NODE).values_list(
                "machine__ip", flat=True
            )
        )
        data_with_role["dn_ips"] = list(
            cluster.storageinstance_set.filter(instance_role=InstanceRole.HDFS_DATA_NODE).values_list(
                "machine__ip", flat=True
            )
        )
        self.data_with_role = data_with_role
