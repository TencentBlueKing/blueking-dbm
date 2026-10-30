# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

------------------------------------------------------------------------------

SQLServer 实例变更类摘要预设。

职责：
  - 描述"每个集群一行"的实例级变更结果（添加Slave / 原地重建 / 新机重建 / 主从互切 / 主故障切换 / 集群迁移）。
  - 通过 table_primary_key = "cluster_domain_and_port" 保证节点重试对同一集群的重复上报走覆盖合并。
  - 本模块同时承载配套的动作枚举 :class:`SqlserverInstanceChangeAction`（就近共存，便于阅读维护）。

设计要点（与 mysql 预设的关键差异，需自定义而非继承）：
  - mysql 的 :class:`InstanceChangeSummarySerializer` 以 instance (IP:Port) 做主键，依赖
    "同业务同 IP:Port 唯一归属一个集群"的 db_meta 约束；SQLServer 的一台新机可同时承载多个
    集群的 slave 实例（add_slave / migrate 单机多集群），instance 不跨集群唯一，故改用
    `cluster_domain_and_port` 做主键，一台新机挂 N 个集群即产生 N 行。
  - "旧实例 / 原 master"通过对端字段 ``peer_old_instance`` 承载，语义对齐 mysql 的 ``related_instance``。

数据源 / 调用通道：
  - 由 SQLServer 实例变更类流程节点在变更动作完成后，经通用组件
    :class:`SqlserverFlowOutputSummaryComponent`（preset="instance_change"）写入。
  - 切换 / 迁移场景元数据已发生互换或回收，旧实例信息**必须在装配期提前捕获**后再写 items。

边界：
  - new_instance / peer_old_instance 字段走 BaseFlowOutputSerializer.InstanceField，格式必须为 IP:Port。
  - action 由枚举 :class:`SqlserverInstanceChangeAction` 强约束，非法值直接被 ChoiceField 拒绝。
"""

from django.utils.translation import gettext as _
from rest_framework import serializers

from backend.flow.utils.base.flow_output import BaseFlowOutputSerializer
from blue_krill.data_types.enum import EnumField, StrStructuredEnum


class SqlserverInstanceChangeAction(StrStructuredEnum):
    """SQLServer 实例变更动作枚举（对齐 :class:`SqlserverInstanceChangeSummarySerializer.action` 字段）。

    功能说明：
      - 描述"一次实例级变更"对应的动作类型；供前端在执行摘要 tab 展示"这一行到底做了什么"，
        并支持按 action 分组 / 过滤。
      - 值为短字符串（写入 FlowSummary），label 经 ``gettext`` 即时求值为 str，符合摘要 JSON 落盘约束。

    取值：
      - ADD_SLAVE    ("add_slave")    -> 添加Slave：新 slave 实例加入集群
      - REBUILD_LOCAL ("rebuild_local") -> 原地重建Slave：在原 slave 机器上修复实例
      - REBUILD_NEW   ("rebuild_new")   -> 新机重建Slave：新机顶替旧 slave（同一行以 peer_old_instance 表达旧 slave）
      - SWITCH       ("switch")       -> 主从互切：master 与 slave 角色互换
      - FAILOVER     ("failover")     -> 主故障切换：原 master 异常，强制提升 slave
      - MIGRATE      ("migrate")      -> 集群迁移：整机 / 集群维度迁往新机

    边界：
      - 非枚举值 -> :class:`serializers.ChoiceField` 校验失败，节点显式失败，便于排障；
      - 未来若出现"缩容下架"等新语义，直接在此追加新的枚举项即可。
    """

    ADD_SLAVE = EnumField("add_slave", _("添加Slave"))
    REBUILD_LOCAL = EnumField("rebuild_local", _("原地重建Slave"))
    REBUILD_NEW = EnumField("rebuild_new", _("新机重建Slave"))
    SWITCH = EnumField("switch", _("主从互切"))
    FAILOVER = EnumField("failover", _("主故障切换"))
    MIGRATE = EnumField("migrate", _("集群迁移"))


class SqlserverInstanceChangeSummarySerializer(BaseFlowOutputSerializer):
    """SQLServer 实例变更明细摘要（每集群一行）。

    功能说明：
      - 描述集群维度的实例变更结果（加从 / 重建 / 切换 / 迁移等），每条记录对应一个集群的一次动作。
      - 通过 `table_primary_key = "cluster_domain_and_port"` 让 FlowOutputHandler.insert_data 在遇到
        相同集群的重复写入时走"后写覆盖前写"分支，天然幂等；同一台新机挂多个集群时按集群各成一行。
      - "变更后的实例"由 ``new_instance`` 承载；"被顶替 / 原角色实例"由 ``peer_old_instance`` 承载，
        避免"一次替换要拆两行"的冗余。

    输入参数（即 data 每一行的字段结构）：
      - cluster_domain_and_port (str, 必填, 非空): 集群主访问入口 `"domain:port"`，作为主键
      - new_instance (str, 必填, IP:Port): 变更后的实例标识（新 slave / 新 master），格式由 InstanceField 强校验
      - action (str, 必填): 变更动作，取值必须在 :class:`SqlserverInstanceChangeAction` 枚举内
      - peer_old_instance (str, 可选, 默认空串): 旧实例(IP:Port)；承载被顶替的旧实例——
        rebuild_new 为旧 slave、switch/failover 为原 master、migrate 为旧 master；其余动作留空
      - extra (str, 可选, 默认 ""): 变更附加信息兜底文本；前端按纯文本渲染。约定：
        migrate 承载"旧standby -> 新standby"与同步模式（AlwaysOn/Mirroring）等

    输出：
      - 写入 FlowSummary.summary 中 table_name = "sqlserver_instance_change" 的表 values。

    边界：
      - cluster_domain_and_port / new_instance / action 缺失 -> is_valid 抛 ValidationError。
      - new_instance / peer_old_instance 格式非 IP:Port -> InstanceField.run_validators 抛校验异常。
      - action 非枚举值 -> ChoiceField 抛校验异常。
      - 重复主键写入 -> 依赖 insert_data 主键合并分支覆盖旧行，行数不变。
    """

    #: 表名（sqlserver 命名空间下唯一，前缀 sqlserver_）
    table_name: str = "sqlserver_instance_change"
    #: 前端表格展示名
    table_display_name: str = _("SQLServer 实例变更明细")
    #: 表主键：每集群一行；SQLServer 一台新机可挂多集群，instance 不跨集群唯一，故以集群维度承载幂等
    table_primary_key: str = "cluster_domain_and_port"

    cluster_domain_and_port = serializers.CharField(
        help_text=_("集群主入口(domain:port)"), required=True, allow_blank=False
    )
    new_instance = BaseFlowOutputSerializer.InstanceField(
        help_text=_("新实例(IP:Port)"), required=True, allow_blank=False
    )
    action = serializers.ChoiceField(
        help_text=_("变更动作"), choices=SqlserverInstanceChangeAction.get_choices(), required=True
    )
    #: 对端实例(IP:Port)；rebuild_new 为旧 slave、switch/failover/migrate 为原 master，其余动作留空
    peer_old_instance = BaseFlowOutputSerializer.InstanceField(
        help_text=_("旧实例(IP:Port)"), required=False, allow_blank=True, default=""
    )
    #: 变更附加信息兜底；前端按纯文本渲染，禁止塞 dict / list 结构化数据
    extra = serializers.CharField(help_text=_("扩展信息"), required=False, allow_blank=True, default="")
