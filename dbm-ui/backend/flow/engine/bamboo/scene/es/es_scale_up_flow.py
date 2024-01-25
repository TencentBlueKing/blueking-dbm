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
from backend.flow.consts import ES_DEFAULT_INSTANCE_NUM, DnsOpType
from backend.flow.engine.bamboo.scene.common.bigdata_common_sub_flow import sa_init_machine_sub_flow
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.es.es_flow import EsFlow, get_all_node_ips_in_ticket
from backend.flow.plugins.components.collections.es.es_db_meta import EsMetaComponent
from backend.flow.plugins.components.collections.es.es_dns_manage import EsDnsManageComponent
from backend.flow.plugins.components.collections.es.exec_es_actuator_script import ExecuteEsActuatorScriptComponent
from backend.flow.plugins.components.collections.es.get_es_payload import GetEsActPayloadComponent
from backend.flow.plugins.components.collections.es.get_es_resource import GetEsResourceComponent
from backend.flow.plugins.components.collections.es.trans_files import TransFileComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent as MySQLTransFileComponent
from backend.flow.utils.es.es_act_payload import EsActPayload
from backend.flow.utils.es.es_context_dataclass import DnsKwargs, EsActKwargs, EsApplyContext
from backend.flow.utils.mysql.mysql_act_dataclass import P2PFileKwargs

logger = logging.getLogger("flow")


class EsScaleUpFlow(EsFlow):
    """
    构建ES扩容流程
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        :param root_id: 任务流程定义的root_id
        :param data: 单据传递过来的参数列表，字典格式
        """
        super().__init__(root_id, data)
        self.master_exec_ip = self.master_ips[0]

        # 定义证书文件分发的目标路径
        self.cer_target_path = "/data/install/"
        self.file_list = ["/tmp/es_cerfiles.tar.gz"]

    def __get_flow_data(self) -> dict:
        flow_data = self.get_flow_base_data()
        flow_data["nodes"] = self.nodes
        return flow_data

    def scale_up_es_flow(self):
        """
        定义扩容ES集群
        :return:
        """
        scale_up_data = self.__get_flow_data()
        es_pipeline = Builder(root_id=self.root_id, data=scale_up_data)

        trans_files = GetFileList(db_type=DBType.Es)

        act_kwargs = EsActKwargs(bk_cloud_id=self.bk_cloud_id)
        act_kwargs.set_trans_data_dataclass = EsApplyContext.__name__
        act_kwargs.file_list = trans_files.es_scale_up(db_version=self.db_version)
        es_pipeline.add_act(
            act_name=_("获取集群部署配置"), act_component_code=GetEsActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )

        # 获取机器资源
        es_pipeline.add_act(
            act_name=_("获取机器信息"), act_component_code=GetEsResourceComponent.code, kwargs=asdict(act_kwargs)
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

        act_kwargs.exec_ip = get_all_node_ips_in_ticket(data=scale_up_data)
        es_pipeline.add_act(
            act_name=_("下发ES介质"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
        )

        # 原有机器下发dbactuator
        act_kwargs.file_list = trans_files.es_disable()
        act_kwargs.exec_ip = self.get_all_node_ips_in_dbmeta()
        es_pipeline.add_act(
            act_name=_("下发dbactuator"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
        )

        # 打包证书
        cer_ip = self.master_exec_ip
        act_kwargs.exec_ip = cer_ip
        act_kwargs.get_es_payload_func = EsActPayload.get_pack_certificate_payload.__name__
        es_pipeline.add_act(
            act_name=_("打包证书"), act_component_code=ExecuteEsActuatorScriptComponent.code, kwargs=asdict(act_kwargs)
        )

        # 分发证书
        es_pipeline.add_act(
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
        for role, role_nodes in self.nodes.items():
            for node in role_nodes:
                sub_pipeline = SubBuilder(root_id=self.root_id, data=self.get_flow_base_data())
                ip = node["ip"]
                instance_num = node.get("instance_num", ES_DEFAULT_INSTANCE_NUM)
                # 节点初始化
                act_kwargs.get_es_payload_func = EsActPayload.get_sys_init_payload.__name__
                act_kwargs.exec_ip = ip
                sub_pipeline.add_act(
                    act_name=_("节点初始化-{}").format(ip),
                    act_component_code=ExecuteEsActuatorScriptComponent.code,
                    kwargs=asdict(act_kwargs),
                )

                # 解压缩
                act_kwargs.get_es_payload_func = EsActPayload.get_decompress_es_pkg_payload.__name__
                act_kwargs.exec_ip = ip
                sub_pipeline.add_act(
                    act_name=_("解压缩介质包-{}").format(ip),
                    act_component_code=ExecuteEsActuatorScriptComponent.code,
                    kwargs=asdict(act_kwargs),
                )

                # 安装supervisor
                act_kwargs.get_es_payload_func = EsActPayload.get_install_supervisor_payload.__name__
                act_kwargs.exec_ip = ip
                sub_pipeline.add_act(
                    act_name=_("安装supervisor-{}").format(ip),
                    act_component_code=ExecuteEsActuatorScriptComponent.code,
                    kwargs=asdict(act_kwargs),
                )

                # 安装ElasticSearch
                act_kwargs.get_es_payload_func = EsActPayload.get_install_es_payload.__name__
                act_kwargs.exec_ip = ip
                act_kwargs.es_role = role
                act_kwargs.instance_num = instance_num
                sub_pipeline.add_act(
                    act_name=_("安装ES {}-{}节点").format(role, ip),
                    act_component_code=ExecuteEsActuatorScriptComponent.code,
                    kwargs=asdict(act_kwargs),
                )

                sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("安装ES {}-{}子流程").format(role, ip)))
        # 并发执行所有子流程
        es_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        # 添加到DBMeta
        es_pipeline.add_act(
            act_name=_("添加到DBMeta"), act_component_code=EsMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        # 添加域名
        dns_kwargs = DnsKwargs(
            bk_cloud_id=self.bk_cloud_id,
            dns_op_type=DnsOpType.UPDATE,
            domain_name=self.domain,
            dns_op_exec_port=self.http_port,
        )
        es_pipeline.add_act(
            act_name=_("更新域名映射"),
            act_component_code=EsDnsManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
        )

        es_pipeline.run_pipeline()
