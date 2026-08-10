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

mysql/spider 实例变更类摘要预设。

职责：
  - 描述"每个实例一行"的实例级变更结果（主从切换 / 扩缩容 / 替换 / 重装 / 迁移等）。
  - 通过 table_primary_key = "instance" (IP:Port) 保证节点重试对同一实例的二次写入走覆盖合并；
    db_meta 约束下一个 IP:Port 在同业务下唯一归属一个集群，所以 instance 单键足以承载幂等。
  - 集群归属通过一等字段 ``cluster_domain`` 承载，避免前端要读 extra 才能分组。
  - 本模块同时承载配套的 action 枚举 :class:`InstanceChangeAction`（就近共存，便于阅读维护）。

数据源 / 调用通道：
  - 由 mysql / spider 变更类流程节点在实例变更动作完成后调用：
    `FlowOutputHandler(InstanceChangeSummarySerializer).insert_data(root_id, data)`。

边界：
  - instance / related_instance 字段走 BaseFlowOutputSerializer.InstanceField，格式必须为 IP:Port，
    否则校验失败。
  - action 由枚举 :class:`InstanceChangeAction` 强约束，非法值直接被 ChoiceField 拒绝。
  - status 语义由业务侧约定字符串（如 success / failed / skipped），本预设不强约束枚举
    （当前接入方仅写 success；失败暂不上报）。
"""

from django.utils.translation import gettext as _
from rest_framework import serializers

from backend.flow.utils.base.flow_output import BaseFlowOutputSerializer
from blue_krill.data_types.enum import EnumField, StrStructuredEnum


class InstanceChangeAction(StrStructuredEnum):
    """实例变更动作枚举（对齐 :class:`InstanceChangeSummarySerializer.action` 字段）。

    功能说明：
      - 描述"一次实例级变更"对应的动作类型；供前端在执行摘要 tab 展示"这一行到底做了什么"，
        并支持按 action 分组 / 过滤。
      - 值为短字符串（写入 FlowSummary），label 经 ``gettext`` 即时求值为 str，符合摘要 JSON 落盘约束。

    取值：
      - ADD    ("add")    -> 扩容上线：把新实例加入集群
      - SWITCH ("switch") -> 替换：一台实例被另一台顶替（同一行以 ``related_instance`` 表达对端）
      - REDUCE ("reduce") -> 缩容下架：把实例从集群移除

    边界：
      - 非枚举值 -> :class:`serializers.ChoiceField` 校验失败，节点显式失败，便于排障；
      - 未来若出现"主从切换 / 重装 / 迁移"等新语义，直接在此追加新的枚举项即可。
    """

    ADD = EnumField("add", _("扩容上线"))
    SWITCH = EnumField("switch", _("替换"))
    REDUCE = EnumField("reduce", _("缩容下架"))


class InstanceChangeSummarySerializer(BaseFlowOutputSerializer):
    """mysql / spider 实例变更明细摘要（每实例一行）。

    功能说明：
      - 描述实例级变更结果（扩缩容 / 替换 / 主从切换 / 重装 / 迁移等），每条记录对应一个实例的一次动作。
      - 通过 `table_primary_key = "instance"` 让 FlowOutputHandler.insert_data 在遇到相同 IP:Port
        的重复写入时走"后写覆盖前写"分支，天然幂等；db_meta 建模保证同业务同 IP:Port 只属于一个集群，
        因此单键 instance 足够。
      - 集群归属由 ``cluster_domain`` 一等字段承载；替换类动作通过 ``related_instance`` 表达对端实例，
        避免"一次替换要拆两行"的冗余。

    输入参数（即 data 每一行的字段结构）：
      - cluster_domain (str, 必填, 非空): 集群不可变域名，一等字段，便于前端按集群分组
      - instance (str, 必填, IP:Port): 变更"当事实例"标识，作为主键，格式由 InstanceField 强校验
      - action (str, 必填): 变更动作，取值必须在 :class:`InstanceChangeAction` 枚举内
      - status (str, 必填, 非空): 结果状态（当前接入方仅写 "success"；失败暂不上报）
      - related_instance (str, 可选, 默认空串): 对端实例(IP:Port)；仅 action=switch 时写入被替换掉
        的旧实例；其余动作留空
      - message (str, 可选, 默认空串): 简短消息 / 错因；不承载业务字段（cluster_domain 已是一等字段）
      - extra (str, 可选, 默认 ""): 单据私有展示文本兜底；前端按纯文本渲染，**不应承载 cluster_domain**
        （会与一等字段冗余）

    输出：
      - 写入 FlowSummary.summary 中 table_name = "mysql_instance_change" 的表 values。

    边界：
      - cluster_domain / instance / action / status 缺失 -> is_valid 抛 ValidationError。
      - instance / related_instance 格式非 IP:Port -> InstanceField.run_validators 抛校验异常。
      - action 非枚举值 -> ChoiceField 抛校验异常。
      - 重复主键（同 instance）写入 -> 依赖 insert_data 主键合并分支覆盖旧行，行数不变。
    """

    #: 表名（mysql/spider 命名空间下唯一，前缀 mysql_）
    table_name: str = "mysql_instance_change"
    #: 前端表格展示名
    table_display_name: str = _("实例变更明细")
    #: 表主键：每实例一行；db_meta 约束下同业务同 IP:Port 唯一归属一个集群，单键足以承载幂等
    table_primary_key: str = "instance"

    cluster_domain = serializers.CharField(help_text=_("集群主域名"), required=True, allow_blank=False)
    instance = BaseFlowOutputSerializer.InstanceField(help_text=_("实例(IP:Port)"), required=True, allow_blank=False)
    action = serializers.ChoiceField(help_text=_("变更动作"), choices=InstanceChangeAction.get_choices(), required=True)
    status = serializers.CharField(help_text=_("结果状态"), required=True, allow_blank=False)
    #: 对端实例(IP:Port)；仅 action=switch 时填被替换下架的旧实例，其余动作留空字符串
    related_instance = BaseFlowOutputSerializer.InstanceField(
        help_text=_("对端实例(IP:Port)"), required=False, allow_blank=True, default=""
    )
    message = serializers.CharField(help_text=_("详细消息"), allow_blank=True, default="")
    #: 单据私有展示文本兜底；前端按纯文本渲染，**禁止承载 cluster_domain**（一等字段已表达），避免冗余
    extra = serializers.CharField(help_text=_("扩展信息"), required=False, allow_blank=True, default="")
