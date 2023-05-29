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
from backend.flow.consts import DnsOpType, ManagerDefaultPort, ManagerOpType, ManagerServiceType
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
from backend.flow.plugins.components.collections.es.trans_files import TransFileComponent
from backend.flow.utils.es.es_act_payload import EsActPayload
from backend.flow.utils.es.es_context_dataclass import DnsKwargs, EsActKwargs, EsApplyContext
from backend.flow.utils.extension_manage import BigdataManagerKwargs

logger = logging.getLogger("flow")


class EsShrinkFlow(EsFlow):
    """
    构建ES缩容流程
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        :param root_id: 任务流程定义的root_id
        :param data: 单据传递过来的参数列表，字典格式
        """
        super().__init__(root_id, data)
        self.master_exec_ip = self.master_ips[0]

    def __get_flow_data(self) -> dict:
        flow_data = self.get_flow_base_data()
        flow_data["nodes"] = self.nodes
        flow_data["master_exec_ip"] = self.master_exec_ip
        return flow_data

    def shrink_es_flow(self):
        """
        定义缩容ES集群
        :return:
        """
        shrink_data = self.__get_flow_data()
        es_pipeline = Builder(root_id=self.root_id, data=shrink_data)

        trans_files = GetFileList(db_type=DBType.Es)

        act_kwargs = EsActKwargs(bk_cloud_id=self.bk_cloud_id)
        act_kwargs.set_trans_data_dataclass = EsApplyContext.__name__
        act_kwargs.file_list = trans_files.es_shrink()
        es_pipeline.add_act(
            act_name=_("获取集群部署配置"), act_component_code=GetEsActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )

        # 获取机器资源
        """es_pipeline.add_act(
            act_name="获取机器信息", act_component_code=GetEsResourceComponent.code, kwargs=asdict(act_kwargs)
        )
        """
        shrink_ips = get_all_node_ips_in_ticket(data=shrink_data)
        act_kwargs.exec_ip = shrink_ips
        act_kwargs.exec_ip.append(self.master_exec_ip)
        es_pipeline.add_act(
            act_name=_("下发ES介质"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
        )

        act_kwargs.get_es_payload_func = EsActPayload.get_exclude_node_payload.__name__
        act_kwargs.exec_ip = self.master_exec_ip
        es_pipeline.add_act(
            act_name=_("排斥缩容节点"),
            act_component_code=ExecuteEsActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 移除域名映射
        dns_kwargs = DnsKwargs(
            bk_cloud_id=self.bk_cloud_id,
            dns_op_type=DnsOpType.RECYCLE_RECORD,
            domain_name=self.domain,
            dns_op_exec_port=self.http_port,
        )
        es_pipeline.add_act(
            act_name=_("更新域名映射"),
            act_component_code=EsDnsManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
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
            act_kwargs.get_es_payload_func = EsActPayload.get_install_kibana_payload.__name__
            act_kwargs.exec_ip = kibana_ip
            es_pipeline.add_act(
                act_name=_("安装kibana"),
                act_component_code=ExecuteEsActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # 更新kibana实例信息
            manager_kwargs = BigdataManagerKwargs(
                manager_op_type=ManagerOpType.UPDATE,
                db_type=DBType.Es,
                service_type=ManagerServiceType.KIBANA,
                manager_ip=kibana_ip,
                manager_port=ManagerDefaultPort.KIBANA,
            )
            es_pipeline.add_act(
                act_name=_("更新kibana实例信息"),
                act_component_code=BigdataManagerComponent.code,
                kwargs={**asdict(act_kwargs), **asdict(manager_kwargs)},
            )

        # 检查shard是否搬完
        act_kwargs.get_es_payload_func = EsActPayload.get_check_shards_payload.__name__
        es_pipeline.add_act(
            act_name=_("校验搬迁状态"), act_component_code=ExecuteEsActuatorScriptComponent.code, kwargs=asdict(act_kwargs)
        )

        sub_pipelines = []
        for ip in get_all_node_ips_in_ticket(data=shrink_data):
            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.__get_flow_data())

            # 检查是否还有http连接
            act_kwargs.get_es_payload_func = EsActPayload.get_check_connections_payload.__name__
            act_kwargs.exec_ip = ip
            sub_pipeline.add_act(
                act_name=_("校验连接状态"),
                act_component_code=ExecuteEsActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # 停止节点
            act_kwargs.get_es_payload_func = EsActPayload.get_stop_process_payload.__name__
            act_kwargs.exec_ip = ip
            sub_pipeline.add_act(
                act_name=_("停止节点-{}").format(ip),
                act_component_code=ExecuteEsActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )
            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("停止ES-{}子流程").format(ip)))
        # 并发执行所有子流程
        es_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        # 清理机器
        clean_data_acts = []
        for ip in get_all_node_ips_in_ticket(data=shrink_data):
            # 清理数据
            act_kwargs.get_es_payload_func = EsActPayload.get_clean_data_payload.__name__
            act_kwargs.exec_ip = ip
            clean_data_act = {
                "act_name": _("节点清理-{}").format(ip),
                "act_component_code": ExecuteEsActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            clean_data_acts.append(clean_data_act)
        es_pipeline.add_parallel_acts(acts_list=clean_data_acts)

        # 清理DBMeta
        es_pipeline.add_act(act_name=_("清理DBMeta"), act_component_code=EsMetaComponent.code, kwargs=asdict(act_kwargs))

        es_pipeline.run_pipeline()
