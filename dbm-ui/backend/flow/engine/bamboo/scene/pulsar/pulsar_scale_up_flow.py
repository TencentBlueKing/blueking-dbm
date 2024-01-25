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
from backend.flow.consts import DnsOpType, MediumFileTypeEnum, PulsarRoleEnum
from backend.flow.engine.bamboo.scene.common.bigdata_common_sub_flow import sa_init_machine_sub_flow
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.pulsar.pulsar_base_flow import PulsarBaseFlow, get_all_node_ips_in_ticket
from backend.flow.plugins.components.collections.pulsar.get_pulsar_payload import GetPulsarActPayloadComponent
from backend.flow.plugins.components.collections.pulsar.get_pulsar_resource import GetPulsarResourceComponent
from backend.flow.plugins.components.collections.pulsar.pulsar_db_meta import PulsarDBMetaComponent
from backend.flow.plugins.components.collections.pulsar.pulsar_dns_manage import PulsarDnsManageComponent
from backend.flow.plugins.components.collections.pulsar.trans_files import TransFileComponent
from backend.flow.utils.pulsar.consts import PULSAR_AUTH_CONF_TARGET_PATH, PULSAR_KEY_PATH_LIST_BROKER
from backend.flow.utils.pulsar.pulsar_context_dataclass import (
    DnsKwargs,
    PulsarActKwargs,
    PulsarApplyContext,
    TransFilesKwargs,
)

logger = logging.getLogger("flow")


class PulsarScaleUpFlow(PulsarBaseFlow):
    """
    构建Pulsar扩容流程
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        :param root_id: 任务流程定义的root_id
        :param data: 单据传递过来的参数列表，字典格式
        """
        super().__init__(root_id, data)

    def scale_up_pulsar_flow(self):
        """
        定义扩容pulsar集群
        :return:
        """
        pulsar_pipeline = Builder(root_id=self.root_id, data=self.base_flow_data)

        trans_files = GetFileList(db_type=DBType.Pulsar)

        act_kwargs = PulsarActKwargs(bk_cloud_id=self.base_flow_data["bk_cloud_id"])
        act_kwargs.set_trans_data_dataclass = PulsarApplyContext.__name__
        act_kwargs.file_list = trans_files.pulsar_apply(db_version=self.base_flow_data["db_version"])
        pulsar_pipeline.add_act(
            act_name=_("获取集群部署配置"), act_component_code=GetPulsarActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )

        # 获取机器资源
        pulsar_pipeline.add_act(
            act_name=_("获取机器信息"), act_component_code=GetPulsarResourceComponent.code, kwargs=asdict(act_kwargs)
        )

        # 增加机器初始化子流程
        all_new_ips = get_all_node_ips_in_ticket(self.base_flow_data)
        pulsar_pipeline.add_sub_pipeline(
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

        act_kwargs.exec_ip = get_all_node_ips_in_ticket(data=self.base_flow_data)
        pulsar_pipeline.add_act(
            act_name=_("下发pulsar介质"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
        )

        # 待扩容节点 安装pulsar common子流程 编排
        sub_pipelines = self.new_nodes_common_sub_flow_list(act_kwargs=act_kwargs, data=self.base_flow_data)

        # 并发执行所有子流程
        pulsar_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        # 安装bookkeeper
        if PulsarRoleEnum.BookKeeper in self.nodes and self.nodes[PulsarRoleEnum.BookKeeper]:
            bookie_act_list = self.new_bookkeeper_act_list(act_kwargs)
            pulsar_pipeline.add_parallel_acts(acts_list=bookie_act_list)

        # 扩容broker 子流程封装
        if PulsarRoleEnum.Broker in self.nodes and self.nodes[PulsarRoleEnum.Broker]:
            # 分发密钥文件到新broker节点
            act_kwargs.file_list = PULSAR_KEY_PATH_LIST_BROKER
            act_kwargs.exec_ip = [node["ip"] for node in self.nodes[PulsarRoleEnum.Broker]]
            trans_file_kwargs = TransFilesKwargs(
                source_ip_list=[self.broker_ips[0]],
                file_type=MediumFileTypeEnum.Server.value,
                file_target_path=PULSAR_AUTH_CONF_TARGET_PATH,
            )
            pulsar_pipeline.add_act(
                act_name=_("分发密钥及token"),
                act_component_code=TransFileComponent.code,
                kwargs={**asdict(act_kwargs), **asdict(trans_file_kwargs)},
            )

            broker_act_list = self.new_broker_act_list(act_kwargs)
            pulsar_pipeline.add_parallel_acts(acts_list=broker_act_list)

            dns_kwargs = DnsKwargs(
                bk_cloud_id=self.base_flow_data["bk_cloud_id"],
                dns_op_type=DnsOpType.CREATE,
                domain_name=self.base_flow_data["domain"],
                dns_op_exec_port=self.base_flow_data["port"],
            )

            pulsar_pipeline.add_act(
                act_name=_("添加集群域名"),
                act_component_code=PulsarDnsManageComponent.code,
                kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
            )

        pulsar_pipeline.add_act(
            act_name=_("更新DBMeta元信息"), act_component_code=PulsarDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )
        pulsar_pipeline.run_pipeline()
