# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

MySQL / Spider 系单据主机退回公共基类 · v2 · F 模型 + 组资源绑定编排骨架。

模块职责：
  - 统一承载 MySQL / Spider 系（HA / Single / MigrateCluster / TenDBCluster 等）单据
    TERMINATED 后的主机退回"顶层编排骨架"：
      · 顶层 try/except 兜底（防阻塞 RECYCLE_APPLY_HOST 主单据）
      · Extractor 产出 ResourceGroup 列表 → 每组构造合并子流程 → 顶层 pipeline 并行执行
  - 各单据类型（HA / Single / Migrate / TenDBCluster）通过**平级继承本基类**接入，
    仅需覆盖两个类属性驱动差异化：``EXTRACTOR_CLASS`` + ``_LOG_PREFIX``

设计要点 / 为什么要抽基类：
  - 原实现中 Single / Migrate / TenDBCluster 继承 :class:`MysqlHaApplyRevokeFlow` 并
    "不覆盖 revoke_flow 方法"：导致 Python 层 ``revoke_flow.__qualname__`` 固化为父类
    ``MysqlHaApplyRevokeFlow.revoke_flow``；而 :class:`CalcRecycleApplyHostParamBuilder.
    build_controller_info` 旧实现依赖 ``__qualname__.split(".")[0]`` 推断 class_name，
    结果反射构造的始终是 HA 父类实例 → 子类覆盖的 ``EXTRACTOR_CLASS`` / ``_LOG_PREFIX``
    永远拿不到，Single 场景的 ticket_data 被 HA Extractor 处理 → TypeError
  - 解决：所有 revoke 子类"平级继承"本基类，彼此没有父子关系；再配合装饰器挂载
    显式类引用（``revoke_flow_class``），彻底摆脱 ``__qualname__`` 推断
  - 本基类**不是**抽象类，继承后至少覆盖 ``EXTRACTOR_CLASS``；未覆盖时 ``_do_revoke_flow``
    会抛 ``TypeError``（``None()`` 实例化）或 ``AttributeError``，让误用在首次 revoke 时暴露

模块边界：
  - ticket_data 必须含 ``uid`` / ``bk_biz_id`` / ``ticket_type``；否则 ``_do_revoke_flow``
    读取时抛 ``KeyError``，由 ``revoke_flow`` 顶层 try/except 统一包装为 Exception
  - Extractor 产出 ``[]``（空候选）→ 抛 Exception"获取不到对应申请资源组"→ 顶层兜底
  - 任何未处理异常 → 以 ``[{_LOG_PREFIX}][{root_id}]`` 前缀封装后 re-raise，便于 ES 按
    子类前缀精确检索
"""
import logging
import traceback
from typing import Any, Dict, List, Type

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.db_services.ipchooser.constants import BkOsTypeCode
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.mysql.common.exceptions import NormalTenDBFlowException
from backend.flow.engine.bamboo.scene.mysql.revoke.base.models import ResourceGroup
from backend.flow.engine.bamboo.scene.mysql.revoke.base.resource_group_revoke_subflow import build_group_revoke_subflow
from backend.flow.engine.bamboo.scene.mysql.revoke.base.trans_data import RevokeTransData
from backend.flow.engine.bamboo.scene.mysql.revoke.extractors.base import HostExtractor
from backend.flow.engine.revoke.base import RevokeFlowBase

logger = logging.getLogger("flow")


class MysqlRevokeFlowBase(RevokeFlowBase):
    """MySQL / Spider 系单据主机退回公共基类 · v2。

    职责：
      - 统一 ``revoke_flow`` 顶层 try/except 兜底
      - 统一 ``_do_revoke_flow`` 编排骨架（Extractor → 分组 → 并行子流程 → 顶层 pipeline）

    子类接入契约：
      - 继承本类（**平级继承**，不要继承具体业务子类如 ``MysqlHaApplyRevokeFlow``）
      - 必须覆盖 ``EXTRACTOR_CLASS``；强烈建议覆盖 ``_LOG_PREFIX``
      - 不要覆盖 ``revoke_flow`` / ``_do_revoke_flow``；特殊场景确有需要时，在子类覆盖
        后仍必须以本类同名方法为唯一真源（最好 ``super().revoke_flow()`` 复用兜底）

    构造入参与 :class:`RevokeFlowBase` 一致：
      - ``root_id``     子单据 flow_obj_id（由 :meth:`Ticket.get_inner_controller_func` 传入）
      - ``ticket_data`` 原单据的 ticket_data 字典

    线程安全：非线程安全（bamboo 单实例执行）
    边界：
      - ticket_data 缺 Extractor 期望字段 → Extractor 返回 [] 或抛业务异常 → 顶层兜底
      - 任何未处理异常 → 顶层 try/except 以 ``[{_LOG_PREFIX}][{root_id}]`` 前缀封装后抛出
    """

    #: Extractor 类：子类必须覆盖以绑定对应单据类型的候选资源组提取逻辑
    EXTRACTOR_CLASS: Type[HostExtractor] = None

    #: 日志前缀：子类覆盖以在日志中区分单据类型（HA / Single / MigrateCluster / TenDBCluster）
    _LOG_PREFIX: str = "MysqlRevokeFlowBase"

    def revoke_flow(self) -> None:
        """执行 revoke 主链路：Extractor → 每组编排「4 段合并子流程」→ 并行运行。

        :return: None
        边界：
          - 顶层任何异常均在此处兜底：以 ``[{_LOG_PREFIX}][{root_id}]`` 前缀封装后 re-raise，
            避免阻塞 RECYCLE_APPLY_HOST 主单据
        """
        try:
            self._do_revoke_flow()
        except Exception as err:
            raise Exception(
                "[{}][{}] revoke_flow unexpected error: {}\n{}".format(
                    self._LOG_PREFIX, self.root_id, err, traceback.format_exc(limit=5)
                )
            )

    def _do_revoke_flow(self) -> None:
        """真正执行 revoke 编排。异常由顶层 revoke_flow 兜底捕获。

        :return: None
        边界：
          - Extractor 返回空列表 → 抛 Exception "单据获取不到对应的申请资源组"
          - ticket_data 缺 ``uid`` / ``bk_biz_id`` / ``ticket_type`` → KeyError
        """
        if not isinstance(self.data, dict):
            raise NormalTenDBFlowException(message="ticket_data is not dict: type={}".format(type(self.data).__name__))

        ticket_id: int = int(self.data["uid"])
        bk_biz_id: int = int(self.data["bk_biz_id"])

        # ---- 1. Extractor 提取候选资源组 ----
        groups: List[ResourceGroup] = self.EXTRACTOR_CLASS().extract(self.data)
        if not groups:
            raise Exception(_("单据获取不到对应的申请资源组"))

        # ---- 2. 顶层 pipeline 并行编排每组的合并子流程 ----
        # 关键字段说明：
        #   - ``uid``：bamboo 框架契约字段，写入 FlowTree.uid / FlowNode.uid；数值 = ticket_id
        #   - ``ticket_type`` / ``created_by`` / ``bk_biz_id``：Builder.run_pipeline 写 FlowTree 时强依赖，
        #     必须从 self.data（即 revoke_flow 入参的 ticket_data）透传；否则 KeyError。
        #   - ``db_type`` / ``os_type``：供清理 Service（如 ClearMachineScript）用；不进 FlowTree。
        #   - ticket_id 不放 global_data：本 flow 内业务 Service 通过 build_group_revoke_subflow(ticket_id=)
        #     显式入参 + act.kwargs 传递，无需走 global_data；避免与 uid 冗余（数值等价）。
        #
        # 关于 db_type 固定为 ``DBType.MySQL.value`` 的演进说明（务必读完再改）：
        #   - 当前 MySQL 系 revoke 仅在 ``ResourceGroupMachineClearService``（段 4）消费 db_type：
        #       · 查 ``db_type_script_map`` 取清机脚本：MySQL / TenDBCluster 两个 key 均指向
        #         同一个 ``mysql_clear_machine_script`` 字符串常量，运行时 0 差异。
        #       · 查 ``db_type_account_user_map`` 取执行账户：MySQL / TenDBCluster 两个 key
        #         均指向 ``DBA_ROOT_USER``，运行时 0 差异。
        #     因此 TenDBClusterApplyRevokeFlow / Spider 系也统一传 MySQL，不会有副作用。
        #   - 不要在 ``MysqlRevokeFlowBase`` 加 ``DB_TYPE`` 类属性让子类覆盖（flow 粒度静态映射）：
        #     F1~F4 判据链路（host_check.py）已经用 **unit 粒度的 ``unit.cluster_type``**
        #     做业务路由（如 ``BizSettings.get_exact_hosting_biz(..., unit.cluster_type)``、
        #     ``ClusterTypeMachineTypeDefine[cluster_type_enum]``）；若段 4 清机改走 flow 粒度
        #     ``self.db_type``，整条链路会出现两种粒度，且无法应对同一 TenDBCluster revoke flow
        #     内 SPIDER / REMOTE / SPIDER_CTL 需要不同脚本的真实分叉场景。
        #   - 真到需要分叉的那一天（概率上更可能按 machine_type / cluster_type 而非 DBType 分叉），
        #     在 ``build_group_revoke_subflow`` 段 4 的 ``act.kwargs`` 中按 ``group.units[0].cluster_type``
        #     显式注入 ``db_type``（或直接注入脚本名）即可，粒度与 F1~F4 对齐。
        global_data: Dict[str, Any] = {
            "uid": ticket_id,
            "bk_biz_id": bk_biz_id,
            "ticket_type": self.data["ticket_type"],
            "created_by": self.data.get("created_by"),
            "db_type": DBType.MySQL.value,
            "os_type": BkOsTypeCode.LINUX.value,
        }
        # 说明：trans_data.recycle_hosts 由 RevokeTransData 声明默认 []；
        # 清理 Service 通过 setattr(trans_data, "recycle_hosts", ...) 累计，
        # 无需在此处 global_data 中冗余声明
        top_pipeline = Builder(root_id=self.root_id, data=global_data)

        # 每组构造一个"计算 → 清理"合并子流程；顶层将各组子流程并行执行
        # 合并到同一 SubProcess 是必需的：跨 SubProcess 时 trans_data 无法回写
        group_sub_pipelines: List[Any] = [
            build_group_revoke_subflow(
                root_id=self.root_id,
                ticket_id=ticket_id,
                group=group,
                global_data=global_data,
            )
            for group in groups
        ]

        top_pipeline.add_parallel_sub_pipeline(sub_flow_list=group_sub_pipelines)

        # 关键：显式注入 RevokeTransData 作为 trans_data 初值
        top_pipeline.run_pipeline(init_trans_data_class=RevokeTransData())
