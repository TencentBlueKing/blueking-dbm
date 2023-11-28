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

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.flow.consts import DnsOpType, ManagerOpType, ManagerServiceType
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.common.bigdata_manager_service import (
    BigdataManagerComponent,
    get_manager_ip,
)
from backend.flow.plugins.components.collections.hdfs.exec_actuator_script import ExecuteHdfsActuatorScriptComponent
from backend.flow.plugins.components.collections.hdfs.get_hdfs_payload import GetHdfsActPayloadComponent
from backend.flow.plugins.components.collections.hdfs.get_hdfs_resource import GetHdfsResourceComponent
from backend.flow.plugins.components.collections.hdfs.hdfs_db_meta import HdfsDBMetaComponent
from backend.flow.plugins.components.collections.hdfs.hdfs_dns_manage import HdfsDnsManageComponent
from backend.flow.plugins.components.collections.hdfs.trans_flies import TransFileComponent
from backend.flow.utils.extension_manage import BigdataManagerKwargs
from backend.flow.utils.hdfs.hdfs_act_playload import HdfsActPayload
from backend.flow.utils.hdfs.hdfs_context_dataclass import ActKwargs, DnsKwargs

logger = logging.getLogger("flow")


class HdfsOperationFlow(object):
    """
    构建HDFS变更操作流程的常用类，封装扩缩容替换等子流程
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

    def build_add_dn_sub_flow(self, act_kwargs: ActKwargs, data: dict) -> SubBuilder:

        add_dn_sub_pipeline = SubBuilder(root_id=self.root_id, data=data)
        add_dn_sub_pipeline.add_act(
            act_name=_("获取集群部署配置"), act_component_code=GetHdfsActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )
        # 获取机器资源 trans_data 用于动态传参
        add_dn_sub_pipeline.add_act(
            act_name=_("添加DN获取机器信息"), act_component_code=GetHdfsResourceComponent.code, kwargs=asdict(act_kwargs)
        )
        act_kwargs.exec_ip = data["new_dn_ips"]
        add_dn_sub_pipeline.add_act(
            act_name=_("下发hdfs介质包"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
        )
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_sys_init_payload.__name__
        add_dn_sub_pipeline.add_act(
            act_name=_("初始化机器"), act_component_code=ExecuteHdfsActuatorScriptComponent.code, kwargs=asdict(act_kwargs)
        )
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_decompress_package_payload.__name__
        add_dn_sub_pipeline.add_act(
            act_name=_("解压缩文件"), act_component_code=ExecuteHdfsActuatorScriptComponent.code, kwargs=asdict(act_kwargs)
        )
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_render_cluster_config_payload.__name__
        add_dn_sub_pipeline.add_act(
            act_name=_("渲染集群配置"), act_component_code=ExecuteHdfsActuatorScriptComponent.code, kwargs=asdict(act_kwargs)
        )
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_install_supervisor_payload.__name__
        add_dn_sub_pipeline.add_act(
            act_name=_("安装supervisor"),
            act_component_code=ExecuteHdfsActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )
        # 旧主机更新hostMapping
        act_kwargs.exec_ip = data["dn_ips"] + data["nn_ips"]
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_update_host_mapping_payload.__name__
        add_dn_sub_pipeline.add_act(
            act_name=_("更新主机映射"),
            act_component_code=ExecuteHdfsActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )
        act_kwargs.exec_ip = data["nn_ips"]
        # 从include增加数据节点
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_add_include_payload.__name__
        add_dn_sub_pipeline.add_act(
            act_name=_("include增加数据节点"),
            act_component_code=ExecuteHdfsActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )
        # 执行 刷新HDFS节点
        act_kwargs.exec_ip = data["nn1_ip"]
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_refresh_nodes_payload.__name__
        add_dn_sub_pipeline.add_act(
            act_name=_("刷新节点配置"), act_component_code=ExecuteHdfsActuatorScriptComponent.code, kwargs=asdict(act_kwargs)
        )

        act_kwargs.exec_ip = data["new_dn_ips"]
        dn_act_list = []
        for dn_ip in data["new_dn_ips"]:
            act_kwargs.exec_ip = dn_ip
            act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_install_datanode_payload.__name__
            datanode_act = {
                "act_name": _("安装DataNode-{}").format(dn_ip),
                "act_component_code": ExecuteHdfsActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            dn_act_list.append(datanode_act)
        add_dn_sub_pipeline.add_parallel_acts(acts_list=dn_act_list)

        act_kwargs.exec_ip = data["new_dn_ips"]
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_install_haproxy_payload.__name__
        add_dn_sub_pipeline.add_act(
            act_name=_("安装HAProxy"),
            act_component_code=ExecuteHdfsActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )
        # 添加新的DN到域名
        dns_kwargs = DnsKwargs(
            dns_op_type=DnsOpType.CREATE,
            domain_name=data["domain"],
            dns_op_exec_port=data["rpc_port"],
            bk_cloud_id=data["bk_cloud_id"],
        )
        add_dn_sub_pipeline.add_act(
            act_name=_("添加新DN到域名"),
            act_component_code=HdfsDnsManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
        )
        add_dn_sub_pipeline.add_act(
            act_name=_("添加元数据到DBMeta"), act_component_code=HdfsDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )
        return add_dn_sub_pipeline

    def build_del_dn_sub_flow(self, act_kwargs: ActKwargs, data: dict) -> SubBuilder:
        # sub_flow 缩容DN
        del_dn_sub_pipeline = SubBuilder(root_id=self.root_id, data=data)
        del_dn_sub_pipeline.add_act(
            act_name=_("获取集群部署配置"), act_component_code=GetHdfsActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )
        act_kwargs.exec_ip = data["nn_ips"]
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_add_exclude_payload.__name__
        del_dn_sub_pipeline.add_act(
            act_name=_("添加数据节点到exclude"),
            act_component_code=ExecuteHdfsActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        act_kwargs.exec_ip = data["nn1_ip"]
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_refresh_nodes_payload.__name__
        del_dn_sub_pipeline.add_act(
            act_name=_("刷新节点配置"), act_component_code=ExecuteHdfsActuatorScriptComponent.code, kwargs=asdict(act_kwargs)
        )
        # 访问某一台DN节点的代理NN WEB服务
        act_kwargs.exec_ip = data["dn_ips"][0]
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_check_decommission_payload.__name__
        del_dn_sub_pipeline.add_act(
            act_name=_("检查节点退役信息"),
            act_component_code=ExecuteHdfsActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 从include剔除数据节点
        act_kwargs.exec_ip = data["nn_ips"]
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_remove_include_payload.__name__
        del_dn_sub_pipeline.add_act(
            act_name=_("include剔除数据节点"),
            act_component_code=ExecuteHdfsActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )
        # 执行 刷新HDFS节点
        act_kwargs.exec_ip = data["nn1_ip"]
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_refresh_nodes_payload.__name__
        del_dn_sub_pipeline.add_act(
            act_name=_("刷新节点配置"), act_component_code=ExecuteHdfsActuatorScriptComponent.code, kwargs=asdict(act_kwargs)
        )

        # 从exclude剔除数据节点
        act_kwargs.exec_ip = data["nn_ips"]
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_remove_exclude_payload.__name__
        del_dn_sub_pipeline.add_act(
            act_name=_("exclude剔除数据节点"),
            act_component_code=ExecuteHdfsActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )
        # 执行 刷新HDFS节点
        act_kwargs.exec_ip = data["nn1_ip"]
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_refresh_nodes_payload.__name__
        del_dn_sub_pipeline.add_act(
            act_name=_("刷新节点配置"), act_component_code=ExecuteHdfsActuatorScriptComponent.code, kwargs=asdict(act_kwargs)
        )

        # 检查下架节点上是否安装haproxy
        manager_ip = get_manager_ip(
            bk_biz_id=data["bk_biz_id"],
            db_type=DBType.Hdfs,
            cluster_name=data["cluster_name"],
            service_type=ManagerServiceType.HA_PROXY,
        )
        if manager_ip in data["del_dn_ips"]:
            # 更新haproxy实例信息
            manager_kwargs = BigdataManagerKwargs(
                manager_op_type=ManagerOpType.UPDATE,
                db_type=DBType.Hdfs,
                service_type=ManagerServiceType.HA_PROXY,
                manager_ip=data["remain_dn_ips"][0],
                manager_port=data["http_port"],
            )
            del_dn_sub_pipeline.add_act(
                act_name=_("更新haproxy实例信息"),
                act_component_code=BigdataManagerComponent.code,
                kwargs={**asdict(act_kwargs), **asdict(manager_kwargs)},
            )

        # 缩容后对机器进行清理
        del_dn_ip_acts = []
        for ip in data["del_dn_ips"]:
            # 停止进程 + 数据清理
            act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_data_clean_payload.__name__
            act_kwargs.exec_ip = ip
            act = {
                "act_name": _("HDFS集群节点清理-{}").format(ip),
                "act_component_code": ExecuteHdfsActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            del_dn_ip_acts.append(act)

        del_dn_sub_pipeline.add_parallel_acts(acts_list=del_dn_ip_acts)

        dns_kwargs = DnsKwargs(
            dns_op_type=DnsOpType.UPDATE,
            domain_name=data["domain"],
            dns_op_exec_port=data["rpc_port"],
            bk_cloud_id=data["bk_cloud_id"],
        )
        del_dn_sub_pipeline.add_act(
            act_name=_("更新域名"),
            act_component_code=HdfsDnsManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
        )

        # 包含将机器CC挪到待回收
        del_dn_sub_pipeline.add_act(
            act_name=_("DBMeta删除下架IP"), act_component_code=HdfsDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )
        return del_dn_sub_pipeline
