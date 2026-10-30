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

SQLServer 集群生命周期类摘要预设。

职责：
  - 描述"每个集群一行"的集群生命周期动作结果（下架 / 禁用 / 启用 / 重置）。
  - 通过 table_primary_key = "cluster_domain_and_port" 保证节点重试对同一集群的重复上报走覆盖合并。
  - 本模块同时承载配套的动作枚举 :class:`SqlserverClusterLifecycleAction`（就近共存，便于阅读维护）。

数据源 / 调用通道：
  - 由 SQLServer 生命周期类流程节点（启用 / 禁用 / 下架 / 重置场景）在动作完成后，经通用组件
    :class:`SqlserverFlowOutputSummaryComponent`（preset="cluster_lifecycle"）写入。
  - 集群域名由流程节点从 db_meta（cluster）直接装配；
    下架 / 重置场景的"事后视角不可得"信息（旧域名、卸载实例列表）由 flow 在装配期提前捕获。

边界：
  - action 由枚举 :class:`SqlserverClusterLifecycleAction` 强约束，非法值直接被 ChoiceField 拒绝。
"""

from django.utils.translation import gettext as _
from rest_framework import serializers

from backend.flow.utils.base.flow_output import BaseFlowOutputSerializer
from blue_krill.data_types.enum import EnumField, StrStructuredEnum


class SqlserverClusterLifecycleAction(StrStructuredEnum):
    """SQLServer 集群生命周期动作枚举（对齐 :class:`SqlserverClusterLifecycleSummarySerializer.action` 字段）。

    功能说明：
      - 描述"一次集群级生命周期动作"对应的动作类型；供前端在执行摘要 tab 展示"这一行到底做了什么"，
        并支持按 action 分组 / 过滤。
      - 值为短字符串（写入 FlowSummary），label 经 ``gettext`` 即时求值为 str，符合摘要 JSON 落盘约束。

    取值：
      - DESTROY ("destroy") -> 下架：删除集群并回收全部实例 / 域名 / 元信息
      - DISABLE ("disable") -> 禁用：禁用业务账号、断开业务链接，集群保留
      - ENABLE  ("enable")  -> 启用：重新启用业务账号，集群恢复访问
      - RESET   ("reset")   -> 重置：更换集群域名并清空数据（要求集群先禁用）

    边界：
      - 非枚举值 -> :class:`serializers.ChoiceField` 校验失败，节点显式失败，便于排障；
      - 未来若出现新的生命周期语义，直接在此追加新的枚举项即可。
    """

    DESTROY = EnumField("destroy", _("下架"))
    DISABLE = EnumField("disable", _("禁用"))
    ENABLE = EnumField("enable", _("启用"))
    RESET = EnumField("reset", _("重置"))


class SqlserverClusterLifecycleSummarySerializer(BaseFlowOutputSerializer):
    """SQLServer 集群生命周期摘要（每集群一行）。

    功能说明：
      - 描述集群级生命周期动作结果（下架 / 禁用 / 启用 / 重置），供前端在单据执行摘要 tab 中展示。
      - 通过 `table_primary_key = "cluster_domain_and_port"` 让 FlowOutputHandler.insert_data 在遇到
        相同集群的重复写入时走"后写覆盖前写"分支，天然幂等。

    输入参数（即 data 每一行的字段结构）：
      - cluster_domain_and_port (str, 必填, 非空): 集群主访问入口 `"domain:port"`，作为主键；
        下架 / 重置场景下集群域名会消失或变化，**必须在装配期提前捕获**后再写 items
      - action (str, 必填): 生命周期动作，取值必须在 :class:`SqlserverClusterLifecycleAction` 枚举内
      - extra (str, 可空, 默认 ""): 动作附加信息兜底文本；前端按纯文本渲染。约定：
        * reset: 承载"旧域名 -> 新域名"映射文本（如 "域名变更: old.domain -> new.domain"）
        * destroy: 承载卸载实例列表（如 "卸载实例: 1.2.3.4:1433,5.6.7.8:1433"）

    输出：
      - 写入 FlowSummary.summary 中 table_name = "sqlserver_cluster_lifecycle" 的表 values。

    边界：
      - cluster_domain_and_port / action 缺失 -> is_valid 抛 ValidationError。
      - action 非枚举值 -> ChoiceField 抛校验异常。
      - 重复主键写入 -> 依赖 insert_data 主键合并分支覆盖旧行，行数不变。
    """

    #: 表名（sqlserver 命名空间下唯一，前缀 sqlserver_）
    table_name: str = "sqlserver_cluster_lifecycle"
    #: 前端表格展示名
    table_display_name: str = _("SQLServer 集群生命周期信息")
    #: 表主键：每集群一行，重复写入按 cluster_domain_and_port 覆盖合并
    table_primary_key: str = "cluster_domain_and_port"

    cluster_domain_and_port = serializers.CharField(
        help_text=_("集群主入口(domain:port)"), required=True, allow_blank=False
    )
    action = serializers.ChoiceField(
        help_text=_("生命周期动作"), choices=SqlserverClusterLifecycleAction.get_choices(), required=True
    )
    #: 动作附加信息兜底；前端按纯文本渲染，禁止塞 dict / list 结构化数据
    extra = serializers.CharField(help_text=_("扩展信息"), required=False, allow_blank=True, default="")
