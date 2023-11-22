import copy
import logging.config
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.flow.consts import DnsOpType, ManagerOpType, ManagerServiceType, MediumFileTypeEnum, PulsarRoleEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.pulsar.pulsar_base_flow import get_all_node_ips_in_ticket
from backend.flow.engine.bamboo.scene.pulsar.pulsar_sub_flow import PulsarOperationFlow
from backend.flow.plugins.components.collections.common.bigdata_manager_service import (
    BigdataManagerComponent,
    get_manager_ip,
)
from backend.flow.plugins.components.collections.pulsar.exec_actuator_script import (
    ExecutePulsarActuatorScriptComponent,
)
from backend.flow.plugins.components.collections.pulsar.get_pulsar_payload import GetPulsarActPayloadComponent
from backend.flow.plugins.components.collections.pulsar.get_pulsar_resource import GetPulsarResourceComponent
from backend.flow.plugins.components.collections.pulsar.pulsar_db_meta import PulsarDBMetaComponent
from backend.flow.plugins.components.collections.pulsar.pulsar_dns_manage import PulsarDnsManageComponent
from backend.flow.plugins.components.collections.pulsar.rewrite_pulsar_config import WriteBackPulsarConfigComponent
from backend.flow.plugins.components.collections.pulsar.trans_files import TransFileComponent
from backend.flow.utils.extension_manage import BigdataManagerKwargs
from backend.flow.utils.pulsar.consts import (
    PULSAR_AUTH_CONF_TARGET_PATH,
    PULSAR_KEY_PATH_LIST_BROKER,
    PULSAR_MANAGER_WEB_PORT,
)
from backend.flow.utils.pulsar.pulsar_act_payload import PulsarActPayload
from backend.flow.utils.pulsar.pulsar_context_dataclass import (
    DnsKwargs,
    PulsarActKwargs,
    PulsarApplyContext,
    TransFilesKwargs,
)
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class PulsarReplaceFlow(PulsarOperationFlow):
    """
    构建Pulsar替换流程的抽象类
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        super().__init__(root_id, data)
        self.data = data

    def replace_pulsar_flow(self):
        """
        定义部署Pulsar集群
        """

        pulsar_pipeline = Builder(root_id=self.root_id, data=self.base_flow_data)
        trans_files = GetFileList(db_type=DBType.Pulsar)
        # 拼接活动节点需要的私有参数
        act_kwargs = PulsarActKwargs(bk_cloud_id=self.base_flow_data["bk_cloud_id"])
        act_kwargs.set_trans_data_dataclass = PulsarApplyContext.__name__

        act_kwargs.file_list = trans_files.pulsar_apply(db_version=self.base_flow_data["db_version"])
        # 获取集群部署配置
        pulsar_pipeline.add_act(
            act_name=_("获取集群部署配置"), act_component_code=GetPulsarActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )
        # 获取机器资源
        pulsar_pipeline.add_act(
            act_name=_("获取机器信息"), act_component_code=GetPulsarResourceComponent.code, kwargs=asdict(act_kwargs)
        )

        # 替换ZK流程
        if PulsarRoleEnum.ZooKeeper in self.data["old_nodes"] and self.data["old_nodes"][PulsarRoleEnum.ZooKeeper]:
            self.get_replace_zk_nodes(ticket_data=self.data)
            replace_zk_data = copy.deepcopy(self.base_flow_data)
            replace_zk_sub_pipeline = SubBuilder(root_id=self.root_id, data=replace_zk_data)
            act_kwargs.exec_ip = self.base_flow_data["new_zk_ips"]
            replace_zk_sub_pipeline.add_act(
                act_name=_("下发pulsar介质"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
            )
            sub_pipelines = self.new_common_sub_flow(
                act_kwargs=act_kwargs,
                data=replace_zk_data,
                ips=replace_zk_data["new_zk_ips"],
                role=PulsarRoleEnum.ZooKeeper,
            )
            replace_zk_sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
            replace_zk_sub_operations = self.replace_zookeeper_pipeline_list(
                act_kwargs=act_kwargs, data=replace_zk_data
            )
            for sub_pipeline in replace_zk_sub_operations:
                replace_zk_sub_pipeline.add_sub_pipeline(sub_pipeline)

            # 判断是否替换pulsar manager 部署
            repl_mgr_sub_pipeline = self.replace_pulsar_manager_sub_flow(act_kwargs, replace_zk_data)
            if repl_mgr_sub_pipeline:
                replace_zk_sub_pipeline.add_sub_pipeline(
                    sub_flow=repl_mgr_sub_pipeline.build_sub_process(sub_name=_("替换pulsar manager子流程"))
                )

            # 清理机器
            clean_data_acts = []
            for ip in replace_zk_data["old_zk_ips"]:
                # 清理数据
                act_kwargs.get_pulsar_payload_func = PulsarActPayload.get_clean_data_payload.__name__
                act_kwargs.exec_ip = ip
                clean_data_act = {
                    "act_name": _("节点清理-{}").format(ip),
                    "act_component_code": ExecutePulsarActuatorScriptComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
                clean_data_acts.append(clean_data_act)
            replace_zk_sub_pipeline.add_parallel_acts(acts_list=clean_data_acts)
            # 更新dbmeta
            replace_zk_sub_pipeline.add_act(
                act_name=_("更新DBMeta"), act_component_code=PulsarDBMetaComponent.code, kwargs=asdict(act_kwargs)
            )
            # 更新dbconfig
            replace_zk_sub_pipeline.add_act(
                act_name=_("回写集群配置信息"),
                act_component_code=WriteBackPulsarConfigComponent.code,
                kwargs=asdict(act_kwargs),
            )
            pulsar_pipeline.add_sub_pipeline(
                sub_flow=replace_zk_sub_pipeline.build_sub_process(sub_name=_("替换ZooKeeper子流程"))
            )

        # 创建 扩/缩容 子流程
        if PulsarRoleEnum.Broker in self.data["old_nodes"] or PulsarRoleEnum.BookKeeper in self.data["old_nodes"]:
            #   将替换流程new_nodes上的IP信息写入self.nodes及self.base_flow_data
            scale_up_data = self.update_nodes_replace(self.data, TicketType.PULSAR_SCALE_UP)
            scale_up_sub_pipeline = SubBuilder(root_id=self.root_id, data=scale_up_data)
            act_kwargs.exec_ip = get_all_node_ips_in_ticket(data=scale_up_data)
            scale_up_sub_pipeline.add_act(
                act_name=_("下发pulsar介质"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
            )
            # 待扩容节点 安装pulsar common子流程 编排
            sub_pipelines = self.new_nodes_common_sub_flow_list(act_kwargs=act_kwargs, data=scale_up_data)
            # 并发执行所有子流程
            scale_up_sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
            # 安装bookkeeper
            if PulsarRoleEnum.BookKeeper in self.nodes and self.nodes[PulsarRoleEnum.BookKeeper]:
                bookie_act_list = self.new_bookkeeper_act_list(act_kwargs)
                scale_up_sub_pipeline.add_parallel_acts(acts_list=bookie_act_list)
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
                scale_up_sub_pipeline.add_act(
                    act_name=_("分发密钥及token"),
                    act_component_code=TransFileComponent.code,
                    kwargs={**asdict(act_kwargs), **asdict(trans_file_kwargs)},
                )
                broker_act_list = self.new_broker_act_list(act_kwargs)
                scale_up_sub_pipeline.add_parallel_acts(acts_list=broker_act_list)
                dns_kwargs = DnsKwargs(
                    bk_cloud_id=scale_up_data["bk_cloud_id"],
                    dns_op_type=DnsOpType.CREATE,
                    domain_name=scale_up_data["domain"],
                    dns_op_exec_port=scale_up_data["port"],
                )
                scale_up_sub_pipeline.add_act(
                    act_name=_("添加集群域名"),
                    act_component_code=PulsarDnsManageComponent.code,
                    kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
                )
            scale_up_sub_pipeline.add_act(
                act_name=_("更新DBMeta元信息"), act_component_code=PulsarDBMetaComponent.code, kwargs=asdict(act_kwargs)
            )
            pulsar_pipeline.add_sub_pipeline(sub_flow=scale_up_sub_pipeline.build_sub_process(sub_name=_("扩容子流程")))

            # 缩容子流程
            shrink_data = self.update_nodes_replace(self.data, TicketType.PULSAR_SHRINK)
            shrink_sub_pipeline = SubBuilder(root_id=self.root_id, data=shrink_data)
            # 缩容bookkeeper编排
            if PulsarRoleEnum.BookKeeper in self.nodes and self.nodes[PulsarRoleEnum.BookKeeper]:
                bookie_num = len(self.bookie_ips) + len(self.nodes[PulsarRoleEnum.BookKeeper])
                shrink_bookie_sub_flow = self.del_bookkeeper_sub_flow(
                    act_kwargs=act_kwargs, data=shrink_data, cur_bookie_num=bookie_num
                )
                shrink_sub_pipeline.add_sub_pipeline(
                    sub_flow=shrink_bookie_sub_flow.build_sub_process(_("缩容BookKeeper子流程"))
                )

            # 缩容broker编排
            if PulsarRoleEnum.Broker in self.nodes and self.nodes[PulsarRoleEnum.Broker]:
                # 添加到DBMeta
                dns_kwargs = DnsKwargs(
                    bk_cloud_id=shrink_data["bk_cloud_id"],
                    dns_op_type=DnsOpType.RECYCLE_RECORD,
                    domain_name=shrink_data["domain"],
                    dns_op_exec_port=shrink_data["port"],
                )
                shrink_sub_pipeline.add_act(
                    act_name=_("更新域名映射"),
                    act_component_code=PulsarDnsManageComponent.code,
                    kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
                )
                broker_act_list = self.del_broker_act_list(act_kwargs)
                shrink_sub_pipeline.add_parallel_acts(acts_list=broker_act_list)

            # 清理机器
            clean_data_acts = []
            for ip in get_all_node_ips_in_ticket(data=shrink_data):
                # 清理数据
                act_kwargs.get_pulsar_payload_func = PulsarActPayload.get_clean_data_payload.__name__
                act_kwargs.exec_ip = ip
                clean_data_act = {
                    "act_name": _("节点清理-{}").format(ip),
                    "act_component_code": ExecutePulsarActuatorScriptComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
                clean_data_acts.append(clean_data_act)
            shrink_sub_pipeline.add_parallel_acts(acts_list=clean_data_acts)

            # 包含将机器CC挪到待回收
            shrink_sub_pipeline.add_act(
                act_name=_("DBMeta删除下架IP"),
                act_component_code=PulsarDBMetaComponent.code,
                kwargs=asdict(act_kwargs),
            )
            pulsar_pipeline.add_sub_pipeline(sub_flow=shrink_sub_pipeline.build_sub_process(sub_name=_("缩容子流程")))

        pulsar_pipeline.run_pipeline()

    # 替换pulsar manager
    def replace_pulsar_manager_sub_flow(self, act_kwargs: PulsarActKwargs, data: dict):

        # 检查下架ZK节点上是否安装pulsar_manager
        manager_ip = get_manager_ip(
            bk_biz_id=data["bk_biz_id"],
            db_type=DBType.Pulsar,
            cluster_name=data["cluster_name"],
            service_type=ManagerServiceType.PULSAR_MANAGER,
        )
        if manager_ip in data["old_zk_ips"]:
            sub_pipeline = SubBuilder(root_id=self.root_id, data=data)
            new_manager_ip = data["new_zk_ips"][0]
            # 更新haproxy实例信息
            manager_kwargs = BigdataManagerKwargs(
                manager_op_type=ManagerOpType.UPDATE,
                db_type=DBType.Pulsar,
                service_type=ManagerServiceType.PULSAR_MANAGER,
                # 随机挑选一台新替换ZK主机
                manager_ip=new_manager_ip,
                manager_port=PULSAR_MANAGER_WEB_PORT,
            )
            sub_pipeline.add_act(
                act_name=_("更新pulsar_manager实例信息"),
                act_component_code=BigdataManagerComponent.code,
                kwargs={**asdict(act_kwargs), **asdict(manager_kwargs)},
            )
            if not self.domain_resolve_supported:
                # 添加Broker域名，仅不支持DNS解析的环境使用
                act_kwargs.exec_ip = new_manager_ip
                act_kwargs.get_pulsar_payload_func = PulsarActPayload.get_modify_hosts_payload.__name__
                # 替换ZK流程中 kwargs zk_host_map 动态更新
                zk_host_map = copy.deepcopy(act_kwargs.zk_host_map)
                # 添加broker域名映射
                act_kwargs.zk_host_map[self.broker_ips[0]] = data["domain"]
                sub_pipeline.add_act(
                    act_name=_("仅非DNS环境使用-添加broker域名"),
                    act_component_code=ExecutePulsarActuatorScriptComponent.code,
                    kwargs=asdict(act_kwargs),
                )
                # act_kwargs.zk_host_map扩容时还需要使用
                act_kwargs.zk_host_map = zk_host_map

            # 安装pulsar manager
            act_kwargs.exec_ip = new_manager_ip
            act_kwargs.get_pulsar_payload_func = PulsarActPayload.get_install_manager_payload.__name__
            sub_pipeline.add_act(
                act_name=_("安装pulsar manager"),
                act_component_code=ExecutePulsarActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )
            # 初始化 manager
            act_kwargs.exec_ip = new_manager_ip
            act_kwargs.get_pulsar_payload_func = PulsarActPayload.get_init_manager_payload.__name__
            sub_pipeline.add_act(
                act_name=_("初始化pulsar manager"),
                act_component_code=ExecutePulsarActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )
            return sub_pipeline
        else:
            return None
