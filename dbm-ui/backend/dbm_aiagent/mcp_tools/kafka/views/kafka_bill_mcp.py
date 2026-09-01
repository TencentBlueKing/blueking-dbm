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

from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.kafka.impl.kafka_bill import (
    submit_kafka_apply_bill,
    submit_kafka_destroy_bill,
    submit_kafka_disable_bill,
    submit_kafka_enable_bill,
    submit_kafka_rebalance_bill,
    submit_kafka_reboot_bill,
    submit_kafka_replace_bill,
    submit_kafka_scale_up_bill,
    submit_kafka_shrink_bill,
)
from backend.dbm_aiagent.mcp_tools.kafka.serializers.kafka_bill import (
    KafkaSubmitBillOutputSerializer,
    SubmitBillKafkaApplyInputSerializer,
    SubmitBillKafkaDestroyInputSerializer,
    SubmitBillKafkaDisableInputSerializer,
    SubmitBillKafkaEnableInputSerializer,
    SubmitBillKafkaRebalanceInputSerializer,
    SubmitBillKafkaRebootInputSerializer,
    SubmitBillKafkaReplaceInputSerializer,
    SubmitBillKafkaScaleUpInputSerializer,
    SubmitBillKafkaShrinkInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import RejectPermission

logger = logging.getLogger("flow")

"""
Kafka 单据相关的 mcp
- broker扩容
- broker缩容
- broker替换
- topic均衡
"""


class KafkaBillMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(_("Kafka集群扩容单据(支持资源池和手工输入两种方式)")),
        request_slz=SubmitBillKafkaScaleUpInputSerializer,
        response_slz=KafkaSubmitBillOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.KAFKA_BILL],
        name_prefix="kafka_bill",
    )
    def submit_bill_scale_up(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        bk_biz_id = validated_params["bk_biz_id"]
        cluster_domain = validated_params["cluster_domain"]
        ip_source = validated_params["ip_source"]
        nodes = validated_params.get("nodes")
        resource_spec = validated_params.get("resource_spec")

        result = submit_kafka_scale_up_bill(
            bk_biz_id=bk_biz_id,
            cluster_domain=cluster_domain,
            ip_source=ip_source,
            nodes=nodes,
            resource_spec=resource_spec,
            creator=request.user.username,
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(
            _(
                "Kafka集群缩容单据。"
                "注意事项："
                "1. nodes参数需要包含待缩容节点的(ip, bk_host_id, bk_cloud_id)"
                "2. 当用户只提供IP地址时，必须先调用cluster_overview接口获取完整的节点信息(bk_host_id, bk_cloud_id)"
            )
        ),
        request_slz=SubmitBillKafkaShrinkInputSerializer,
        response_slz=KafkaSubmitBillOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.KAFKA_BILL],
        name_prefix="kafka_bill",
    )
    def submit_bill_shrink(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        bk_biz_id = validated_params["bk_biz_id"]
        cluster_domain = validated_params["cluster_domain"]
        nodes = validated_params["nodes"]

        result = submit_kafka_shrink_bill(
            bk_biz_id=bk_biz_id,
            cluster_domain=cluster_domain,
            nodes=nodes,
            creator=request.user.username,
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(
            _(
                "Kafka集群替换单据，支持资源池和手工输入。"
                "重要规则："
                "1.用户指定规格名称时，须先调用search_specs_by_name获取spec_id再传入resource_spec，不指定则使用原节点规格；"
                "2.ip_source=manual_input时必须提供new_nodes；"
                "3.old_nodes须含bk_host_id和bk_cloud_id，仅有IP时先调cluster_overview获取。"
            )
        ),
        request_slz=SubmitBillKafkaReplaceInputSerializer,
        response_slz=KafkaSubmitBillOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.KAFKA_BILL],
        name_prefix="kafka_bill",
    )
    def submit_bill_replace(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        bk_biz_id = validated_params["bk_biz_id"]
        cluster_domain = validated_params["cluster_domain"]
        old_nodes = validated_params["old_nodes"]
        ip_source = validated_params["ip_source"]
        new_nodes = validated_params.get("new_nodes")
        resource_spec = validated_params.get("resource_spec")

        result = submit_kafka_replace_bill(
            bk_biz_id=bk_biz_id,
            cluster_domain=cluster_domain,
            old_nodes=old_nodes,
            ip_source=ip_source,
            new_nodes=new_nodes,
            resource_spec=resource_spec,
            creator=request.user.username,
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(
            _(
                "Kafka集群Topic均衡单据，对指定topic进行分区重均衡以平衡broker负载。"
                "重要规则："
                "1.指定目标broker时，须先调cluster_overview获取IP，再传入target_ips；"
                "2.用户当前请求未提及速率时，必须省略throttle_rate，不要从历史对话获取速率值。"
            )
        ),
        request_slz=SubmitBillKafkaRebalanceInputSerializer,
        response_slz=KafkaSubmitBillOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.KAFKA_BILL],
        name_prefix="kafka_bill",
    )
    def submit_bill_rebalance(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        bk_biz_id = validated_params["bk_biz_id"]
        cluster_domain = validated_params["cluster_domain"]
        topics = validated_params["topics"]
        throttle_rate = validated_params["throttle_rate"]
        target_ips = validated_params.get("target_ips")

        result = submit_kafka_rebalance_bill(
            bk_biz_id=bk_biz_id,
            cluster_domain=cluster_domain,
            topics=topics,
            throttle_rate=throttle_rate,
            target_ips=target_ips,
            creator=request.user.username,
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(
            _(
                "Kafka实例重启单据。"
                "用途：重启指定的Kafka broker实例。"
                "参数说明："
                "1. bk_biz_id：必填，业务ID"
                "2. cluster_domain：必填，集群域名"
                "3. instance_list：必填，需要重启的实例列表。每个实例需要包含ip、port、bk_host_id、bk_cloud_id。"
                ""
                "注意事项："
                "当用户只提供IP地址时，必须先调用cluster_overview接口获取完整的实例信息(bk_host_id, bk_cloud_id, port)"
            )
        ),
        request_slz=SubmitBillKafkaRebootInputSerializer,
        response_slz=KafkaSubmitBillOutputSerializer,
        tags=[DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.KAFKA_BILL],
        name_prefix="kafka_bill",
    )
    def submit_bill_reboot(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        bk_biz_id = validated_params["bk_biz_id"]
        cluster_domain = validated_params["cluster_domain"]
        instance_list = validated_params["instance_list"]

        result = submit_kafka_reboot_bill(
            bk_biz_id=bk_biz_id,
            cluster_domain=cluster_domain,
            instance_list=instance_list,
            creator=request.user.username,
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(
            _(
                "Kafka集群启用单据。"
                "用途：将禁用的Kafka集群重新上线。"
                "参数说明："
                "1. bk_biz_id：必填，业务ID"
                "2. cluster_domain：必填，集群域名"
                ""
                "前置条件：集群必须处于禁用状态才能启用。如果集群是在线状态，无需操作。"
            )
        ),
        request_slz=SubmitBillKafkaEnableInputSerializer,
        response_slz=KafkaSubmitBillOutputSerializer,
        tags=[DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.KAFKA_BILL],
        name_prefix="kafka_bill",
    )
    def submit_bill_enable(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        bk_biz_id = validated_params["bk_biz_id"]
        cluster_domain = validated_params["cluster_domain"]

        result = submit_kafka_enable_bill(
            bk_biz_id=bk_biz_id,
            cluster_domain=cluster_domain,
            creator=request.user.username,
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(
            _("Kafka集群禁用单据。" "用途：将Kafka集群下线禁用，数据保留，可恢复。" "参数说明：" "1. bk_biz_id：必填，业务ID" "2. cluster_domain：必填，集群域名")
        ),
        request_slz=SubmitBillKafkaDisableInputSerializer,
        response_slz=KafkaSubmitBillOutputSerializer,
        tags=[DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.KAFKA_BILL],
        name_prefix="kafka_bill",
    )
    def submit_bill_disable(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        bk_biz_id = validated_params["bk_biz_id"]
        cluster_domain = validated_params["cluster_domain"]

        result = submit_kafka_disable_bill(
            bk_biz_id=bk_biz_id,
            cluster_domain=cluster_domain,
            creator=request.user.username,
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(
            _(
                "Kafka集群删除单据。"
                "用途：永久删除Kafka集群及其数据，不可恢复。"
                "参数说明："
                "1. bk_biz_id：必填，业务ID"
                "2. cluster_domain：必填，集群域名"
                ""
                "前置条件：集群必须处于禁用状态才能删除。如果集群是在线状态，请先调用禁用接口。"
                " important: 此操作将永久删除集群数据，不可恢复，请谨慎操作！"
            )
        ),
        request_slz=SubmitBillKafkaDestroyInputSerializer,
        response_slz=KafkaSubmitBillOutputSerializer,
        tags=[DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.KAFKA_BILL],
        name_prefix="kafka_bill",
    )
    def submit_bill_destroy(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        bk_biz_id = validated_params["bk_biz_id"]
        cluster_domain = validated_params["cluster_domain"]

        result = submit_kafka_destroy_bill(
            bk_biz_id=bk_biz_id,
            cluster_domain=cluster_domain,
            creator=request.user.username,
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(
            _(
                "Kafka集群部署单据，支持资源池和手工输入，部署包含zookeeper和broker的新集群。"
                "重要规则："
                "1.zookeeper固定3个节点，broker至少1个，副本数不能超过broker数量；"
                "2.city_code：用户说'随机'或不指定时用'default'，否则用实际城市名称；"
                "3.域名格式：kafka.{cluster_name}.{db_app_abbr}.db；"
                "4.仅有IP时须先调cluster_overview获取bk_host_id和bk_cloud_id。"
            )
        ),
        request_slz=SubmitBillKafkaApplyInputSerializer,
        response_slz=KafkaSubmitBillOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.KAFKA_BILL],
        name_prefix="kafka_bill",
    )
    def submit_bill_apply(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        bk_biz_id = validated_params["bk_biz_id"]
        cluster_name = validated_params["cluster_name"]
        ip_source = validated_params.get("ip_source", "resource_pool")
        nodes = validated_params.get("nodes")
        resource_spec = validated_params.get("resource_spec")
        db_app_abbr = validated_params["db_app_abbr"]
        timezone = validated_params.get("timezone", "Asia/Shanghai")
        city_code = validated_params["city_code"]
        region = validated_params.get("region", "default")
        disaster_tolerance_level = validated_params.get("disaster_tolerance_level", "MAX_EACH_ZONE_EQUAL")
        replication_num = validated_params.get("replication_num", 2)
        version = validated_params.get("version", "2.4.0")

        result = submit_kafka_apply_bill(
            bk_biz_id=bk_biz_id,
            cluster_name=cluster_name,
            ip_source=ip_source,
            nodes=nodes,
            resource_spec=resource_spec,
            db_app_abbr=db_app_abbr,
            timezone=timezone,
            city_code=city_code,
            region=region,
            disaster_tolerance_level=disaster_tolerance_level,
            replication_num=replication_num,
            version=version,
            creator=request.user.username,
        )
        return Response(result)
