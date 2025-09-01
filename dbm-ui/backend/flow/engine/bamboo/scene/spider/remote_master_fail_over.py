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
import logging
from typing import Any, Dict, List

from django.utils.translation import ugettext as _

from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.spider.remote_master_slave_swtich import RemoteMasterSlaveSwitchFlow
from backend.flow.utils.mysql.mysql_context_dataclass import SpiderSwitchContext

logger = logging.getLogger("flow")

# 常量定义
DEFAULT_FORCE_FAILOVER = True


class RemoteMasterFailOverFlow(RemoteMasterSlaveSwitchFlow):
    """TenDB Cluster集群remote存储主故障切换流程类.

    继承自RemoteMasterSlaveSwitchFlow，复用大部分主从切换逻辑，但针对故障切换场景做了特殊处理。

    主要特性:
        - 故障切换时不需要执行从节点切换操作（add_slave_switch_act）
        - 标准化流程只需要处理从节点，不处理已故障的主节点
        - 通过重写关键方法实现差异化处理，同时保持与父类的兼容性

    Attributes:
        继承父类的所有属性

    Note:
        该类专门用于处理主节点故障的切换场景，与正常的主从切换有所区别
    """

    def remote_fail_over(self) -> None:
        """构建remote主故障切换的流程.

        复用父类的主要流程框架，通过方法重写实现故障切换的特殊逻辑。

        实现原理:
            - 调用父类的公有方法build_cluster_sub_pipelines()
            - 父类方法内部会调用子类重写的_build_single_cluster_pipeline()
            - 实现多态性，无需修改父类代码即可定制子类行为

        Raises:
            Exception: 当流程执行失败时抛出异常
        """
        # 提取集群ID列表
        cluster_ids = self._extract_cluster_ids()

        # 创建主流水线，复用父类逻辑
        switch_pipeline = self._create_main_pipeline(cluster_ids)

        # 构建集群切换映射关系，复用父类逻辑
        cluster_switch_map = self.build_cluster_switch_mapping()

        # 构建子流水线 - 这里会调用子类重写的_build_single_cluster_pipeline()
        sub_pipelines = self.build_cluster_sub_pipelines(cluster_switch_map)

        # 添加并执行流水线
        switch_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        switch_pipeline.run_pipeline(is_drop_random_user=True, init_trans_data_class=SpiderSwitchContext())

    def _build_single_cluster_pipeline(
        self, cluster_id: int, switch_tuples: List[Dict[str, Any]], batch_idx: int
    ) -> Any:
        """构建单个集群的子流水线 - 故障切换定制版本.

        重写父类的私有方法，实现故障切换的特殊逻辑。

        Args:
            cluster_id: 集群ID
            switch_tuples: 切换元组列表，包含主从节点信息
            batch_idx: 批次索引，用于并发控制

        Returns:
            构建好的子流水线对象

        Note:
            与父类的主要区别：
            1. 保留前置检查、下发介质、主节点切换、元数据更新等步骤
            2. 移除从节点切换步骤（add_slave_switch_act） - 故障场景下不需要
            3. 使用定制的标准化流程，只处理从节点
        """
        logger.info(_("构建单个集群的子流水线 - 故障切换定制版本"))
        # 准备子流程上下文
        sub_flow_context = copy.deepcopy(self.data)
        sub_flow_context.pop("infos")

        # 获取集群相关信息 - 复用父类公有方法
        cluster = self.get_cluster_and_validate(cluster_id)
        spiders, ctl_primary = self.get_cluster_components(cluster)

        # 计算检测参数 - 复用父类公有方法
        check_client_conn_inst, verify_checksum_tuples, slave_addr_tuples = self.calculate_check_parameters(
            sub_flow_context, cluster, switch_tuples, spiders
        )

        # 创建子流水线
        sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

        # 添加各个步骤 - 复用父类公有方法
        self.add_pre_check_sub_flow(
            sub_pipeline, sub_flow_context, cluster, check_client_conn_inst, verify_checksum_tuples, slave_addr_tuples
        )
        self.add_download_media_act(sub_pipeline, cluster, ctl_primary)
        self.add_master_switch_act(sub_pipeline, cluster, ctl_primary, cluster_id, switch_tuples, batch_idx)
        # 注意：故障切换场景下不执行从节点切换 - 与父类的主要差异
        # 父类中的 self.add_slave_switch_act() 在这里被省略
        force = self.data.get("force", DEFAULT_FORCE_FAILOVER)  # 故障切换默认强制
        self.add_meta_update_act(sub_pipeline, cluster_id, switch_tuples, force)
        self.add_standardization_flows(sub_pipeline, sub_flow_context, cluster, switch_tuples)

        return sub_pipeline.build_sub_process(sub_name=_("[{}]故障切换".format(cluster.name)))

    def add_standardization_flows(
        self,
        sub_pipeline: SubBuilder,
        sub_flow_context: Dict[str, Any],
        cluster: Any,
        switch_tuples: List[Dict[str, Any]],
    ) -> None:
        """添加标准化流程 - 故障切换定制版本.

        Args:
            sub_pipeline: 子流水线对象
            sub_flow_context: 子流程上下文数据
            cluster: 集群对象
            switch_tuples: 切换元组列表，包含主从节点信息

        Note:
            与父类方法的区别：
            - 父类处理主节点和从节点两种IP
            - 子类只处理从节点IP（因为主节点已故障，无需标准化）
        """
        logger.info(_("添加标准化流程 - 故障切换定制版本"))
        slave_ips = [info["slave"]["ip"] for info in switch_tuples]

        standardization_flows = [self.create_standardization_flow(sub_flow_context, cluster, slave_ips)]
        sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=standardization_flows)
