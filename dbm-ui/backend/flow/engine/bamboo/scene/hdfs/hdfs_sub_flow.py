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
from dataclasses import asdict, replace
from typing import Dict, Optional

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.flow.consts import HdfsRoleEnum
from backend.flow.engine.bamboo.scene.common.bigdata_common_sub_flow import new_machine_common_sub_flow
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.hdfs.exec_actuator_script import ExecuteHdfsActuatorScriptComponent
from backend.flow.plugins.components.collections.hdfs.get_hdfs_payload import GetHdfsActPayloadComponent
from backend.flow.plugins.components.collections.hdfs.get_hdfs_resource import GetHdfsResourceComponent
from backend.flow.plugins.components.collections.hdfs.hdfs_db_meta import HdfsDBMetaComponent
from backend.flow.plugins.components.collections.hdfs.trans_flies import TransFileComponent
from backend.flow.utils.hdfs.hdfs_act_playload import HdfsActPayload
from backend.flow.utils.hdfs.hdfs_context_dataclass import ActKwargs
from backend.flow.utils.hdfs.hdfs_flow_data_initializer import (
    get_all_node_ips_in_ticket,
    get_node_ips_in_ticket_by_role,
)

logger = logging.getLogger("flow")


class HdfsOperationFlow(object):
    """
    构建HDFS变更操作流程的常用类，封装扩缩容替换等子流程

    DN 增删不涉及主域名和 HAProxy：存量集群的主域名都已不指向 DN，HAProxy 也都不在 DN 上，
    所以子流程里不安装 HAProxy、不增删主域名记录、也不迁移 extension 表里的 HAProxy 登记。
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
            act_name=_("获取集群部署配置"),
            act_component_code=GetHdfsActPayloadComponent.code,
            kwargs=asdict(act_kwargs),
        )
        # 获取机器资源 trans_data 用于动态传参
        add_dn_sub_pipeline.add_act(
            act_name=_("添加DN获取机器信息"),
            act_component_code=GetHdfsResourceComponent.code,
            kwargs=asdict(act_kwargs),
        )
        # 增加机器初始化子流程
        all_new_ips = get_node_ips_in_ticket_by_role(data, HdfsRoleEnum.DataNode.value)
        common_sub_flow = new_machine_common_sub_flow(
            uid=data["uid"], root_id=self.root_id, bk_cloud_id=data["bk_cloud_id"], new_ips=all_new_ips
        )
        if common_sub_flow:
            add_dn_sub_pipeline.add_sub_pipeline(sub_flow=common_sub_flow)

        # 旧节点也要拿到新的 dbactuator，初始化及之后仍只在新 DN 上执行
        act_kwargs.exec_ip = all_new_ips + data["nn_ips"] + data["dn_ips"]
        add_dn_sub_pipeline.add_act(
            act_name=_("下发hdfs介质包"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
        )
        act_kwargs.exec_ip = all_new_ips
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_sys_init_payload.__name__
        add_dn_sub_pipeline.add_act(
            act_name=_("初始化机器"),
            act_component_code=ExecuteHdfsActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_decompress_package_payload.__name__
        add_dn_sub_pipeline.add_act(
            act_name=_("解压缩文件"),
            act_component_code=ExecuteHdfsActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )
        # 渲染要用 payload 的 host 替换 {{dn_host}}，而同一份 payload 的 host 固定取 exec_ip[0]，
        # 批量下发会让所有机器都写成首台 IP，故按机器逐台下发
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_render_cluster_config_payload.__name__
        render_act_list = []
        for dn_ip in all_new_ips:
            act_kwargs.exec_ip = dn_ip
            render_act_list.append(
                {
                    "act_name": _("渲染集群配置-{}").format(dn_ip),
                    "act_component_code": ExecuteHdfsActuatorScriptComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )
        add_dn_sub_pipeline.add_parallel_acts(acts_list=render_act_list)

        act_kwargs.exec_ip = all_new_ips
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_install_supervisor_payload.__name__
        add_dn_sub_pipeline.add_act(
            act_name=_("安装supervisor"),
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
            act_name=_("刷新节点配置"),
            act_component_code=ExecuteHdfsActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        dn_act_list = []
        for dn_ip in all_new_ips:
            act_kwargs.exec_ip = dn_ip
            act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_install_datanode_payload.__name__
            datanode_act = {
                "act_name": _("安装DataNode-{}").format(dn_ip),
                "act_component_code": ExecuteHdfsActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            dn_act_list.append(datanode_act)
        add_dn_sub_pipeline.add_parallel_acts(acts_list=dn_act_list)

        # 新 DN 不装 HAProxy、不加主域名，原因见类注释
        act_kwargs.exec_ip = all_new_ips
        add_dn_sub_pipeline.add_act(
            act_name=_("添加元数据到DBMeta"), act_component_code=HdfsDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )
        return add_dn_sub_pipeline

    def build_del_dn_sub_flow(self, act_kwargs: ActKwargs, data: dict) -> SubBuilder:
        # sub_flow 缩容DN
        del_dn_sub_pipeline = SubBuilder(root_id=self.root_id, data=data)
        del_dn_sub_pipeline.add_act(
            act_name=_("获取集群部署配置"),
            act_component_code=GetHdfsActPayloadComponent.code,
            kwargs=asdict(act_kwargs),
        )
        # 增删 include/exclude、刷新节点在 NN 上执行，检查退役在 dn_ips[0] 上执行，都依赖新版 dbactuator
        # （legacy_dn_host 等新字段），先下发；只下发 actuator，避免替换场景重复下发完整介质包
        trans_actuator_kwargs = replace(
            act_kwargs,
            exec_ip=list(dict.fromkeys(data["nn_ips"] + data["dn_ips"][:1])),
            file_list=GetFileList(db_type=DBType.Hdfs).hdfs_actuator(),
        )
        del_dn_sub_pipeline.add_act(
            act_name=_("下发dbactuator"),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(trans_actuator_kwargs),
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
            act_name=_("刷新节点配置"),
            act_component_code=ExecuteHdfsActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
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
            act_name=_("刷新节点配置"),
            act_component_code=ExecuteHdfsActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
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
            act_name=_("刷新节点配置"),
            act_component_code=ExecuteHdfsActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 下架 DN 不在主域名里，也不承载 HAProxy，无需摘域名或迁移 HAProxy 登记，原因见类注释
        # 缩容后对机器进行清理
        del_dn_ips = get_node_ips_in_ticket_by_role(data, HdfsRoleEnum.DataNode.value)
        del_dn_ip_acts = []
        for ip in del_dn_ips:
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

        # 包含将机器CC挪到待回收
        del_dn_sub_pipeline.add_act(
            act_name=_("DBMeta删除下架IP"), act_component_code=HdfsDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )
        return del_dn_sub_pipeline

    @staticmethod
    def new_machine_hdfs_flow(root_id: str, act_kwargs: ActKwargs, data: dict) -> SubBuilder:
        # """
        # HDFS集群新节点公共子流程
        # 包括
        #     下发HDFS介质包
        #     初始化机器
        #     解压缩文件
        #     渲染集群配置
        #     安装supervisor
        # 操作
        # """
        hdfs_common_sub_pipeline = SubBuilder(root_id=root_id, data=data)
        # 修改act对应执行的IP
        all_ips = get_all_node_ips_in_ticket(data)
        act_kwargs.exec_ip = all_ips

        hdfs_common_sub_pipeline.add_act(
            act_name=_("下发hdfs介质包"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
        )
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_sys_init_payload.__name__
        hdfs_common_sub_pipeline.add_act(
            act_name=_("初始化机器"),
            act_component_code=ExecuteHdfsActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_decompress_package_payload.__name__
        hdfs_common_sub_pipeline.add_act(
            act_name=_("解压缩文件"),
            act_component_code=ExecuteHdfsActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 渲染要用 payload 的 host 替换 {{dn_host}}，而同一份 payload 的 host 固定取 exec_ip[0]，
        # 批量下发会让所有机器都写成首台 IP，故按机器逐台下发
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_render_cluster_config_payload.__name__
        render_act_list = []
        for ip in all_ips:
            act_kwargs.exec_ip = ip
            render_act_list.append(
                {
                    "act_name": _("渲染集群配置-{}").format(ip),
                    "act_component_code": ExecuteHdfsActuatorScriptComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )
        hdfs_common_sub_pipeline.add_parallel_acts(acts_list=render_act_list)

        act_kwargs.exec_ip = all_ips
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_install_supervisor_payload.__name__
        hdfs_common_sub_pipeline.add_act(
            act_name=_("安装supervisor"),
            act_component_code=ExecuteHdfsActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        return hdfs_common_sub_pipeline
