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

from backend.db_meta.enums import ClusterType
from backend.flow.consts import HdfsRoleEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.plugins.components.collections.hdfs.get_hdfs_resource import GetHdfsResourceComponent
from backend.flow.plugins.components.collections.hdfs.hdfs_db_meta import HdfsDBMetaComponent
from backend.flow.plugins.components.collections.hdfs.rewrite_hdfs_config import WriteBackHdfsConfigComponent
from backend.flow.utils.hdfs.hdfs_act_playload import gen_host_name_by_role
from backend.flow.utils.hdfs.hdfs_context_dataclass import ActKwargs, HdfsApplyContext

logger = logging.getLogger("flow")


class HdfsFakeApplyFlow(object):
    """
    构建hdfs虚拟申请流程类，用于迁移集群/IP等元数据
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
         @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data
        # 写入cluster_type，转模块会使用
        self.data["cluster_type"] = ClusterType.Hdfs.value
        self.__init_data_with_role(data)

    def fake_deploy_hdfs_flow(self):
        """
        定义部署hdfs集群参数
        """
        # Builder 传参 为封装好角色IP的数据结构
        hdfs_pipeline = Builder(root_id=self.root_id, data=self.data_with_role)

        # 拼接活动节点需要的私有参数
        act_kwargs = ActKwargs(bk_cloud_id=self.data["bk_cloud_id"])
        act_kwargs.set_trans_data_dataclass = HdfsApplyContext.__name__

        # 需要将配置项写入
        act_kwargs.is_update_trans_data = True

        # 获取机器资源
        hdfs_pipeline.add_act(
            act_name=_("获取机器信息"), act_component_code=GetHdfsResourceComponent.code, kwargs=asdict(act_kwargs)
        )

        hdfs_pipeline.add_act(
            act_name=_("更新DBMeta元信息"), act_component_code=HdfsDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        hdfs_pipeline.add_act(
            act_name=_("回写hdfs集群配置"), act_component_code=WriteBackHdfsConfigComponent.code, kwargs=asdict(act_kwargs)
        )

        hdfs_pipeline.run_pipeline()

    def __init_data_with_role(self, data: Optional[Dict]):
        # 对手动部署HDFS集群的单据 对角色对应IP做初始化，后续用作静态传参
        data_with_role = copy.deepcopy(data)

        data_with_role["nn1_ip"] = data["nodes"]["nn1"]["ip"]
        data_with_role["nn2_ip"] = data["nodes"]["nn2"]["ip"]

        zk_ips = [node["ip"] for node in data["nodes"][HdfsRoleEnum.ZooKeeper]]
        data_with_role["zk_ips"] = zk_ips
        data_with_role["jn_ips"] = zk_ips
        data_with_role["dn_ips"] = [node["ip"] for node in data["nodes"][HdfsRoleEnum.DataNode]]
        all_ip_set = {data_with_role["nn1_ip"], data_with_role["nn2_ip"]}
        all_ip_set.update(data_with_role["zk_ips"])
        # master_ips 字段目前仅 转模块 使用
        data_with_role["master_ips"] = list(all_ip_set)
        # 暂时jn与zk一致，无需添加
        all_ip_set.update(data_with_role["dn_ips"])
        data_with_role["all_ips"] = list(all_ip_set)

        all_ip_hosts = dict()
        all_ip_hosts[data_with_role["nn1_ip"]] = data["nodes"]["nn1"]["hostname"]
        all_ip_hosts[data_with_role["nn2_ip"]] = data["nodes"]["nn2"]["hostname"]

        for dn_ip in data_with_role["dn_ips"]:
            all_ip_hosts[dn_ip] = gen_host_name_by_role(dn_ip, "dn")
        data_with_role["all_ip_hosts"] = all_ip_hosts
        self.data_with_role = data_with_role
        # if alias not set, default as cluster_name
        if not self.data["cluster_alias"]:
            self.data_with_role["cluster_alias"] = self.data_with_role["cluster_name"]
