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
from backend.flow.consts import DnsOpType, HdfsRoleEnum, ManagerOpType, ManagerServiceType
from backend.flow.engine.bamboo.scene.common.bigdata_common_sub_flow import new_machine_common_sub_flow
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.hdfs.hdfs_sub_flow import HdfsOperationFlow
from backend.flow.plugins.components.collections.common.bigdata_manager_service import BigdataManagerComponent
from backend.flow.plugins.components.collections.hdfs.exec_actuator_script import ExecuteHdfsActuatorScriptComponent
from backend.flow.plugins.components.collections.hdfs.get_hdfs_payload import GetHdfsActPayloadComponent
from backend.flow.plugins.components.collections.hdfs.get_hdfs_resource import GetHdfsResourceComponent
from backend.flow.plugins.components.collections.hdfs.hdfs_apply_summary import add_hdfs_apply_summary_output_act
from backend.flow.plugins.components.collections.hdfs.hdfs_db_meta import HdfsDBMetaComponent
from backend.flow.plugins.components.collections.hdfs.hdfs_dns_manage import HdfsDnsManageComponent
from backend.flow.plugins.components.collections.hdfs.rewrite_hdfs_config_v2 import WriteHdfsConfigV2Component
from backend.flow.plugins.components.collections.hdfs.write_hdfs_password import WriteHdfsPasswordComponent
from backend.flow.utils.extension_manage import BigdataManagerKwargs
from backend.flow.utils.hdfs.hdfs_act_playload import HdfsActPayload
from backend.flow.utils.hdfs.hdfs_context_dataclass import ActKwargs, DnsKwargs, HdfsApplyContext
from backend.flow.utils.hdfs.hdfs_flow_data_initializer import (
    HdfsFlowDataInitializer,
    get_all_node_ips_in_ticket,
    get_node_ips_in_ticket_by_role,
    get_webui_ip,
)

logger = logging.getLogger("flow")


class HdfsApplyFlowV2(object):
    """
    构建 V2版本hdfs集群申请流程类
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
         @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data
        self.flow_data = HdfsFlowDataInitializer.init_apply_data(self.data)

    def deploy_hdfs_flow(self):
        """
        定义部署 HDFS集群流程
        对比V1版本:
        TODO
        """
        flow_data = HdfsFlowDataInitializer.init_apply_data(ticket_data=self.data)
        # Builder 传参 为封装好角色IP的数据结构
        hdfs_pipeline = Builder(root_id=self.root_id, data=flow_data)
        trans_files = GetFileList(db_type=DBType.Hdfs)

        # 拼接活动节点需要的私有参数
        act_kwargs = ActKwargs(bk_cloud_id=flow_data["bk_cloud_id"])
        act_kwargs.set_trans_data_dataclass = HdfsApplyContext.__name__
        act_kwargs.file_list = trans_files.hdfs_apply(db_version=flow_data["db_version"])

        hdfs_pipeline.add_act(
            act_name=_("获取集群部署配置"), act_component_code=GetHdfsActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )

        # 获取机器资源 当前trans_data仅用于转模块
        hdfs_pipeline.add_act(
            act_name=_("获取机器信息"), act_component_code=GetHdfsResourceComponent.code, kwargs=asdict(act_kwargs)
        )

        # 增加机器初始化子流程
        common_sub_flow = new_machine_common_sub_flow(
            uid=self.data["uid"],
            root_id=self.root_id,
            bk_cloud_id=flow_data["bk_cloud_id"],
            new_ips=get_all_node_ips_in_ticket(flow_data),
        )
        if common_sub_flow:
            hdfs_pipeline.add_sub_pipeline(sub_flow=common_sub_flow)

        hdfs_common_sub_flow = HdfsOperationFlow.new_machine_hdfs_flow(
            root_id=self.root_id, act_kwargs=act_kwargs, data=flow_data
        )
        hdfs_pipeline.add_sub_pipeline(hdfs_common_sub_flow.build_sub_process(sub_name=_("HDFS新机器通用流程")))

        zk_act_list = []
        for zk_ip in get_node_ips_in_ticket_by_role(flow_data, HdfsRoleEnum.ZooKeeper.value):
            act_kwargs.exec_ip = zk_ip
            act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_install_zookeeper_payload.__name__
            zookeeper_act = {
                "act_name": _("安装zookeeper-{}").format(zk_ip),
                "act_component_code": ExecuteHdfsActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            zk_act_list.append(zookeeper_act)
        hdfs_pipeline.add_parallel_acts(acts_list=zk_act_list)

        act_kwargs.exec_ip = get_node_ips_in_ticket_by_role(flow_data, HdfsRoleEnum.JournalNode.value)
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_install_journal_node_payload.__name__
        hdfs_pipeline.add_act(
            act_name=_("安装JournalNode"),
            act_component_code=ExecuteHdfsActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        nn_ips = get_node_ips_in_ticket_by_role(flow_data, HdfsRoleEnum.NameNode.value)
        act_kwargs.exec_ip = nn_ips[0]
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_install_nn1_payload.__name__
        hdfs_pipeline.add_act(
            act_name=_("安装NN1"), act_component_code=ExecuteHdfsActuatorScriptComponent.code, kwargs=asdict(act_kwargs)
        )

        act_kwargs.exec_ip = nn_ips[1]
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_install_nn2_payload.__name__
        hdfs_pipeline.add_act(
            act_name=_("安装NN2"), act_component_code=ExecuteHdfsActuatorScriptComponent.code, kwargs=asdict(act_kwargs)
        )

        act_kwargs.exec_ip = nn_ips
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_install_zkfc_payload.__name__
        hdfs_pipeline.add_act(
            act_name=_("安装ZKFC"), act_component_code=ExecuteHdfsActuatorScriptComponent.code, kwargs=asdict(act_kwargs)
        )

        dn_act_list = []
        for dn_ip in get_node_ips_in_ticket_by_role(flow_data, HdfsRoleEnum.DataNode.value):
            act_kwargs.exec_ip = dn_ip
            act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_install_datanode_payload.__name__
            datanode_act = {
                "act_name": _("安装DataNode-{}").format(dn_ip),
                "act_component_code": ExecuteHdfsActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            dn_act_list.append(datanode_act)
        hdfs_pipeline.add_parallel_acts(acts_list=dn_act_list)

        # 安装HAProxy 是单据里不在NameNode角色，只在Zookeeper角色里的任意一个ip（单据里有且必须多于1个）
        act_kwargs.exec_ip = get_webui_ip(flow_data)
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_install_haproxy_payload.__name__
        hdfs_pipeline.add_act(
            act_name=_("安装HAProxy"),
            act_component_code=ExecuteHdfsActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 插入haproxy实例信息
        manager_kwargs = BigdataManagerKwargs(
            manager_op_type=ManagerOpType.CREATE,
            db_type=DBType.Hdfs,
            service_type=ManagerServiceType.HA_PROXY,
            manager_ip=act_kwargs.exec_ip,
            manager_port=flow_data["http_port"],
        )
        hdfs_pipeline.add_act(
            act_name=_("插入haproxy实例信息"),
            act_component_code=BigdataManagerComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(manager_kwargs)},
        )

        # 添加域名 方法内增加版本兼容
        dns_kwargs = DnsKwargs(
            dns_op_type=DnsOpType.CREATE,
            domain_name=flow_data["domain"],
            dns_op_exec_port=flow_data["rpc_port"],
            bk_cloud_id=flow_data["bk_cloud_id"],
        )
        hdfs_pipeline.add_act(
            act_name=_("添加域名"),
            act_component_code=HdfsDnsManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
        )

        # 集群信息写入dbmeta，监控实例，转移模块
        hdfs_pipeline.add_act(
            act_name=_("添加元数据到DBMeta"), act_component_code=HdfsDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        # 部署完回写dbconfig, 扩容等需要的信息
        hdfs_pipeline.add_act(
            act_name=_("回写HDFS密码服务"),
            act_component_code=WriteHdfsPasswordComponent.code,
            kwargs=asdict(act_kwargs),
        )
        hdfs_pipeline.add_act(
            act_name=_("回写集群部署配置"), act_component_code=WriteHdfsConfigV2Component.code, kwargs=asdict(act_kwargs)
        )

        # 写入集群信息摘要，供前端"执行摘要"展示
        add_hdfs_apply_summary_output_act(
            hdfs_pipeline=hdfs_pipeline,
            bk_biz_id=flow_data["bk_biz_id"],
            domain_name=flow_data["domain"],
            region=flow_data.get("city_code", ""),
            version=flow_data["db_version"],
            rpc_port=flow_data["rpc_port"],
        )

        hdfs_pipeline.run_pipeline()
        return
