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
from typing import Dict, List, Optional, Tuple

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import InstanceRole
from backend.flow.consts import DnsOpType, DorisRoleEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.doris.doris_base_flow import (
    DorisBaseFlow,
    get_all_node_ips_in_ticket,
    make_meta_host_map,
)
from backend.flow.engine.bamboo.scene.doris.exceptions import (
    ReplaceMachineCountException,
    RoleMachineCountMustException,
)
from backend.flow.plugins.components.collections.doris.doris_db_meta import DorisMetaComponent
from backend.flow.plugins.components.collections.doris.doris_dns_manage import DorisDnsManageComponent
from backend.flow.plugins.components.collections.doris.exec_doris_actuator_script import (
    ExecuteDorisActuatorScriptComponent,
)
from backend.flow.plugins.components.collections.doris.get_doris_payload import GetDorisActPayloadComponent
from backend.flow.plugins.components.collections.es.trans_files import TransFileComponent
from backend.flow.utils.doris.consts import DORIS_FOLLOWER_MUST_COUNT
from backend.flow.utils.doris.doris_act_payload import DorisActPayload
from backend.flow.utils.doris.doris_context_dataclass import DorisActKwargs, DorisApplyContext
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class DorisReplaceFlow(DorisBaseFlow):
    """
    Doris替换流程
    FE 替换采用逐个滚动替换模式，保证集群在替换过程中始终有足够的可用节点。
    BE 替换保持先扩后缩的两阶段模式。
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        :param root_id: 任务流程定义的root_id
        :param data: 单据传递过来的参数列表，字典格式
        """
        super().__init__(root_id, data)
        self.new_nodes = data["new_nodes"]
        self.old_nodes = data["old_nodes"]

    def __get_fe_replace_order(self) -> List[Tuple[str, str, str]]:
        """
        确定 FE 替换顺序：follower（先） → observer（后）
        follower 统一使用 Stop → DROP 顺序，避免 "can not drop current master node" 错误

        :return: [(old_ip, new_ip, role), ...] 按替换顺序排列
        """
        fe_roles = [DorisRoleEnum.FOLLOWER.value, DorisRoleEnum.OBSERVER.value]
        followers = []
        observers = []

        for role in fe_roles:
            if role not in self.old_nodes or role not in self.new_nodes:
                continue
            old_ips = [node["ip"] for node in self.old_nodes[role]]
            new_ips = [node["ip"] for node in self.new_nodes[role]]
            if len(old_ips) != len(new_ips):
                raise ReplaceMachineCountException(
                    doris_role=role,
                    old_count=len(old_ips),
                    new_count=len(new_ips),
                )
            for i, old_ip in enumerate(old_ips):
                new_ip = new_ips[i]
                if role == DorisRoleEnum.FOLLOWER.value:
                    followers.append((old_ip, new_ip, role))
                else:
                    observers.append((old_ip, new_ip, role))

        replace_order = followers + observers
        logger.info("FE replace order: %s", replace_order)
        return replace_order

    def __get_flow_data(self) -> dict:
        flow_data = self.get_flow_base_data()
        flow_data["new_nodes"] = self.new_nodes
        flow_data["old_nodes"] = self.old_nodes
        flow_data["master_fe_ip"] = self.follower_ips[0]
        return flow_data

    def __get_scale_up_flow_data(self) -> dict:
        flow_data = self.get_flow_base_data()
        flow_data["nodes"] = self.new_nodes
        flow_data["ticket_type"] = TicketType.DORIS_SCALE_UP.value
        follower_ips = self.get_role_ips_in_dbmeta(InstanceRole.DORIS_FOLLOWER)
        if len(follower_ips) < DORIS_FOLLOWER_MUST_COUNT:
            logger.error("get follower ips from dbmeta, count is {}, invalid".format(len(follower_ips)))
            raise RoleMachineCountMustException(
                doris_role=DorisRoleEnum.FOLLOWER, must_count=DORIS_FOLLOWER_MUST_COUNT
            )
        flow_data["master_fe_ip"] = follower_ips[0]
        host_map = make_meta_host_map(flow_data)
        flow_data["host_meta_map"] = host_map
        return flow_data

    def __get_shrink_flow_data(self) -> dict:
        flow_data = self.get_flow_base_data()
        flow_data["nodes"] = self.old_nodes
        flow_data["ticket_type"] = TicketType.DORIS_SHRINK.value
        if DorisRoleEnum.FOLLOWER in self.new_nodes and self.new_nodes[DorisRoleEnum.FOLLOWER]:
            new_follower_ips = [node["ip"] for node in self.new_nodes[DorisRoleEnum.FOLLOWER]]
            flow_data["master_fe_ip"] = new_follower_ips[0]
        else:
            follower_ips = self.get_role_ips_in_dbmeta(InstanceRole.DORIS_FOLLOWER)
            if len(follower_ips) < DORIS_FOLLOWER_MUST_COUNT:
                logger.error("get follower ips from dbmeta, count is {}, invalid".format(len(follower_ips)))
                raise RoleMachineCountMustException(
                    doris_role=DorisRoleEnum.FOLLOWER, must_count=DORIS_FOLLOWER_MUST_COUNT
                )
            flow_data["master_fe_ip"] = follower_ips[0]
        return flow_data

    def replace_doris_flow(self):
        """
        Doris 替换流程
        FE 采用逐个滚动替换，BE 保持先扩后缩两阶段模式
        """
        replace_data = self.__get_flow_data()
        self.check_replace_role_ip_count(replace_data)

        doris_pipeline = Builder(root_id=self.root_id, data=replace_data)
        trans_files = GetFileList(db_type=DBType.Doris)

        # ================================================================
        # Pipeline 1: 介质准备与节点预初始化
        # ================================================================
        preinit_pipeline = SubBuilder(root_id=self.root_id, data=replace_data)

        preinit_kwargs = DorisActKwargs(bk_cloud_id=self.bk_cloud_id)
        preinit_kwargs.set_trans_data_dataclass = DorisApplyContext.__name__

        # --- 获取 Payload（必须在 ExecuteDorisActuatorScript 之前） ---
        preinit_pipeline.add_act(
            act_name=_("获取Payload"),
            act_component_code=GetDorisActPayloadComponent.code,
            kwargs=asdict(preinit_kwargs),
        )

        # --- A. 所有旧节点下发最新 dbactuator 介质 ---
        all_old_ips = get_all_node_ips_in_ticket(data={"nodes": self.old_nodes})
        if all_old_ips:
            preinit_kwargs.exec_ip = all_old_ips
            preinit_kwargs.file_list = trans_files.doris_actuator()
            preinit_pipeline.add_act(
                act_name=_("旧节点下发dbactuator介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(preinit_kwargs),
            )

        # --- B. 所有新节点下发 Doris 介质 + 并发初始化 ---
        all_new_ips = get_all_node_ips_in_ticket(data={"nodes": self.new_nodes})
        if all_new_ips:
            preinit_kwargs.exec_ip = all_new_ips
            preinit_kwargs.file_list = trans_files.doris_apply(db_version=self.db_version)
            preinit_pipeline.add_act(
                act_name=_("新节点下发Doris介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(preinit_kwargs),
            )

            new_init_data = copy.deepcopy(replace_data)
            new_init_data["nodes"] = self.new_nodes
            sub_common_pipelines = self.new_common_sub_flows(act_kwargs=preinit_kwargs, data=new_init_data)
            if sub_common_pipelines:
                preinit_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_common_pipelines)

        doris_pipeline.add_sub_pipeline(sub_flow=preinit_pipeline.build_sub_process(sub_name=_("介质准备与节点预初始化")))

        # ================================================================
        # Pipeline 2: FE 替换（逐个滚动替换）
        # ================================================================
        fe_replace_order = self.__get_fe_replace_order()

        # 追踪当前确定在线的 FE IP（follower 或 observer 均可）。
        # 用于 ADD FOLLOWER、helper 启动、BE 元数据更新等需要连接集群的操作。
        # 第1个替换用当前 master，之后的替换用上一个已启动成功的新 FE。
        # 全部替换完成后它就是最后一个新 FE，传给 BE 替换阶段使用。
        #
        # 注意：active_target_ip 的更新发生在每轮迭代末尾，它假设上一轮
        # 的新 FE 已成功启动。但若上一轮的新 FE 启动失败，active_target_ip 已指向一个
        # 未上线的节点，而该轮迭代的旧 FE 可能已被 DROP，导致下一轮 ADD 无可用连接。
        # 此处依赖 sub_pipeline 的串行执行语义：任意子步骤失败会立即中止整个流程，
        # 不会进入下一轮迭代，因此不会出现"旧 FE 已删、新 FE 未启"的中间态被后续
        # 迭代使用的问题。
        active_target_ip = self.follower_ips[0]
        logger.info("replace flow: initial active_target_ip=%s", active_target_ip)

        if fe_replace_order:
            fe_replace_pipeline = SubBuilder(root_id=self.root_id, data=replace_data)

            for idx, (old_ip, new_ip, role) in enumerate(fe_replace_order):
                logger.info(
                    "FE rolling replace [%d/%d]: old=%s new=%s role=%s target=%s",
                    idx + 1,
                    len(fe_replace_order),
                    old_ip,
                    new_ip,
                    role,
                    active_target_ip,
                )

                # 每个迭代创建独立的数据副本，避免共享引用导致 master_fe_ip 被后续迭代覆盖
                iter_data = copy.deepcopy(replace_data)
                iter_data["master_fe_ip"] = active_target_ip
                # ADD 使用的 host_meta_map
                iter_data["host_meta_map"] = {role: [new_ip]}
                # DROP 使用的 host_meta_map（存在不同 key，避免与 ADD 冲突）
                iter_data["host_meta_map_del"] = {role: [old_ip]}
                iter_data["master_fe_ip_del"] = new_ip

                rolling_pipeline = SubBuilder(root_id=self.root_id, data=iter_data)

                rolling_kwargs = DorisActKwargs(bk_cloud_id=self.bk_cloud_id)
                rolling_kwargs.set_trans_data_dataclass = DorisApplyContext.__name__

                # --- Step 1: 获取主 Payload ---
                rolling_pipeline.add_act(
                    act_name=_("获取Payload"),
                    act_component_code=GetDorisActPayloadComponent.code,
                    kwargs=asdict(rolling_kwargs),
                )

                # --- Step 2: 添加新 FE 元数据 ---
                rolling_kwargs.exec_ip = active_target_ip
                rolling_kwargs.get_doris_payload_func = DorisActPayload.get_add_metadata_payload.__name__
                rolling_pipeline.add_act(
                    act_name=_("添加新FE元数据-{}-{}").format(role, new_ip),
                    act_component_code=ExecuteDorisActuatorScriptComponent.code,
                    kwargs=asdict(rolling_kwargs),
                )

                # --- Step 3: 启动新 FE ---
                rolling_kwargs.exec_ip = new_ip
                rolling_kwargs.doris_role = role
                rolling_kwargs.get_doris_payload_func = DorisActPayload.get_start_fe_by_helper_payload.__name__
                rolling_pipeline.add_act(
                    act_name=_("helper启动新FE-{}-{}").format(role, new_ip),
                    act_component_code=ExecuteDorisActuatorScriptComponent.code,
                    kwargs=asdict(rolling_kwargs),
                )

                rolling_kwargs.get_doris_payload_func = DorisActPayload.get_install_doris_payload.__name__
                rolling_pipeline.add_act(
                    act_name=_("supervisor接管新FE-{}-{}").format(role, new_ip),
                    act_component_code=ExecuteDorisActuatorScriptComponent.code,
                    kwargs=asdict(rolling_kwargs),
                )

                # --- Step 4: 检查新 FE 启动 ---
                rolling_kwargs.get_doris_payload_func = DorisActPayload.get_check_start_payload.__name__
                rolling_pipeline.add_act(
                    act_name=_("检查新FE启动-{}-{}").format(role, new_ip),
                    act_component_code=ExecuteDorisActuatorScriptComponent.code,
                    kwargs=asdict(rolling_kwargs),
                )

                # --- Step 5: 停止旧 FE 进程 ---
                rolling_kwargs.exec_ip = old_ip
                rolling_kwargs.doris_role = role
                rolling_kwargs.get_doris_payload_func = DorisActPayload.get_stop_process_payload.__name__
                rolling_pipeline.add_act(
                    act_name=_("停止旧FE进程-{}-{}").format(role, old_ip),
                    act_component_code=ExecuteDorisActuatorScriptComponent.code,
                    kwargs=asdict(rolling_kwargs),
                )

                # --- Step 6: 删除旧 FE 元数据 ---
                rolling_kwargs.exec_ip = new_ip
                rolling_kwargs.get_doris_payload_func = DorisActPayload.get_drop_metadata_for_replace_payload.__name__
                rolling_pipeline.add_act(
                    act_name=_("删除旧FE元数据-{}-{}").format(role, old_ip),
                    act_component_code=ExecuteDorisActuatorScriptComponent.code,
                    kwargs=asdict(rolling_kwargs),
                )

                fe_replace_pipeline.add_sub_pipeline(
                    sub_flow=rolling_pipeline.build_sub_process(
                        sub_name=_(
                            "滚动替换FE [{}/{}] {}-{}→{}".format(idx + 1, len(fe_replace_order), role, old_ip, new_ip)
                        )
                    )
                )

                # 本轮替换完成后，新 FE 已在线，下一个替换用这个新 FE 作为连接目标
                active_target_ip = new_ip
                logger.info(
                    "FE rolling replace [%d/%d] done, next active_target_ip=%s",
                    idx + 1,
                    len(fe_replace_order),
                    active_target_ip,
                )

            # FE 替换完成，立即更新 DBMeta 和域名（只更新 FE 相关节点）
            fe_meta_data = copy.deepcopy(replace_data)
            fe_roles = [DorisRoleEnum.FOLLOWER.value, DorisRoleEnum.OBSERVER.value]
            fe_meta_data["new_nodes"] = {k: v for k, v in self.new_nodes.items() if k in fe_roles}
            fe_meta_data["old_nodes"] = {k: v for k, v in self.old_nodes.items() if k in fe_roles}
            fe_meta_data["ticket_type"] = TicketType.DORIS_REPLACE.value

            fe_meta_sub = SubBuilder(root_id=self.root_id, data=fe_meta_data)
            fe_meta_sub.add_act(
                act_name=_("更新FE-DBMeta"),
                act_component_code=DorisMetaComponent.code,
                kwargs={},
            )
            fe_meta_sub.add_act(
                act_name=_("更新FE域名"),
                act_component_code=DorisDnsManageComponent.code,
                kwargs={
                    "bk_cloud_id": self.bk_cloud_id,
                    "dns_op_type": DnsOpType.UPDATE,
                    "domain_name": self.domain,
                    "dns_op_exec_port": self.http_port,
                },
            )
            fe_replace_pipeline.add_sub_pipeline(fe_meta_sub.build_sub_process(sub_name=_("更新FE元数据")))

            doris_pipeline.add_sub_pipeline(fe_replace_pipeline.build_sub_process(sub_name=_("FE替换")))

        # ================================================================
        # Pipeline 3: BE 替换（先扩后缩）
        # ================================================================
        be_roles = [DorisRoleEnum.HOT.value, DorisRoleEnum.WARM.value, DorisRoleEnum.COLD.value]
        be_has_new = any(role in self.new_nodes and self.new_nodes[role] for role in be_roles)
        be_has_old = any(role in self.old_nodes and self.old_nodes[role] for role in be_roles)

        if be_has_new or be_has_old:
            be_replace_pipeline = SubBuilder(root_id=self.root_id, data=replace_data)

            # --- BE 扩容 ---
            if be_has_new:
                scale_up_data = self.__get_scale_up_flow_data()
                scale_up_data["master_fe_ip"] = active_target_ip
                # 只更新 BE 节点元数据，FE 已在 FE 替换阶段逐个 ADD 完毕
                scale_up_data["host_meta_map"] = {
                    k: v for k, v in scale_up_data["host_meta_map"].items() if k in be_roles
                }
                be_expand_sub = SubBuilder(root_id=self.root_id, data=scale_up_data)

                expand_kwargs = DorisActKwargs(bk_cloud_id=self.bk_cloud_id)
                expand_kwargs.set_trans_data_dataclass = DorisApplyContext.__name__

                # 节点初始化已在 Pipeline 1 完成，这里只需 GetPayload + ADD + 启动
                be_expand_sub.add_act(
                    act_name=_("获取Payload"),
                    act_component_code=GetDorisActPayloadComponent.code,
                    kwargs=asdict(expand_kwargs),
                )

                expand_kwargs.exec_ip = scale_up_data["master_fe_ip"]
                expand_kwargs.get_doris_payload_func = DorisActPayload.get_add_metadata_payload.__name__
                be_expand_sub.add_act(
                    act_name=_("BE集群元数据更新"),
                    act_component_code=ExecuteDorisActuatorScriptComponent.code,
                    kwargs=asdict(expand_kwargs),
                )

                sub_new_be_acts = self.new_be_sub_acts(act_kwargs=expand_kwargs, data=scale_up_data)
                if sub_new_be_acts:
                    be_expand_sub.add_parallel_acts(acts_list=sub_new_be_acts)

                be_replace_pipeline.add_sub_pipeline(be_expand_sub.build_sub_process(sub_name=_("BE扩容")))

            # --- BE 缩容 ---
            if be_has_old:
                shrink_data = self.__get_shrink_flow_data()
                shrink_data["master_fe_ip"] = active_target_ip
                # 把新 BE 的 host_meta_map 注入 shrink_data，供退役前检查使用
                if be_has_new:
                    shrink_data["host_meta_map_new"] = {
                        k: v for k, v in scale_up_data["host_meta_map"].items() if k in be_roles
                    }
                del_be_pipeline = self.build_del_be_sub_flow(data=shrink_data)
                be_replace_pipeline.add_sub_pipeline(del_be_pipeline.build_sub_process(sub_name=_("BE缩容")))

            # BE 替换完成，立即更新 DBMeta 和域名（只更新 BE 相关节点）
            be_meta_data = copy.deepcopy(replace_data)
            be_meta_data["new_nodes"] = {k: v for k, v in self.new_nodes.items() if k in be_roles}
            be_meta_data["old_nodes"] = {k: v for k, v in self.old_nodes.items() if k in be_roles}
            be_meta_data["ticket_type"] = TicketType.DORIS_REPLACE.value

            be_meta_sub = SubBuilder(root_id=self.root_id, data=be_meta_data)
            be_meta_sub.add_act(
                act_name=_("更新BE-DBMeta"),
                act_component_code=DorisMetaComponent.code,
                kwargs={},
            )
            be_meta_sub.add_act(
                act_name=_("更新BE域名"),
                act_component_code=DorisDnsManageComponent.code,
                kwargs={
                    "bk_cloud_id": self.bk_cloud_id,
                    "dns_op_type": DnsOpType.UPDATE,
                    "domain_name": self.domain,
                    "dns_op_exec_port": self.http_port,
                },
            )
            be_replace_pipeline.add_sub_pipeline(be_meta_sub.build_sub_process(sub_name=_("更新BE元数据")))

            doris_pipeline.add_sub_pipeline(be_replace_pipeline.build_sub_process(sub_name=_("BE替换")))

        # ================================================================
        # Pipeline 4: 收尾步骤（只清理旧节点数据目录）
        # ================================================================
        cleanup_pipeline = SubBuilder(root_id=self.root_id, data=replace_data)

        # 收集所有待清理的旧节点（FE + BE）
        all_old_cleanup_ips = get_all_node_ips_in_ticket(data={"nodes": self.old_nodes})

        cleanup_kwargs = DorisActKwargs(bk_cloud_id=self.bk_cloud_id)
        cleanup_kwargs.set_trans_data_dataclass = DorisApplyContext.__name__

        # 必须先 GetPayload 初始化 trans_data.doris_act_payload
        cleanup_pipeline.add_act(
            act_name=_("获取Payload"),
            act_component_code=GetDorisActPayloadComponent.code,
            kwargs=asdict(cleanup_kwargs),
        )

        if all_old_cleanup_ips:
            cleanup_acts = []
            # 注意：循环中多次修改 cleanup_kwargs 后通过 asdict() 生成 dict 追加到列表。
            # asdict() 每次调用都会将 dataclass 转换为新的 dict，因此各迭代的 kwargs
            # 互不影响。切勿改为直接传 cleanup_kwargs 对象，否则所有 act 将共享同一
            # 引用，最终全部指向循环末尾的值。
            for ip in all_old_cleanup_ips:
                # 从 old_nodes 中查找该 IP 对应的角色
                ip_role = ""
                for role, nodes in self.old_nodes.items():
                    if any(node["ip"] == ip for node in nodes):
                        ip_role = role
                        break
                cleanup_kwargs.exec_ip = ip
                cleanup_kwargs.doris_role = ip_role
                cleanup_kwargs.get_doris_payload_func = DorisActPayload.get_clean_data_payload.__name__
                cleanup_acts.append(
                    {
                        "act_name": _("清理旧节点-{}-{}").format(ip_role, ip),
                        "act_component_code": ExecuteDorisActuatorScriptComponent.code,
                        "kwargs": asdict(cleanup_kwargs),
                    }
                )
            if cleanup_acts:
                cleanup_pipeline.add_parallel_acts(acts_list=cleanup_acts)

        doris_pipeline.add_sub_pipeline(sub_flow=cleanup_pipeline.build_sub_process(sub_name=_("收尾步骤")))

        doris_pipeline.run_pipeline_with_sidecar(check_ai_monitor_cluster_list=[self.cluster_id])

    def check_replace_role_ip_count(self, data: dict):
        old_role_nodes = {}
        new_role_nodes = {}
        for role in DorisRoleEnum:
            if role not in data.get("old_nodes"):
                old_ips = []
            else:
                old_ips = [node["ip"] for node in data["old_nodes"][role]]
            old_role_nodes[role] = old_ips

            if role not in data.get("new_nodes"):
                new_ips = []
            else:
                new_ips = [node["ip"] for node in data["new_nodes"][role]]
            new_role_nodes[role] = new_ips

        for role, ips in old_role_nodes.items():
            old_ips_cnt = len(ips)
            new_ips_cnt = len(new_role_nodes[role])
            if old_ips_cnt != new_ips_cnt:
                logger.error("ticket_type: %s, role is %s, machine count mismatch.", self.ticket_type, role)
                raise ReplaceMachineCountException(doris_role=role, old_count=old_ips_cnt, new_count=new_ips_cnt)
