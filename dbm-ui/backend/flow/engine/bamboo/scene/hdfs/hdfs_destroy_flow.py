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
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.flow.consts import DnsOpType, ManagerOpType, ManagerServiceType
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.common.bigdata_manager_service import BigdataManagerComponent
from backend.flow.plugins.components.collections.hdfs.check_cluster_status import CheckClusterStatusComponent
from backend.flow.plugins.components.collections.hdfs.exec_actuator_script import ExecuteHdfsActuatorScriptComponent
from backend.flow.plugins.components.collections.hdfs.get_hdfs_payload import GetHdfsActPayloadComponent
from backend.flow.plugins.components.collections.hdfs.hdfs_db_meta import HdfsDBMetaComponent
from backend.flow.plugins.components.collections.hdfs.hdfs_dns_manage import HdfsDnsManageComponent
from backend.flow.plugins.components.collections.hdfs.trans_flies import TransFileComponent
from backend.flow.utils.extension_manage import BigdataManagerKwargs
from backend.flow.utils.hdfs.hdfs_act_playload import HdfsActPayload
from backend.flow.utils.hdfs.hdfs_context_dataclass import ActKwargs, DnsKwargs, HdfsApplyContext
from backend.flow.utils.hdfs.hdfs_flow_data_initializer import HdfsFlowDataInitializer, get_all_node_ips_in_dbmeta

logger = logging.getLogger("flow")


class HdfsDestroyFlow(object):
    """
    构建HDFS集群禁用流程
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        :param root_id: 任务流程定义的root_id
        :param data: 单据传递过来的参数列表，字典格式
        """
        self.root_id = root_id
        self.data = data

    def destroy_hdfs_flow(self):
        """
        禁用HDFS集群
        """
        flow_data = HdfsFlowDataInitializer.init_destroy_data(self.data)
        # Builder 传参 为封装好角色IP的数据结构
        hdfs_pipeline = Builder(root_id=self.root_id, data=flow_data)
        trans_files = GetFileList(db_type=DBType.Hdfs)

        # 拼接活动节点需要的私有参数
        act_kwargs = ActKwargs(bk_cloud_id=flow_data["bk_cloud_id"])
        act_kwargs.set_trans_data_dataclass = HdfsApplyContext.__name__
        act_kwargs.file_list = trans_files.hdfs_actuator()

        hdfs_pipeline.add_act(
            act_name=_("检查集群状态"), act_component_code=CheckClusterStatusComponent.code, kwargs=asdict(act_kwargs)
        )

        hdfs_pipeline.add_act(
            act_name=_("获取集群部署配置"), act_component_code=GetHdfsActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )
        # 从cluster中获取所有IP
        all_ips = get_all_node_ips_in_dbmeta(cluster_id=flow_data["cluster_id"])
        act_kwargs.exec_ip = all_ips
        hdfs_pipeline.add_act(
            act_name=_("下发hdfs actuator"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
        )

        all_ip_acts = []
        for ip in all_ips:
            # 停止进程
            act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_data_clean_payload.__name__
            act_kwargs.exec_ip = ip
            act = {
                "act_name": _("HDFS集群节点清理-{}").format(ip),
                "act_component_code": ExecuteHdfsActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            all_ip_acts.append(act)

        hdfs_pipeline.add_parallel_acts(acts_list=all_ip_acts)

        # 清理haproxy
        manager_kwargs = BigdataManagerKwargs(
            manager_op_type=ManagerOpType.DELETE,
            db_type=DBType.Hdfs,
            service_type=ManagerServiceType.HA_PROXY,
        )
        hdfs_pipeline.add_act(
            act_name=_("删除haproxy实例信息"),
            act_component_code=BigdataManagerComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(manager_kwargs)},
        )

        # 清理域名
        dns_kwargs = DnsKwargs(
            dns_op_type=DnsOpType.CLUSTER_DELETE,
            bk_cloud_id=flow_data["bk_cloud_id"],
            dns_op_exec_port=flow_data["rpc_port"],
        )
        hdfs_pipeline.add_act(
            act_name=_("删除域名"),
            act_component_code=HdfsDnsManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
        )

        # 修改DBMeta + 将机器挪到空闲机模块
        hdfs_pipeline.add_act(
            act_name=_("修改Meta"), act_component_code=HdfsDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        hdfs_pipeline.run_pipeline()
