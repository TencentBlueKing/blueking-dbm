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
from backend.flow.consts import (
    ES_DEFAULT_INSTANCE_NUM,
    DnsOpType,
    ManagerDefaultPort,
    ManagerOpType,
    ManagerServiceType,
)
from backend.flow.engine.bamboo.scene.common.bigdata_common_sub_flow import sa_init_machine_sub_flow
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.es.es_flow import EsFlow, get_all_node_ips_in_ticket
from backend.flow.plugins.components.collections.common.bigdata_manager_service import (
    BigdataManagerComponent,
    get_manager_ip,
)
from backend.flow.plugins.components.collections.es.es_db_meta import EsMetaComponent
from backend.flow.plugins.components.collections.es.es_dns_manage import EsDnsManageComponent
from backend.flow.plugins.components.collections.es.exec_es_actuator_script import ExecuteEsActuatorScriptComponent
from backend.flow.plugins.components.collections.es.get_es_payload import GetEsActPayloadComponent
from backend.flow.plugins.components.collections.es.get_es_resource import GetEsResourceComponent
from backend.flow.plugins.components.collections.es.trans_files import TransFileComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent as MySQLTransFileComponent
from backend.flow.utils.es.es_act_payload import EsActPayload
from backend.flow.utils.es.es_context_dataclass import DnsKwargs, EsActKwargs, EsApplyContext
from backend.flow.utils.extension_manage import BigdataManagerKwargs
from backend.flow.utils.mysql.mysql_act_dataclass import P2PFileKwargs
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class EsReplaceFlow(EsFlow):
    """
    构建ES替换流程
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        :param root_id: 任务流程定义的root_id
        :param data: 单据传递过来的参数列表，字典格式
        """
        super().__init__(root_id, data)
        self.master_exec_ip = self.master_ips[0]
        self.new_nodes = data["new_nodes"]
        self.old_nodes = data["old_nodes"]
        # 定义证书文件分发的目标路径
        self.cer_target_path = "/data/install/"
        self.file_list = ["/tmp/es_cerfiles.tar.gz"]

    def __get_scale_up_flow_data(self) -> dict:
        flow_data = self.get_flow_base_data()
        flow_data["nodes"] = self.new_nodes
        flow_data["ticket_type"] = TicketType.ES_SCALE_UP.value
        return flow_data

    def __get_shrink_flow_data(self) -> dict:
        flow_data = self.get_flow_base_data()
        flow_data["all_instance_ips"] = self.get_all_node_ips_in_dbmeta()
        flow_data["nodes"] = self.old_nodes
        flow_data["ticket_type"] = TicketType.ES_SHRINK.value
        return flow_data

    def replace_es_flow(self):
        """
        定义替换ES节点
        :return:
        """
        es_pipeline = Builder(root_id=self.root_id, data=self.get_flow_base_data())

        # 扩容子流程
        scale_up_data = self.__get_scale_up_flow_data()
        scale_up_sub_pipeline = SubBuilder(root_id=self.root_id, data=scale_up_data)

        trans_files = GetFileList(db_type=DBType.Es)

        scale_up_act_kwargs = EsActKwargs(scale_up_data["bk_cloud_id"])
        scale_up_act_kwargs.set_trans_data_dataclass = EsApplyContext.__name__
        scale_up_act_kwargs.file_list = trans_files.es_scale_up(db_version=self.db_version)
        scale_up_sub_pipeline.add_act(
            act_name=_("获取扩容流程集群部署配置"),
            act_component_code=GetEsActPayloadComponent.code,
            kwargs=asdict(scale_up_act_kwargs),
        )

        # 获取机器资源
        scale_up_sub_pipeline.add_act(
            act_name=_("获取机器信息"), act_component_code=GetEsResourceComponent.code, kwargs=asdict(scale_up_act_kwargs)
        )

        # 增加机器初始化子流程
        all_new_ips = get_all_node_ips_in_ticket(data=scale_up_data)
        es_pipeline.add_sub_pipeline(
            sub_flow=sa_init_machine_sub_flow(
                uid=self.uid,
                root_id=self.root_id,
                bk_cloud_id=self.bk_cloud_id,
                bk_biz_id=self.bk_biz_id,
                init_ips=all_new_ips,
                idle_check_ips=all_new_ips,
                set_dns_ips=[],
            )
        )

        scale_up_act_kwargs.exec_ip = get_all_node_ips_in_ticket(data=scale_up_data)
        scale_up_sub_pipeline.add_act(
            act_name=_("下发ES介质"), act_component_code=TransFileComponent.code, kwargs=asdict(scale_up_act_kwargs)
        )

        # 原有机器下发dbactuator
        scale_up_act_kwargs.file_list = trans_files.es_disable()
        scale_up_act_kwargs.exec_ip = self.get_all_node_ips_in_dbmeta()
        scale_up_sub_pipeline.add_act(
            act_name=_("下发dbactuator"), act_component_code=TransFileComponent.code, kwargs=asdict(scale_up_act_kwargs)
        )

        # 打包证书
        cer_ip = self.master_exec_ip
        scale_up_act_kwargs.exec_ip = cer_ip
        scale_up_act_kwargs.get_es_payload_func = EsActPayload.get_pack_certificate_payload.__name__
        scale_up_sub_pipeline.add_act(
            act_name=_("打包证书"),
            act_component_code=ExecuteEsActuatorScriptComponent.code,
            kwargs=asdict(scale_up_act_kwargs),
        )

        # 分发证书
        scale_up_sub_pipeline.add_act(
            act_name=_("分发证书"),
            act_component_code=MySQLTransFileComponent.code,
            kwargs=asdict(
                P2PFileKwargs(
                    bk_cloud_id=self.bk_cloud_id,
                    file_list=self.file_list,
                    file_target_path=self.cer_target_path,
                    source_ip_list=[cer_ip],
                    exec_ip=get_all_node_ips_in_ticket(data=scale_up_data),
                )
            ),
        )

        sub_pipelines = []
        for role, role_nodes in scale_up_data["nodes"].items():
            for node in role_nodes:
                sub_pipeline = SubBuilder(root_id=self.root_id, data=scale_up_data)
                ip = node["ip"]
                instance_num = node.get("instance_num", ES_DEFAULT_INSTANCE_NUM)
                # 节点初始化
                scale_up_act_kwargs.get_es_payload_func = EsActPayload.get_sys_init_payload.__name__
                scale_up_act_kwargs.exec_ip = ip
                sub_pipeline.add_act(
                    act_name=_("节点初始化-{}").format(ip),
                    act_component_code=ExecuteEsActuatorScriptComponent.code,
                    kwargs=asdict(scale_up_act_kwargs),
                )

                # 解压缩
                scale_up_act_kwargs.get_es_payload_func = EsActPayload.get_decompress_es_pkg_payload.__name__
                scale_up_act_kwargs.exec_ip = ip
                sub_pipeline.add_act(
                    act_name=_("解压缩介质包-{}").format(ip),
                    act_component_code=ExecuteEsActuatorScriptComponent.code,
                    kwargs=asdict(scale_up_act_kwargs),
                )

                # 安装supervisor
                scale_up_act_kwargs.get_es_payload_func = EsActPayload.get_install_supervisor_payload.__name__
                scale_up_act_kwargs.exec_ip = ip
                sub_pipeline.add_act(
                    act_name=_("安装supervisor-{}").format(ip),
                    act_component_code=ExecuteEsActuatorScriptComponent.code,
                    kwargs=asdict(scale_up_act_kwargs),
                )

                # 安装ElasticSearch
                scale_up_act_kwargs.get_es_payload_func = EsActPayload.get_install_es_payload.__name__
                scale_up_act_kwargs.exec_ip = ip
                scale_up_act_kwargs.es_role = role
                scale_up_act_kwargs.instance_num = instance_num
                sub_pipeline.add_act(
                    act_name=_("安装ES {}-{}节点").format(role, ip),
                    act_component_code=ExecuteEsActuatorScriptComponent.code,
                    kwargs=asdict(scale_up_act_kwargs),
                )

                sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("安装ES {}-{}子流程").format(role, ip)))
        # 并发执行所有子流程
        scale_up_sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        # 添加到DBMeta
        scale_up_sub_pipeline.add_act(
            act_name=_("添加到DBMeta"), act_component_code=EsMetaComponent.code, kwargs=asdict(scale_up_act_kwargs)
        )

        # 添加域名
        dns_kwargs = DnsKwargs(
            bk_cloud_id=scale_up_data["bk_cloud_id"],
            dns_op_type=DnsOpType.UPDATE,
            domain_name=scale_up_data["domain"],
            dns_op_exec_port=scale_up_data["http_port"],
        )
        scale_up_sub_pipeline.add_act(
            act_name=_("更新域名映射"),
            act_component_code=EsDnsManageComponent.code,
            kwargs={**asdict(scale_up_act_kwargs), **asdict(dns_kwargs)},
        )

        # 校验扩容是否成功
        scale_up_act_kwargs.get_es_payload_func = EsActPayload.get_check_nodes_payload.__name__
        scale_up_act_kwargs.exec_ip = self.master_exec_ip
        scale_up_sub_pipeline.add_act(
            act_name=_("校验扩容结果"),
            act_component_code=ExecuteEsActuatorScriptComponent.code,
            kwargs=asdict(scale_up_act_kwargs),
        )

        es_pipeline.add_sub_pipeline(sub_flow=scale_up_sub_pipeline.build_sub_process(sub_name=_("扩容子流程")))

        # 缩容子流程
        shrink_data = self.__get_shrink_flow_data()
        shrink_sub_pipeline = SubBuilder(root_id=self.root_id, data=shrink_data)

        shrink_act_kwargs = EsActKwargs(bk_cloud_id=shrink_data["bk_cloud_id"])
        shrink_act_kwargs.set_trans_data_dataclass = EsApplyContext.__name__
        shrink_act_kwargs.file_list = trans_files.es_shrink()
        shrink_sub_pipeline.add_act(
            act_name=_("获取缩容流程集群部署配置"),
            act_component_code=GetEsActPayloadComponent.code,
            kwargs=asdict(shrink_act_kwargs),
        )

        shrink_act_kwargs.file_list = trans_files.es_shrink()
        shrink_ips = get_all_node_ips_in_ticket(data=shrink_data)
        shrink_act_kwargs.exec_ip = shrink_ips
        shrink_sub_pipeline.add_act(
            act_name=_("下发dbactuator"), act_component_code=TransFileComponent.code, kwargs=asdict(shrink_act_kwargs)
        )

        shrink_act_kwargs.get_es_payload_func = EsActPayload.get_exclude_node_payload.__name__
        shrink_act_kwargs.exec_ip = self.master_exec_ip
        shrink_sub_pipeline.add_act(
            act_name=_("排斥缩容节点"),
            act_component_code=ExecuteEsActuatorScriptComponent.code,
            kwargs=asdict(shrink_act_kwargs),
        )

        # 移除域名映射
        dns_kwargs = DnsKwargs(
            bk_cloud_id=shrink_data["bk_cloud_id"],
            dns_op_type=DnsOpType.RECYCLE_RECORD,
            domain_name=self.domain,
            dns_op_exec_port=self.http_port,
        )
        shrink_sub_pipeline.add_act(
            act_name=_("更新域名映射"),
            act_component_code=EsDnsManageComponent.code,
            kwargs={**asdict(shrink_act_kwargs), **asdict(dns_kwargs)},
        )

        # 检查下架节点上是否安装kibana
        manager_ip = get_manager_ip(
            bk_biz_id=self.bk_biz_id,
            db_type=DBType.Es,
            cluster_name=self.cluster_name,
            service_type=ManagerServiceType.KIBANA,
        )

        if manager_ip in shrink_ips:
            # 安装kibana
            kibana_ip = self.get_node_in_dbmeta_preferred_hot(exclude_ips=shrink_ips)
            shrink_act_kwargs.get_es_payload_func = EsActPayload.get_install_kibana_payload.__name__
            shrink_act_kwargs.exec_ip = kibana_ip
            shrink_sub_pipeline.add_act(
                act_name=_("安装kibana"),
                act_component_code=ExecuteEsActuatorScriptComponent.code,
                kwargs=asdict(shrink_act_kwargs),
            )

            # 更新kibana实例信息
            manager_kwargs = BigdataManagerKwargs(
                manager_op_type=ManagerOpType.UPDATE,
                db_type=DBType.Es,
                service_type=ManagerServiceType.KIBANA,
                manager_ip=kibana_ip,
                manager_port=ManagerDefaultPort.KIBANA,
            )
            shrink_sub_pipeline.add_act(
                act_name=_("更新kibana实例信息"),
                act_component_code=BigdataManagerComponent.code,
                kwargs={**asdict(shrink_act_kwargs), **asdict(manager_kwargs)},
            )

        # 检查shard是否搬完
        shrink_act_kwargs.get_es_payload_func = EsActPayload.get_check_shards_payload.__name__
        shrink_sub_pipeline.add_act(
            act_name=_("校验搬迁状态"),
            act_component_code=ExecuteEsActuatorScriptComponent.code,
            kwargs=asdict(shrink_act_kwargs),
        )

        sub_pipeline = SubBuilder(root_id=self.root_id, data=shrink_data)

        for ip in shrink_ips:
            # 检查是否还有http连接
            shrink_act_kwargs.get_es_payload_func = EsActPayload.get_check_connections_payload.__name__
            shrink_act_kwargs.exec_ip = ip
            sub_pipeline.add_act(
                act_name=_("校验连接状态"),
                act_component_code=ExecuteEsActuatorScriptComponent.code,
                kwargs=asdict(shrink_act_kwargs),
            )

            # 停止节点
            shrink_act_kwargs.get_es_payload_func = EsActPayload.get_stop_process_payload.__name__
            shrink_act_kwargs.exec_ip = ip
            sub_pipeline.add_act(
                act_name=_("停止节点-{}").format(ip),
                act_component_code=ExecuteEsActuatorScriptComponent.code,
                kwargs=asdict(shrink_act_kwargs),
            )
        # 并发执行所有子流程
        shrink_sub_pipeline.add_sub_pipeline(sub_flow=sub_pipeline.build_sub_process(sub_name=_("停止ES子流程")))

        # 清理机器
        clean_machine_acts = []
        for ip in shrink_ips:
            # 清理数据
            shrink_act_kwargs.get_es_payload_func = EsActPayload.get_clean_data_payload.__name__
            shrink_act_kwargs.exec_ip = ip
            clear_machine_act = {
                "act_name": _("节点清理-{}").format(ip),
                "act_component_code": ExecuteEsActuatorScriptComponent.code,
                "kwargs": asdict(shrink_act_kwargs),
            }
            clean_machine_acts.append(clear_machine_act)
        # 并发执行
        shrink_sub_pipeline.add_parallel_acts(acts_list=clean_machine_acts)

        # 清理DBMeta
        shrink_sub_pipeline.add_act(
            act_name=_("清理DBMeta"), act_component_code=EsMetaComponent.code, kwargs=asdict(shrink_act_kwargs)
        )

        # 更新数据节点的master ip
        if self.new_nodes.get("master", []):
            all_instance_ips = shrink_data["all_instance_ips"]
            all_instance_ips.extend(get_all_node_ips_in_ticket(data=scale_up_data))
            # 缩容的机器不需要替换master ip
            all_instance_ips = list(set(all_instance_ips) - set(shrink_ips))

            replace_master_acts = []
            for ip in all_instance_ips:
                shrink_act_kwargs.get_es_payload_func = EsActPayload.get_replace_master_payload.__name__
                shrink_act_kwargs.exec_ip = ip
                replace_master_act = {
                    "act_name": _("{}-替换master ip").format(ip),
                    "act_component_code": ExecuteEsActuatorScriptComponent.code,
                    "kwargs": asdict(shrink_act_kwargs),
                }
                replace_master_acts.append(replace_master_act)
            shrink_sub_pipeline.add_parallel_acts(acts_list=replace_master_acts)

        es_pipeline.add_sub_pipeline(sub_flow=shrink_sub_pipeline.build_sub_process(sub_name=_("缩容子流程")))

        es_pipeline.run_pipeline()
