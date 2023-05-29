import logging.config
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.flow.consts import DnsOpType, PulsarRoleEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.pulsar.pulsar_base_flow import get_all_node_ips_in_ticket
from backend.flow.engine.bamboo.scene.pulsar.pulsar_sub_flow import PulsarOperationFlow
from backend.flow.plugins.components.collections.pulsar.exec_actuator_script import (
    ExecutePulsarActuatorScriptComponent,
)
from backend.flow.plugins.components.collections.pulsar.get_pulsar_payload import GetPulsarActPayloadComponent
from backend.flow.plugins.components.collections.pulsar.get_pulsar_resource import GetPulsarResourceComponent
from backend.flow.plugins.components.collections.pulsar.pulsar_db_meta import PulsarDBMetaComponent
from backend.flow.plugins.components.collections.pulsar.pulsar_dns_manage import PulsarDnsManageComponent
from backend.flow.plugins.components.collections.pulsar.trans_files import TransFileComponent
from backend.flow.utils.pulsar.pulsar_act_payload import PulsarActPayload
from backend.flow.utils.pulsar.pulsar_context_dataclass import DnsKwargs, PulsarActKwargs, PulsarApplyContext

logger = logging.getLogger("flow")


class PulsarShrinkFlow(PulsarOperationFlow):
    """
    构建Pulsar缩容流程的抽象类
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        super().__init__(root_id, data)
        self.data = data

    def shrink_pulsar_flow(self):
        """
        定义部署Pulsar集群
        """

        pulsar_pipeline = Builder(root_id=self.root_id, data=self.base_flow_data)
        trans_files = GetFileList(db_type=DBType.Pulsar)
        # 拼接活动节点需要的私有参数
        act_kwargs = PulsarActKwargs(bk_cloud_id=self.base_flow_data["bk_cloud_id"])
        act_kwargs.set_trans_data_dataclass = PulsarApplyContext.__name__

        act_kwargs.file_list = trans_files.pulsar_actuator()

        # 获取集群部署配置
        pulsar_pipeline.add_act(
            act_name=_("获取集群部署配置"), act_component_code=GetPulsarActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )
        # 获取机器资源
        pulsar_pipeline.add_act(
            act_name=_("获取机器信息"), act_component_code=GetPulsarResourceComponent.code, kwargs=asdict(act_kwargs)
        )

        # 更新dbactor
        all_ips = self.get_all_node_ips_from_dbmeta()
        act_kwargs.exec_ip = all_ips
        pulsar_pipeline.add_act(
            act_name=_("下发pulsar actuator"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
        )
        # 缩容bookkeeper编排
        if PulsarRoleEnum.BookKeeper in self.nodes and self.nodes[PulsarRoleEnum.BookKeeper]:
            shrink_bookie_sub_flow = self.del_bookkeeper_sub_flow(
                act_kwargs=act_kwargs, data=self.base_flow_data, cur_bookie_num=len(self.bookie_ips)
            )
            pulsar_pipeline.add_sub_pipeline(sub_flow=shrink_bookie_sub_flow.build_sub_process(_("缩容BookKeeper子流程")))

        # 缩容broker编排
        if PulsarRoleEnum.Broker in self.nodes and self.nodes[PulsarRoleEnum.Broker]:
            # 添加到DBMeta
            dns_kwargs = DnsKwargs(
                bk_cloud_id=self.base_flow_data["bk_cloud_id"],
                dns_op_type=DnsOpType.RECYCLE_RECORD,
                domain_name=self.base_flow_data["domain"],
                dns_op_exec_port=self.base_flow_data["port"],
            )
            pulsar_pipeline.add_act(
                act_name=_("更新域名映射"),
                act_component_code=PulsarDnsManageComponent.code,
                kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
            )
            broker_act_list = self.del_broker_act_list(act_kwargs)
            pulsar_pipeline.add_parallel_acts(acts_list=broker_act_list)

        # 清理机器
        clean_data_acts = []
        for ip in get_all_node_ips_in_ticket(data=self.base_flow_data):
            # 清理数据
            act_kwargs.get_pulsar_payload_func = PulsarActPayload.get_clean_data_payload.__name__
            act_kwargs.exec_ip = ip
            clean_data_act = {
                "act_name": _("节点清理-{}").format(ip),
                "act_component_code": ExecutePulsarActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            clean_data_acts.append(clean_data_act)
        pulsar_pipeline.add_parallel_acts(acts_list=clean_data_acts)

        # 包含将机器CC挪到待回收
        pulsar_pipeline.add_act(
            act_name=_("DBMeta删除下架IP"), act_component_code=PulsarDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        pulsar_pipeline.run_pipeline()
