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
    make_be_map_from_ticket,
    make_fe_map_from_ticket,
    make_meta_host_map,
)
from backend.flow.engine.bamboo.scene.doris.exceptions import ReplaceMachineCountException
from backend.flow.plugins.components.collections.doris.doris_db_meta import DorisMetaComponent
from backend.flow.plugins.components.collections.doris.doris_dns_manage import DorisDnsManageComponent
from backend.flow.plugins.components.collections.doris.exec_doris_actuator_script import (
    ExecuteDorisActuatorScriptComponent,
)
from backend.flow.plugins.components.collections.doris.get_doris_payload import GetDorisActPayloadComponent
from backend.flow.plugins.components.collections.es.trans_files import TransFileComponent
from backend.flow.utils.doris.doris_act_payload import DorisActPayload
from backend.flow.utils.doris.doris_context_dataclass import DorisActKwargs, DorisApplyContext
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class DorisReplaceFlow(DorisBaseFlow):
    """
    Doris替换流程，分为三大部分：
    1. Observer 替换：先扩后缩（Observer 不参与选主，可批量操作）
    2. Follower 滚动替换：逐个 ADD→启动→DNS→停旧→DNS→DROP→DBMeta
    3. BE 替换：先扩后缩
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        :param root_id: 任务流程定义的root_id
        :param data: 单据传递过来的参数列表，字典格式
        """
        super().__init__(root_id, data)
        self.new_nodes = data["new_nodes"]
        self.old_nodes = data["old_nodes"]

    def __get_follower_replace_order(self) -> List[Tuple[str, str, str]]:
        """
        确定 Follower 滚动替换顺序

        :return: [(old_ip, new_ip, role), ...] 按替换顺序排列
        """
        role = DorisRoleEnum.FOLLOWER.value
        replace_order = []

        if role not in self.old_nodes or role not in self.new_nodes:
            return replace_order

        old_ips = [node["ip"] for node in self.old_nodes[role]]
        new_ips = [node["ip"] for node in self.new_nodes[role]]
        if len(old_ips) != len(new_ips):
            raise ReplaceMachineCountException(
                doris_role=role,
                old_count=len(old_ips),
                new_count=len(new_ips),
            )
        for i, old_ip in enumerate(old_ips):
            replace_order.append((old_ip, new_ips[i], role))
        return replace_order

    def __get_flow_data(self) -> dict:
        flow_data = self.get_flow_base_data()
        flow_data["new_nodes"] = self.new_nodes
        flow_data["old_nodes"] = self.old_nodes
        flow_data["master_fe_ip"] = self.follower_ips[0]
        return flow_data

    def replace_doris_flow(self):  # noqa: C901
        """
        Doris 替换流程
        Pipeline 1: 介质准备与节点预初始化
        Pipeline 2: Observer 替换（先扩后缩）
        Pipeline 3: Follower 滚动替换
        Pipeline 4: BE 替换（先扩后缩）
        Pipeline 5: 收尾清理
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

        # --- A. 所有节点下发最新 dbactuator 介质 ---
        # 替换过程中需要在 FE 节点（active_target_ip）上执行元数据变更操作
        # （如 ADD/DROP OBSERVER、ADD FOLLOWER、退役 BE 等），而这些 FE 节点
        # 可能既不在旧节点也不在新节点中，因此需要对所有集群节点下发介质
        preinit_kwargs.exec_ip = self.get_all_node_ips_in_dbmeta()
        preinit_kwargs.file_list = trans_files.doris_actuator()
        dbactuator_act = {
            "act_name": _("下发dbactuator介质"),
            "act_component_code": TransFileComponent.code,
            "kwargs": asdict(preinit_kwargs),
        }

        parallel_acts = [dbactuator_act]
        all_new_ips = get_all_node_ips_in_ticket(data={"nodes": self.new_nodes})

        # --- B. 所有新节点下发 Doris 介质 ---
        # 与 dbactuator 并发执行，互不依赖
        if all_new_ips:
            preinit_kwargs.exec_ip = all_new_ips
            preinit_kwargs.file_list = trans_files.doris_apply(db_version=self.db_version)
            parallel_acts.append(
                {
                    "act_name": _("下发Doris介质"),
                    "act_component_code": TransFileComponent.code,
                    "kwargs": asdict(preinit_kwargs),
                }
            )

        preinit_pipeline.add_parallel_acts(acts_list=parallel_acts)

        # --- 新节点并发初始化 ---
        # 依赖 Doris 介质已下发到新节点
        if all_new_ips:
            new_init_data = copy.deepcopy(replace_data)
            new_init_data["nodes"] = self.new_nodes
            sub_common_pipelines = self.new_common_sub_flows(act_kwargs=preinit_kwargs, data=new_init_data)
            if sub_common_pipelines:
                preinit_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_common_pipelines)

        doris_pipeline.add_sub_pipeline(sub_flow=preinit_pipeline.build_sub_process(sub_name=_("介质准备与节点预初始化")))

        # active_target_ip 追踪当前确定在线的 Follower IP，用于 ADD/DROP 元数据、
        # helper 启动等需要连接集群的操作。初始值为 DBMeta 中现有的第一个 follower。
        # Observer 替换阶段不会改变 follower，Follower 滚动替换阶段每轮更新为新 follower。
        active_target_ip = self.follower_ips[0]

        # 查询集群当前 Observer IP 列表（构建时查询，反映 DBMeta 初始状态）
        # 用于： Follower 滚动替换判断是否需要更新 DNS
        existing_observer_ips = self.get_role_ips_in_dbmeta(InstanceRole.DORIS_OBSERVER)
        has_observer_in_dbmeta = len(existing_observer_ips) > 0

        # ================================================================
        # Pipeline 2: Observer 替换（先扩后缩）
        # Observer 不参与选主，可以像 BE 一样先扩后缩，无需滚动。
        # ================================================================
        observer_role = DorisRoleEnum.OBSERVER.value
        observer_has_new = observer_role in self.new_nodes and self.new_nodes[observer_role]
        observer_has_old = observer_role in self.old_nodes and self.old_nodes[observer_role]

        if observer_has_new or observer_has_old:
            observer_replace_pipeline = SubBuilder(root_id=self.root_id, data=replace_data)

            # --- Observer 扩容 ---
            if observer_has_new:
                obs_scale_up_nodes = {observer_role: self.new_nodes[observer_role]}

                obs_scale_up_data = self.get_flow_base_data()
                obs_scale_up_data["nodes"] = obs_scale_up_nodes
                obs_scale_up_data["ticket_type"] = TicketType.DORIS_SCALE_UP.value
                obs_scale_up_data["master_fe_ip"] = active_target_ip
                obs_scale_up_data["host_meta_map"] = make_meta_host_map(obs_scale_up_data)

                obs_scale_up_sub = SubBuilder(root_id=self.root_id, data=obs_scale_up_data)

                obs_up_kwargs = DorisActKwargs(bk_cloud_id=self.bk_cloud_id)
                obs_up_kwargs.set_trans_data_dataclass = DorisApplyContext.__name__

                obs_scale_up_sub.add_act(
                    act_name=_("获取Payload"),
                    act_component_code=GetDorisActPayloadComponent.code,
                    kwargs=asdict(obs_up_kwargs),
                )

                # ADD OBSERVER 元数据
                obs_up_kwargs.exec_ip = obs_scale_up_data["master_fe_ip"]
                obs_up_kwargs.get_doris_payload_func = DorisActPayload.get_add_metadata_payload.__name__
                obs_scale_up_sub.add_act(
                    act_name=_("Observer集群元数据更新"),
                    act_component_code=ExecuteDorisActuatorScriptComponent.code,
                    kwargs=asdict(obs_up_kwargs),
                )

                # 启动新 Observer（helper 启动 → supervisor 接管）
                obs_up_kwargs.get_doris_payload_func = DorisActPayload.get_start_fe_by_helper_payload.__name__
                for node in self.new_nodes[observer_role]:
                    obs_up_kwargs.exec_ip = node["ip"]
                    obs_up_kwargs.doris_role = observer_role
                    obs_scale_up_sub.add_act(
                        act_name=_("helper启动新Observer-{}").format(node["ip"]),
                        act_component_code=ExecuteDorisActuatorScriptComponent.code,
                        kwargs=asdict(obs_up_kwargs),
                    )
                    obs_up_kwargs.get_doris_payload_func = DorisActPayload.get_install_doris_payload.__name__
                    obs_scale_up_sub.add_act(
                        act_name=_("supervisor接管新Observer-{}").format(node["ip"]),
                        act_component_code=ExecuteDorisActuatorScriptComponent.code,
                        kwargs=asdict(obs_up_kwargs),
                    )
                    obs_up_kwargs.get_doris_payload_func = DorisActPayload.get_start_fe_by_helper_payload.__name__

                # 检查新 Observer 启动
                for node in self.new_nodes[observer_role]:
                    obs_up_kwargs.exec_ip = node["ip"]
                    obs_up_kwargs.doris_role = observer_role
                    obs_up_kwargs.get_doris_payload_func = DorisActPayload.get_check_start_payload.__name__
                    obs_scale_up_sub.add_act(
                        act_name=_("检查新Observer启动-{}").format(node["ip"]),
                        act_component_code=ExecuteDorisActuatorScriptComponent.code,
                        kwargs=asdict(obs_up_kwargs),
                    )

                # 写 DBMeta（scale_up 把新 Observer 写入 DBMeta）
                obs_scale_up_sub.add_act(
                    act_name=_("添加到DBMeta"),
                    act_component_code=DorisMetaComponent.code,
                    kwargs=asdict(obs_up_kwargs),
                )

                # 更新域名：基于 DBMeta 按优先级重算（有 Observer 则只绑 Observer，
                # 自动把 Follower 从域名中移除）
                obs_scale_up_sub.add_act(
                    act_name=_("更新域名"),
                    act_component_code=DorisDnsManageComponent.code,
                    kwargs={
                        "bk_cloud_id": self.bk_cloud_id,
                        "dns_op_type": DnsOpType.UPDATE,
                        "domain_name": self.domain,
                        "dns_op_exec_port": self.http_port,
                    },
                )

                observer_replace_pipeline.add_sub_pipeline(
                    sub_flow=obs_scale_up_sub.build_sub_process(sub_name=_("Observer扩容"))
                )

            # --- Observer 缩容 ---
            if observer_has_old:
                obs_shrink_nodes = {observer_role: self.old_nodes[observer_role]}

                obs_shrink_data = self.get_flow_base_data()
                obs_shrink_data["nodes"] = obs_shrink_nodes
                obs_shrink_data["ticket_type"] = TicketType.DORIS_SHRINK.value
                obs_shrink_data["master_fe_ip"] = active_target_ip
                obs_shrink_data["host_meta_map"] = make_fe_map_from_ticket({"nodes": obs_shrink_nodes})

                obs_shrink_sub = SubBuilder(root_id=self.root_id, data=obs_shrink_data)

                obs_down_kwargs = DorisActKwargs(bk_cloud_id=self.bk_cloud_id)
                obs_down_kwargs.set_trans_data_dataclass = DorisApplyContext.__name__

                obs_shrink_sub.add_act(
                    act_name=_("获取Payload"),
                    act_component_code=GetDorisActPayloadComponent.code,
                    kwargs=asdict(obs_down_kwargs),
                )

                # 从域名移除旧 Observer（必须在停止旧 Observer 之前完成，
                # 确保客户端不会再解析到即将下线的旧 Observer）
                old_observer_ips = [node["ip"] for node in self.old_nodes[observer_role]]
                obs_shrink_sub.add_act(
                    act_name=_("更新域名"),
                    act_component_code=DorisDnsManageComponent.code,
                    kwargs={
                        "bk_cloud_id": self.bk_cloud_id,
                        "dns_op_type": DnsOpType.ADD_AND_DELETE,
                        "domain_name": self.domain,
                        "dns_op_exec_port": self.http_port,
                        "add_ips": [],
                        "del_ips": old_observer_ips,
                    },
                )

                # 并行停止旧 Observer 进程
                stop_obs_acts = []
                for fe_node in self.old_nodes[observer_role]:
                    obs_down_kwargs.exec_ip = fe_node["ip"]
                    obs_down_kwargs.doris_role = observer_role
                    obs_down_kwargs.get_doris_payload_func = DorisActPayload.get_stop_process_payload.__name__
                    stop_obs_acts.append(
                        {
                            "act_name": _("停止DorisObserver-{}").format(fe_node["ip"]),
                            "act_component_code": ExecuteDorisActuatorScriptComponent.code,
                            "kwargs": asdict(obs_down_kwargs),
                        }
                    )
                if stop_obs_acts:
                    obs_shrink_sub.add_parallel_acts(acts_list=stop_obs_acts)

                # 删除旧 Observer 元数据
                obs_down_kwargs.exec_ip = obs_shrink_data["master_fe_ip"]
                obs_down_kwargs.get_doris_payload_func = DorisActPayload.get_drop_metadata_payload.__name__
                obs_shrink_sub.add_act(
                    act_name=_("集群元数据更新-drop-observer"),
                    act_component_code=ExecuteDorisActuatorScriptComponent.code,
                    kwargs=asdict(obs_down_kwargs),
                )

                # 更新 DBMeta
                obs_shrink_sub.add_act(
                    act_name=_("更新DBMeta"),
                    act_component_code=DorisMetaComponent.code,
                    kwargs=asdict(obs_down_kwargs),
                )

                observer_replace_pipeline.add_sub_pipeline(
                    sub_flow=obs_shrink_sub.build_sub_process(sub_name=_("Observer缩容"))
                )

            doris_pipeline.add_sub_pipeline(
                sub_flow=observer_replace_pipeline.build_sub_process(sub_name=_("Observer替换"))
            )

        # ================================================================
        # Pipeline 3: Follower 滚动替换
        # Follower 参与选主，必须逐个滚动替换，保证集群始终有足够可用节点。
        # 每轮：ADD 新 → 启动 → 检查 → 更新DNS(仅无observer时) → 停旧 → DROP旧 → 更新DBMeta
        # ================================================================
        follower_replace_order = self.__get_follower_replace_order()

        if follower_replace_order:
            follower_replace_pipeline = SubBuilder(root_id=self.root_id, data=replace_data)

            for idx, (old_ip, new_ip, role) in enumerate(follower_replace_order):
                logger.info(
                    "Follower rolling replace [%d/%d]: old=%s new=%s target=%s",
                    idx + 1,
                    len(follower_replace_order),
                    old_ip,
                    new_ip,
                    active_target_ip,
                )

                iter_data = copy.deepcopy(replace_data)
                iter_data["master_fe_ip"] = active_target_ip
                iter_data["host_meta_map"] = {role: [new_ip]}
                iter_data["host_meta_map_del"] = {role: [old_ip]}
                iter_data["master_fe_ip_del"] = new_ip
                iter_data["new_nodes"] = {role: [{"ip": new_ip}]}
                iter_data["old_nodes"] = {role: [{"ip": old_ip}]}
                iter_data["ticket_type"] = TicketType.DORIS_REPLACE.value

                rolling_pipeline = SubBuilder(root_id=self.root_id, data=iter_data)

                rolling_kwargs = DorisActKwargs(bk_cloud_id=self.bk_cloud_id)
                rolling_kwargs.set_trans_data_dataclass = DorisApplyContext.__name__

                rolling_pipeline.add_act(
                    act_name=_("获取Payload"),
                    act_component_code=GetDorisActPayloadComponent.code,
                    kwargs=asdict(rolling_kwargs),
                )

                # ADD 新 Follower 元数据
                rolling_kwargs.exec_ip = active_target_ip
                rolling_kwargs.get_doris_payload_func = DorisActPayload.get_add_metadata_payload.__name__
                rolling_pipeline.add_act(
                    act_name=_("添加新Follower元数据-{}").format(new_ip),
                    act_component_code=ExecuteDorisActuatorScriptComponent.code,
                    kwargs=asdict(rolling_kwargs),
                )

                # 启动新 Follower
                rolling_kwargs.exec_ip = new_ip
                rolling_kwargs.doris_role = role
                rolling_kwargs.get_doris_payload_func = DorisActPayload.get_start_fe_by_helper_payload.__name__
                rolling_pipeline.add_act(
                    act_name=_("helper启动新Follower-{}").format(new_ip),
                    act_component_code=ExecuteDorisActuatorScriptComponent.code,
                    kwargs=asdict(rolling_kwargs),
                )
                rolling_kwargs.get_doris_payload_func = DorisActPayload.get_install_doris_payload.__name__
                rolling_pipeline.add_act(
                    act_name=_("supervisor接管新Follower-{}").format(new_ip),
                    act_component_code=ExecuteDorisActuatorScriptComponent.code,
                    kwargs=asdict(rolling_kwargs),
                )

                # 检查新 Follower 启动
                rolling_kwargs.get_doris_payload_func = DorisActPayload.get_check_start_payload.__name__
                rolling_pipeline.add_act(
                    act_name=_("检查新Follower启动-{}").format(new_ip),
                    act_component_code=ExecuteDorisActuatorScriptComponent.code,
                    kwargs=asdict(rolling_kwargs),
                )

                # 更新 FE 域名：一步完成加入新 Follower + 移除旧 Follower
                # 必须在停止旧 FE 之前完成，确保客户端不会再解析到即将下线的旧 FE
                if not has_observer_in_dbmeta:
                    rolling_pipeline.add_act(
                        act_name=_("更新FE域名"),
                        act_component_code=DorisDnsManageComponent.code,
                        kwargs={
                            "bk_cloud_id": self.bk_cloud_id,
                            "dns_op_type": DnsOpType.ADD_AND_DELETE,
                            "domain_name": self.domain,
                            "dns_op_exec_port": self.http_port,
                            "add_ips": [new_ip],
                            "del_ips": [old_ip],
                        },
                    )

                # 停止旧 Follower 进程
                rolling_kwargs.exec_ip = old_ip
                rolling_kwargs.doris_role = role
                rolling_kwargs.get_doris_payload_func = DorisActPayload.get_stop_process_payload.__name__
                rolling_pipeline.add_act(
                    act_name=_("停止旧Follower进程-{}").format(old_ip),
                    act_component_code=ExecuteDorisActuatorScriptComponent.code,
                    kwargs=asdict(rolling_kwargs),
                )

                # DROP 旧 Follower 元数据
                rolling_kwargs.exec_ip = new_ip
                rolling_kwargs.get_doris_payload_func = DorisActPayload.get_drop_metadata_for_replace_payload.__name__
                rolling_pipeline.add_act(
                    act_name=_("删除旧Follower元数据-{}").format(old_ip),
                    act_component_code=ExecuteDorisActuatorScriptComponent.code,
                    kwargs=asdict(rolling_kwargs),
                )

                # 更新 DBMeta（单台粒度）
                rolling_pipeline.add_act(
                    act_name=_("更新DBMeta"),
                    act_component_code=DorisMetaComponent.code,
                    kwargs={},
                )

                follower_replace_pipeline.add_sub_pipeline(
                    sub_flow=rolling_pipeline.build_sub_process(
                        sub_name=_(
                            "滚动替换Follower [{}/{}] {}→{}".format(idx + 1, len(follower_replace_order), old_ip, new_ip)
                        )
                    )
                )

                active_target_ip = new_ip
                logger.info(
                    "Follower rolling replace [%d/%d] done, next active_target_ip=%s",
                    idx + 1,
                    len(follower_replace_order),
                    active_target_ip,
                )

            doris_pipeline.add_sub_pipeline(follower_replace_pipeline.build_sub_process(sub_name=_("Follower滚动替换")))

        # ================================================================
        # Pipeline 4: BE 替换（先扩后缩）
        # ================================================================
        be_roles = [DorisRoleEnum.HOT.value, DorisRoleEnum.WARM.value, DorisRoleEnum.COLD.value]
        be_has_new = any(role in self.new_nodes and self.new_nodes[role] for role in be_roles)
        be_has_old = any(role in self.old_nodes and self.old_nodes[role] for role in be_roles)

        if be_has_new or be_has_old:
            be_replace_pipeline = SubBuilder(root_id=self.root_id, data=replace_data)

            # --- BE 扩容 ---
            if be_has_new:
                be_scale_up_new_nodes = {k: v for k, v in self.new_nodes.items() if k in be_roles}

                scale_up_data = self.get_flow_base_data()
                scale_up_data["nodes"] = be_scale_up_new_nodes
                scale_up_data["ticket_type"] = TicketType.DORIS_SCALE_UP.value
                scale_up_data["master_fe_ip"] = active_target_ip
                scale_up_data["host_meta_map"] = make_meta_host_map(scale_up_data)

                scale_up_sub_pipeline = SubBuilder(root_id=self.root_id, data=scale_up_data)

                new_act_kwargs = DorisActKwargs(bk_cloud_id=self.bk_cloud_id)
                new_act_kwargs.set_trans_data_dataclass = DorisApplyContext.__name__

                scale_up_sub_pipeline.add_act(
                    act_name=_("获取Payload"),
                    act_component_code=GetDorisActPayloadComponent.code,
                    kwargs=asdict(new_act_kwargs),
                )

                new_act_kwargs.exec_ip = scale_up_data["master_fe_ip"]
                new_act_kwargs.get_doris_payload_func = DorisActPayload.get_add_metadata_payload.__name__
                scale_up_sub_pipeline.add_act(
                    act_name=_("BE集群元数据更新"),
                    act_component_code=ExecuteDorisActuatorScriptComponent.code,
                    kwargs=asdict(new_act_kwargs),
                )

                sub_new_be_acts = self.new_be_sub_acts(act_kwargs=new_act_kwargs, data=scale_up_data)
                if sub_new_be_acts:
                    scale_up_sub_pipeline.add_parallel_acts(acts_list=sub_new_be_acts)

                # 检查新 BE 节点是否已加入集群且 Alive
                new_act_kwargs.exec_ip = scale_up_data["master_fe_ip"]
                new_act_kwargs.get_doris_payload_func = DorisActPayload.get_check_backends_alive_payload.__name__
                scale_up_sub_pipeline.add_act(
                    act_name=_("检查新BE节点状态"),
                    act_component_code=ExecuteDorisActuatorScriptComponent.code,
                    kwargs=asdict(new_act_kwargs),
                )

                scale_up_sub_pipeline.add_act(
                    act_name=_("添加到DBMeta"),
                    act_component_code=DorisMetaComponent.code,
                    kwargs=asdict(new_act_kwargs),
                )

                be_replace_pipeline.add_sub_pipeline(
                    sub_flow=scale_up_sub_pipeline.build_sub_process(sub_name=_("BE扩容"))
                )

            # --- BE 缩容 ---
            if be_has_old:
                be_shrink_old_nodes = {k: v for k, v in self.old_nodes.items() if k in be_roles}

                shrink_data = self.get_flow_base_data()
                shrink_data["nodes"] = be_shrink_old_nodes
                shrink_data["ticket_type"] = TicketType.DORIS_SHRINK.value
                shrink_data["master_fe_ip"] = active_target_ip
                shrink_data["host_meta_map"] = make_be_map_from_ticket({"nodes": be_shrink_old_nodes})

                shrink_sub_pipeline = SubBuilder(root_id=self.root_id, data=shrink_data)

                shrink_act_kwargs = DorisActKwargs(bk_cloud_id=shrink_data["bk_cloud_id"])
                shrink_act_kwargs.set_trans_data_dataclass = DorisApplyContext.__name__

                shrink_sub_pipeline.add_act(
                    act_name=_("获取Payload"),
                    act_component_code=GetDorisActPayloadComponent.code,
                    kwargs=asdict(shrink_act_kwargs),
                )

                # 退役 BE 元数据
                shrink_act_kwargs.exec_ip = shrink_data["master_fe_ip"]
                shrink_act_kwargs.get_doris_payload_func = DorisActPayload.get_decommission_metadata_payload.__name__
                shrink_sub_pipeline.add_act(
                    act_name=_("集群元数据更新-退役-BE"),
                    act_component_code=ExecuteDorisActuatorScriptComponent.code,
                    kwargs=asdict(shrink_act_kwargs),
                )

                # 等待数据搬迁完成
                shrink_act_kwargs.get_doris_payload_func = DorisActPayload.get_check_decommission_payload.__name__
                shrink_sub_pipeline.add_act(
                    act_name=_("检查数据节点是否退役"),
                    act_component_code=ExecuteDorisActuatorScriptComponent.code,
                    kwargs=asdict(shrink_act_kwargs),
                )

                # 删除 BE 元数据
                shrink_act_kwargs.get_doris_payload_func = DorisActPayload.get_force_drop_metadata_payload.__name__
                shrink_sub_pipeline.add_act(
                    act_name=_("集群元数据更新-删除-BE"),
                    act_component_code=ExecuteDorisActuatorScriptComponent.code,
                    kwargs=asdict(shrink_act_kwargs),
                )

                # 并行停止旧 BE 进程
                stop_be_acts = []
                for role, role_nodes in be_shrink_old_nodes.items():
                    if role in be_roles:
                        for be_node in role_nodes:
                            shrink_act_kwargs.exec_ip = be_node["ip"]
                            shrink_act_kwargs.doris_role = role
                            shrink_act_kwargs.get_doris_payload_func = (
                                DorisActPayload.get_stop_process_payload.__name__
                            )
                            stop_be_acts.append(
                                {
                                    "act_name": _("停止DorisBE-{}-{}").format(role, be_node["ip"]),
                                    "act_component_code": ExecuteDorisActuatorScriptComponent.code,
                                    "kwargs": asdict(shrink_act_kwargs),
                                }
                            )
                if stop_be_acts:
                    shrink_sub_pipeline.add_parallel_acts(acts_list=stop_be_acts)

                # 更新 DBMeta
                shrink_sub_pipeline.add_act(
                    act_name=_("更新DBMeta"),
                    act_component_code=DorisMetaComponent.code,
                    kwargs=asdict(shrink_act_kwargs),
                )

                be_replace_pipeline.add_sub_pipeline(
                    sub_flow=shrink_sub_pipeline.build_sub_process(sub_name=_("BE缩容"))
                )

            doris_pipeline.add_sub_pipeline(sub_flow=be_replace_pipeline.build_sub_process(sub_name=_("BE替换")))

        # ================================================================
        # Pipeline 5: 收尾步骤（清理所有旧节点数据目录）
        # ================================================================
        cleanup_pipeline = SubBuilder(root_id=self.root_id, data=replace_data)

        all_old_cleanup_ips = get_all_node_ips_in_ticket(data={"nodes": self.old_nodes})

        cleanup_kwargs = DorisActKwargs(bk_cloud_id=self.bk_cloud_id)
        cleanup_kwargs.set_trans_data_dataclass = DorisApplyContext.__name__

        cleanup_pipeline.add_act(
            act_name=_("获取Payload"),
            act_component_code=GetDorisActPayloadComponent.code,
            kwargs=asdict(cleanup_kwargs),
        )

        if all_old_cleanup_ips:
            cleanup_acts = []
            for ip in all_old_cleanup_ips:
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
