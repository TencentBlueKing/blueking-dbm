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

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.mysql.base import BaseMySQLHATicketFlowBuilder, MySQLBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class MySQLProxyRescueDetailSerializer(MySQLBaseOperateDetailSerializer):
    """
    MySQL Proxy 救援工单参数序列化器（多集群模式）

    支持同时救援多个集群，每条 info 对应一个集群：
    - 有旧 Proxy 元数据：所有原 Proxy 必须不可用
    - 没有旧 Proxy 元数据：需在 info 中提供 proxy_port
    """

    class RescueInfoSerializer(serializers.Serializer):
        """单个集群的救援参数"""

        class NewProxySerializer(serializers.Serializer):
            """新 Proxy 机器信息"""

            ip = serializers.IPAddressField(help_text=_("机器IP地址"), required=True)
            bk_host_id = serializers.IntegerField(help_text=_("主机ID"), required=True)
            bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"), required=True)
            bk_biz_id = serializers.IntegerField(help_text=_("业务ID"), required=True)
            spec = serializers.JSONField(help_text=_("机器规格（需包含 id 字段，用于 DBMeta 记录）"), required=True)

        cluster_id = serializers.IntegerField(help_text=_("需要救援的集群ID"), required=True)
        new_proxies = serializers.ListField(
            help_text=_("新 Proxy 机器列表"), child=NewProxySerializer(), min_length=1, required=True
        )
        # 无旧 Proxy 元数据时必填
        proxy_port = serializers.IntegerField(
            help_text=_("Proxy 端口（集群没有旧 Proxy 元数据时此参数必填）"),
            required=False,
            min_value=3306,
            max_value=65535,
        )
        # 可选：指定版本则使用，否则自动推断
        proxy_version = serializers.CharField(
            help_text=_("Proxy 版本（可选，指定则使用该版本，否则自动从旧 Proxy 获取或使用最新版本）"),
            required=False,
            allow_blank=True,
            max_length=64,
        )
        # 人工确认后是否自动下架旧 Proxy
        auto_cleanup_old_proxies = serializers.BooleanField(
            help_text=_("人工确认后是否自动下架旧 Proxy"), required=False, default=True
        )

    infos = serializers.ListField(
        help_text=_("救援信息列表，每条对应一个集群"),
        child=RescueInfoSerializer(),
        min_length=1,
    )


class MySQLProxyRescueFlowParamBuilder(builders.FlowParamBuilder):
    """MySQL Proxy 救援流程参数构建器"""

    controller = MySQLController.mysql_proxy_rescue_scene


@builders.BuilderFactory.register(TicketType.MYSQL_PROXY_RESCUE, is_apply=True)
class MySQLProxyRescueFlowBuilder(BaseMySQLHATicketFlowBuilder):
    """
    MySQL Proxy 救援流程构建器（多集群模式）

    每个集群作为独立子流程并行执行：
    1. 上架新 Proxy 实例
    2. 配置 Proxy 后端
    3. 从 Master 恢复白名单
    4. 更新域名/CLB 解析
    5. 人工确认
    6. （可选）下架旧 Proxy
    """

    serializer = MySQLProxyRescueDetailSerializer
    inner_flow_builder = MySQLProxyRescueFlowParamBuilder
