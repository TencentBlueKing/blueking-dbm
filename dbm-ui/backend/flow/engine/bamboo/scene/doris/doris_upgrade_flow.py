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

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import InstanceRole
from backend.flow.consts import DorisRoleEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.doris.doris_base_flow import DorisBaseFlow
from backend.flow.engine.bamboo.scene.doris.exceptions import MasterNotFoundException
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.doris.doris_db_meta import DorisMetaComponent
from backend.flow.plugins.components.collections.doris.exec_doris_actuator_script import (
    ExecuteDorisActuatorScriptComponent,
)
from backend.flow.plugins.components.collections.doris.get_doris_payload import GetDorisActPayloadComponent
from backend.flow.plugins.components.collections.doris.rewrite_doris_config import WriteBackDorisConfigComponent
from backend.flow.plugins.components.collections.doris.trans_files import TransFileComponent
from backend.flow.utils.doris.doris_act_payload import DorisActPayload
from backend.flow.utils.doris.doris_context_dataclass import DorisActKwargs, DorisApplyContext
from backend.flow.utils.doris.master_resolver import get_cluster_master

logger = logging.getLogger("flow")


class DorisUpgradeFlow(DorisBaseFlow):
    """
    构建Doris集群原地升级流程
    升级顺序：先升级BE节点，再升级非Master的FE节点，最后升级Master FE节点
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        :param root_id: 任务流程定义的root_id
        :param data: 单据传递过来的参数列表，字典格式
        """
        super().__init__(root_id, data)
        self.data = data
        self.new_version = data.get("new_version")

    def __get_flow_data(self) -> dict:
        """
        构建flow运行所需的数据结构
        master_fe_ip 获取策略:
            1. 优先从监控缓存(周期任务从蓝鲸监控同步)获取实时master
            2. 缓存不存在时，降级使用 dbmeta 中 follower 列表的第一台
        """
        flow_data = self.get_flow_base_data()
        flow_data["new_version"] = self.new_version
        flow_data["master_fe_ip"] = self.__resolve_master_fe_ip()
        return flow_data

    def __resolve_master_fe_ip(self) -> str:
        """
        解析当前集群真实的 master FE IP
        优先从监控缓存中获取(周期任务每小时同步一次, cache key 由 sync_cluster_master 周期任务维护)
        缓存中存的格式为 "ip:port"，需要转换为纯 ip
        若缓存命中失败, 降级使用 dbmeta 中的 follower_ips[0]
        """
        try:
            cached_master = get_cluster_master(bk_biz_id=self.bk_biz_id, cluster_domain=self.domain)
            cached_master_ip = cached_master.split(":")[0] if cached_master else ""
        except Exception as e:
            logger.warning("get master from monitor cache failed, fallback to dbmeta. err=%s", e)
            cached_master_ip = ""

        # 校验缓存中的 master 必须存在于 dbmeta 的 follower 列表中, 防止角色漂移导致升级到非预期节点
        follower_ips = self.get_role_ips_in_dbmeta(InstanceRole.DORIS_FOLLOWER)
        if cached_master_ip and cached_master_ip in follower_ips:
            logger.info("resolved master_fe_ip from monitor cache: %s", cached_master_ip)
            return cached_master_ip

        if cached_master_ip and cached_master_ip not in follower_ips:
            logger.warning(
                "cached master_ip %s not in dbmeta follower list %s, fallback to follower_ips[0]",
                cached_master_ip,
                follower_ips,
            )

        fallback_ip = self.follower_ips[0] if self.follower_ips else ""
        if not fallback_ip:
            raise MasterNotFoundException(domain=self.domain)
        logger.info("resolved master_fe_ip from dbmeta fallback: %s", fallback_ip)
        return fallback_ip

    def upgrade_doris_flow(self):
        """
        Doris集群原地升级主流程
        流程编排：前置检查 → 介质下发解压 → 逐节点升级BE → 逐节点升级FE → 元数据更新 → 升级后验证
        """
        upgrade_data = self.__get_flow_data()
        doris_pipeline = Builder(root_id=self.root_id, data=upgrade_data)
        trans_files = GetFileList(db_type=DBType.Doris)

        # 拼接活动节点需要的私有参数
        act_kwargs = DorisActKwargs(bk_cloud_id=self.bk_cloud_id)
        act_kwargs.set_trans_data_dataclass = DorisApplyContext.__name__

        # ===== 阶段1: 获取集群Payload =====
        doris_pipeline.add_act(
            act_name=_("获取集群部署配置"), act_component_code=GetDorisActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )

        # ===== 阶段2: 下发actuator和新版本介质包到所有节点 =====
        all_ips = self.get_all_node_ips_in_dbmeta()
        act_kwargs.exec_ip = all_ips
        act_kwargs.file_list = trans_files.doris_apply(db_version=self.new_version)
        doris_pipeline.add_act(
            act_name=_("下发升级介质包"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
        )

        # ===== 阶段3: 解压新版本介质包并渲染配置 =====
        sub_pipelines = []
        for instance_role, doris_role in self.INSTANCE_ROLE_DORIS_ROLE_MAP.items():
            for ip in self.get_role_ips_in_dbmeta(instance_role):
                sub_pipeline = SubBuilder(root_id=self.root_id, data=upgrade_data)
                act_kwargs.exec_ip = ip
                act_kwargs.doris_role = doris_role
                # 解压缩
                act_kwargs.get_doris_payload_func = DorisActPayload.get_decompress_pkg_v2_payload.__name__
                sub_pipeline.add_act(
                    act_name=_("解压介质包-{}").format(ip),
                    act_component_code=ExecuteDorisActuatorScriptComponent.code,
                    kwargs=asdict(act_kwargs),
                )
                # 渲染集群配置（升级场景使用V2，传入new_version渲染到新版本目录）
                act_kwargs.get_doris_payload_func = DorisActPayload.get_render_config_v2_payload.__name__
                sub_pipeline.add_act(
                    act_name=_("渲染集群配置-{}").format(ip),
                    act_component_code=ExecuteDorisActuatorScriptComponent.code,
                    kwargs=asdict(act_kwargs),
                )
                sub_pipelines.append(
                    sub_pipeline.build_sub_process(sub_name=_("解压并渲染配置-{}-{}").format(doris_role, ip))
                )
        doris_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        # ===== 阶段4: 人工确认后开始升级BE =====
        doris_pipeline.add_act(act_name=_("人工确认执行升级"), act_component_code=PauseComponent.code, kwargs={})

        # 升级BE：按 cold → warm → hot 顺序逐节点串行升级
        be_role_order = [
            (InstanceRole.DORIS_BACKEND_COLD, DorisRoleEnum.COLD.value),
            (InstanceRole.DORIS_BACKEND_WARM, DorisRoleEnum.WARM.value),
            (InstanceRole.DORIS_BACKEND_HOT, DorisRoleEnum.HOT.value),
        ]
        be_sub_pipeline = SubBuilder(root_id=self.root_id, data=upgrade_data)
        for instance_role, doris_role in be_role_order:
            for ip in self.get_role_ips_in_dbmeta(instance_role):
                act_kwargs.exec_ip = ip
                act_kwargs.doris_role = doris_role
                act_kwargs.get_doris_payload_func = DorisActPayload.get_upgrade_node_payload.__name__
                be_sub_pipeline.add_act(
                    act_name=_("升级BE-{}-{}").format(doris_role, ip),
                    act_component_code=ExecuteDorisActuatorScriptComponent.code,
                    kwargs=asdict(act_kwargs),
                )
        doris_pipeline.add_sub_pipeline(sub_flow=be_sub_pipeline.build_sub_process(sub_name=_("逐节点升级BE子流程")))

        # ===== 阶段5: 逐节点升级FE =====
        # 升级FE：按 observer → 非master follower → master follower 顺序逐节点串行升级
        # master_ip 取自 __get_flow_data() 阶段从监控缓存解析的实时 master
        master_ip = upgrade_data["master_fe_ip"]
        observer_ips = self.get_role_ips_in_dbmeta(InstanceRole.DORIS_OBSERVER)
        follower_ips = self.get_role_ips_in_dbmeta(InstanceRole.DORIS_FOLLOWER)

        # 构造完整的 FE 升级有序队列: observer → 非master follower → master follower
        fe_upgrade_queue = []
        for ip in observer_ips:
            fe_upgrade_queue.append((DorisRoleEnum.OBSERVER.value, ip))
        # 用列表推导排除 master_ip, 避免 list.remove() 在 master_ip 不在列表时抛 ValueError
        non_master_followers = [ip for ip in follower_ips if ip != master_ip]
        for ip in non_master_followers:
            fe_upgrade_queue.append((DorisRoleEnum.FOLLOWER.value, ip))
        # master 必须放在队列末尾, 减少升级期间主动切主次数
        if master_ip:
            fe_upgrade_queue.append((DorisRoleEnum.FOLLOWER.value, master_ip))

        fe_sub_pipeline = SubBuilder(root_id=self.root_id, data=upgrade_data)
        for doris_role, ip in fe_upgrade_queue:
            act_kwargs.exec_ip = ip
            act_kwargs.doris_role = doris_role
            act_kwargs.get_doris_payload_func = DorisActPayload.get_upgrade_node_payload.__name__
            fe_sub_pipeline.add_act(
                act_name=_("升级FE-{}-{}").format(doris_role, ip),
                act_component_code=ExecuteDorisActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )
            act_kwargs.get_doris_payload_func = DorisActPayload.get_check_start_payload.__name__
            fe_sub_pipeline.add_act(
                act_name=_("验证FE升级-{}-{}").format(doris_role, ip),
                act_component_code=ExecuteDorisActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )
        doris_pipeline.add_sub_pipeline(sub_flow=fe_sub_pipeline.build_sub_process(sub_name=_("逐节点升级FE子流程")))

        # ===== 阶段6: 更新DBConfig和DBMeta =====
        # 6.1 回写DBConfig，将conf_file切换到新版本
        doris_pipeline.add_act(
            act_name=_("回写集群配置信息"), act_component_code=WriteBackDorisConfigComponent.code, kwargs=asdict(act_kwargs)
        )

        # 6.2 更新DBMeta中集群的major_version为new_version
        doris_pipeline.add_act(
            act_name=_("更新DBMeta版本信息"), act_component_code=DorisMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        doris_pipeline.run_pipeline()
