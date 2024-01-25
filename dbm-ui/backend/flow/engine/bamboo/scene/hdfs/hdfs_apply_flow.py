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
from backend.db_meta.enums import ClusterType
from backend.flow.consts import DnsOpType, HdfsRoleEnum, ManagerOpType, ManagerServiceType
from backend.flow.engine.bamboo.scene.common.bigdata_common_sub_flow import sa_init_machine_sub_flow
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.hdfs.exceptions import ManualMachineCountException
from backend.flow.plugins.components.collections.common.bigdata_manager_service import BigdataManagerComponent
from backend.flow.plugins.components.collections.hdfs.exec_actuator_script import ExecuteHdfsActuatorScriptComponent
from backend.flow.plugins.components.collections.hdfs.get_hdfs_payload import GetHdfsActPayloadComponent
from backend.flow.plugins.components.collections.hdfs.get_hdfs_resource import GetHdfsResourceComponent
from backend.flow.plugins.components.collections.hdfs.hdfs_db_meta import HdfsDBMetaComponent
from backend.flow.plugins.components.collections.hdfs.hdfs_dns_manage import HdfsDnsManageComponent
from backend.flow.plugins.components.collections.hdfs.rewrite_hdfs_config import WriteBackHdfsConfigComponent
from backend.flow.plugins.components.collections.hdfs.trans_flies import TransFileComponent
from backend.flow.utils.extension_manage import BigdataManagerKwargs
from backend.flow.utils.hdfs.hdfs_act_playload import HdfsActPayload, gen_host_name_by_role
from backend.flow.utils.hdfs.hdfs_context_dataclass import ActKwargs, DnsKwargs, HdfsApplyContext

logger = logging.getLogger("flow")


class HdfsApplyFlow(object):
    """
    构建hdfs集群申请流程的抽象类
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

    def deploy_hdfs_flow(self):
        """
        定义部署hdfs集群
        """
        # Builder 传参 为封装好角色IP的数据结构
        hdfs_pipeline = Builder(root_id=self.root_id, data=self.data_with_role)
        trans_files = GetFileList(db_type=DBType.Hdfs)

        # 拼接活动节点需要的私有参数
        act_kwargs = ActKwargs(bk_cloud_id=self.data["bk_cloud_id"])
        act_kwargs.set_trans_data_dataclass = HdfsApplyContext.__name__
        act_kwargs.file_list = trans_files.hdfs_apply(db_version=self.data["db_version"])

        # 需要将配置项写入
        act_kwargs.is_update_trans_data = True

        hdfs_pipeline.add_act(
            act_name=_("获取集群部署配置"), act_component_code=GetHdfsActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )

        # 获取机器资源 当前trans_data仅用于转模块
        hdfs_pipeline.add_act(
            act_name=_("获取机器信息"), act_component_code=GetHdfsResourceComponent.code, kwargs=asdict(act_kwargs)
        )

        # 增加机器初始化子流程
        hdfs_pipeline.add_sub_pipeline(
            sub_flow=sa_init_machine_sub_flow(
                uid=self.data_with_role["uid"],
                root_id=self.root_id,
                bk_cloud_id=self.data_with_role["bk_cloud_id"],
                bk_biz_id=self.data["bk_biz_id"],
                init_ips=self.data_with_role["all_ips"],
                idle_check_ips=self.data_with_role["all_ips"],
                set_dns_ips=[],
            )
        )

        # 修改act对应执行的IP
        act_kwargs.exec_ip = self.data_with_role["all_ips"]
        hdfs_pipeline.add_act(
            act_name=_("下发hdfs介质包"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
        )
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_sys_init_payload.__name__
        hdfs_pipeline.add_act(
            act_name=_("初始化机器"), act_component_code=ExecuteHdfsActuatorScriptComponent.code, kwargs=asdict(act_kwargs)
        )

        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_decompress_package_payload.__name__
        hdfs_pipeline.add_act(
            act_name=_("解压缩文件"), act_component_code=ExecuteHdfsActuatorScriptComponent.code, kwargs=asdict(act_kwargs)
        )

        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_render_cluster_config_payload.__name__
        hdfs_pipeline.add_act(
            act_name=_("渲染集群配置"), act_component_code=ExecuteHdfsActuatorScriptComponent.code, kwargs=asdict(act_kwargs)
        )

        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_install_supervisor_payload.__name__
        hdfs_pipeline.add_act(
            act_name=_("安装supervisor"),
            act_component_code=ExecuteHdfsActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        zk_act_list = []
        for zk_ip in self.data_with_role["zk_ips"]:
            act_kwargs.exec_ip = zk_ip
            act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_install_zookeeper_payload.__name__
            zookeeper_act = {
                "act_name": _("安装zookeeper-{}").format(zk_ip),
                "act_component_code": ExecuteHdfsActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            zk_act_list.append(zookeeper_act)
        hdfs_pipeline.add_parallel_acts(acts_list=zk_act_list)

        act_kwargs.exec_ip = self.data_with_role["jn_ips"]
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_install_journal_node_payload.__name__
        hdfs_pipeline.add_act(
            act_name=_("安装JournalNode"),
            act_component_code=ExecuteHdfsActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        act_kwargs.exec_ip = self.data_with_role["nn1_ip"]
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_install_nn1_payload.__name__
        hdfs_pipeline.add_act(
            act_name=_("安装NN1"), act_component_code=ExecuteHdfsActuatorScriptComponent.code, kwargs=asdict(act_kwargs)
        )

        act_kwargs.exec_ip = self.data_with_role["nn2_ip"]
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_install_nn2_payload.__name__
        hdfs_pipeline.add_act(
            act_name=_("安装NN2"), act_component_code=ExecuteHdfsActuatorScriptComponent.code, kwargs=asdict(act_kwargs)
        )

        act_kwargs.exec_ip = (self.data_with_role["nn1_ip"], self.data_with_role["nn2_ip"])
        act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_install_zkfc_payload.__name__
        hdfs_pipeline.add_act(
            act_name=_("安装ZKFC"), act_component_code=ExecuteHdfsActuatorScriptComponent.code, kwargs=asdict(act_kwargs)
        )

        dn_act_list = []
        for dn_ip in self.data_with_role["dn_ips"]:
            act_kwargs.exec_ip = dn_ip
            act_kwargs.get_hdfs_payload_func = HdfsActPayload.get_install_datanode_payload.__name__
            datanode_act = {
                "act_name": _("安装DataNode-{}").format(dn_ip),
                "act_component_code": ExecuteHdfsActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            dn_act_list.append(datanode_act)
        hdfs_pipeline.add_parallel_acts(acts_list=dn_act_list)

        act_kwargs.exec_ip = self.data_with_role["dn_ips"]
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
            manager_ip=self.data_with_role["dn_ips"][0],
            manager_port=self.data_with_role["http_port"],
        )
        hdfs_pipeline.add_act(
            act_name=_("插入haproxy实例信息"),
            act_component_code=BigdataManagerComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(manager_kwargs)},
        )

        # 添加域名
        dns_kwargs = DnsKwargs(
            dns_op_type=DnsOpType.CREATE,
            domain_name=self.data["domain"],
            dns_op_exec_port=self.data["rpc_port"],
            bk_cloud_id=self.data["bk_cloud_id"],
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
            act_name=_("回写集群部署配置"), act_component_code=WriteBackHdfsConfigComponent.code, kwargs=asdict(act_kwargs)
        )

        hdfs_pipeline.run_pipeline()

    def __init_data_with_role(self, data: Optional[Dict]):
        # 对手动部署HDFS集群的单据 对角色对应IP做初始化，后续用作静态传参
        data_with_role = copy.deepcopy(data)

        manual_nn_count = len(data["nodes"][HdfsRoleEnum.NameNode])
        if manual_nn_count != 2:
            logger.error(_("NameNode主机数不为2"))
            raise ManualMachineCountException(hdfs_role=HdfsRoleEnum.NameNode, machine_count=manual_nn_count)
        manual_zk_count = len(data["nodes"][HdfsRoleEnum.ZooKeeper])
        if manual_zk_count != 3:
            logger.error(_("ZooKeeper主机数不为3"))
            raise ManualMachineCountException(hdfs_role=HdfsRoleEnum.ZooKeeper, machine_count=manual_zk_count)
        manual_dn_count = len(data["nodes"][HdfsRoleEnum.DataNode])
        if manual_dn_count < 2:
            logger.error(_("DataNode主机数少于2"))
            raise ManualMachineCountException(hdfs_role=HdfsRoleEnum.DataNode, machine_count=manual_dn_count)

        data_with_role["nn1_ip"] = data["nodes"][HdfsRoleEnum.NameNode][0]["ip"]
        data_with_role["nn2_ip"] = data["nodes"][HdfsRoleEnum.NameNode][1]["ip"]

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
        all_ip_hosts[data_with_role["nn1_ip"]] = gen_host_name_by_role(data_with_role["nn1_ip"], "nn1")
        all_ip_hosts[data_with_role["nn2_ip"]] = gen_host_name_by_role(data_with_role["nn2_ip"], "nn2")
        zk_count = 0
        for zk_ip in data_with_role["zk_ips"]:
            if zk_ip not in all_ip_hosts:
                all_ip_hosts[zk_ip] = gen_host_name_by_role(zk_ip, f"zk{zk_count}")
                zk_count += 1
            else:
                logger.info(_("复用NN主机 {} 作为ZK").format(zk_ip))
        for dn_ip in data_with_role["dn_ips"]:
            all_ip_hosts[dn_ip] = gen_host_name_by_role(dn_ip, "dn")
        data_with_role["all_ip_hosts"] = all_ip_hosts
        self.data_with_role = data_with_role
        # if alias not set, default as cluster_name
        if not self.data["cluster_alias"]:
            self.data_with_role["cluster_alias"] = self.data_with_role["cluster_name"]
