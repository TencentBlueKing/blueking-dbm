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
    SubmitBillKafkaApplyInputSerializer,
    SubmitBillKafkaDestroyInputSerializer,
    SubmitBillKafkaDisableInputSerializer,
    SubmitBillKafkaEnableInputSerializer,
    SubmitBillKafkaRebalanceInputSerializer,
    SubmitBillKafkaRebootInputSerializer,
    SubmitBillKafkaReplaceInputSerializer,
    SubmitBillKafkaScaleUpInputSerializer,
    SubmitBillKafkaShrinkInputSerializer,
    SubmitBillOutputSerializer,
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
        response_slz=SubmitBillOutputSerializer,
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
        response_slz=SubmitBillOutputSerializer,
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
                "Kafka集群替换单据。支持资源池和手工输入两种方式。"
                "参数说明："
                "1. bk_biz_id：必填，业务ID"
                "2. cluster_domain：必填，集群域名"
                "3. old_nodes：必填，待替换节点信息 {'broker': [{'ip': 'xxx', 'bk_host_id': xxx, 'bk_cloud_id': xxx}]}"
                "4. ip_source：必填，主机来源(resource_pool资源池 或 manual_input手工_input)，默认resource_pool"
                "5. new_nodes：手工输入时必填，新节点信息"
                "6. resource_spec：资源池方式时可选，指定新节点规格 {'broker': {'spec_id': xxx}}"
                ""
                "重要规则："
                "- 当用户指定规格名称（如'IT5_16核_64G_3.5TB'）时："
                "  1. 必须先调用search_specs_by_name接口查询该规格名称对应的spec_id"
                "  2. 然后传入resource_spec={'broker': {'spec_id': 查询到的spec_id}}，否则系统将使用原节点规格"
                "- 当用户不指定规格时：使用原节点规格，无需提供resource_spec"
                "- 当用户指定手动输入(ip_source=manual_input)时：必须提供new_nodes"
                "- old_nodes必须包含bk_host_id和bk_cloud_id，仅IP不够时调用cluster_overview获取完整信息"
            )
        ),
        request_slz=SubmitBillKafkaReplaceInputSerializer,
        response_slz=SubmitBillOutputSerializer,
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
                "Kafka集群Topic均衡单据。"
                "用途：对指定topic进行数据分区重均衡，平衡各个broker之间的数据负载。"
                "参数说明："
                "1. bk_biz_id：必填，业务ID"
                "2. cluster_domain：必填，集群域名"
                "3. topics：可选，需要均衡的topic列表，不传则均衡所有topic"
                "4. throttle_rate：可选，均衡速率(字节/秒)。系统默认为80MB/s。"
                "5. target_ips：可选，目标broker IP列表。指定将数据均衡到这些IP所在的broker节点，不传则均衡到所有broker。"
                ""
                "重要规则："
                "- 当用户需要将数据均衡到指定的broker时（如'均衡到IP为x.x.x.x的broker'），"
                "  1. 必须先调用cluster_overview接口获取集群中所有broker节点的IP信息"
                "  2. 然后传入target_ips=['x.x.x.x', ...]，只对指定IP的broker进行均衡"
                "- 当用户没有指定目标broker时，省略target_ips参数，系统会均衡到所有broker"
                ""
                "重要：当用户当前请求中没有提及速率相关词汇（如'速率xx MB/s'、'每秒xx字节'、'throttle_rate'等）时，"
                "必须省略throttle_rate参数，不要从历史对话或上下文中获取任何速率值。"
                "只有用户在当前请求中明确指定了速率时，才需要传递此参数"
            )
        ),
        request_slz=SubmitBillKafkaRebalanceInputSerializer,
        response_slz=SubmitBillOutputSerializer,
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
        response_slz=SubmitBillOutputSerializer,
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
        response_slz=SubmitBillOutputSerializer,
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
        response_slz=SubmitBillOutputSerializer,
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
        response_slz=SubmitBillOutputSerializer,
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
                "Kafka集群部署单据。支持资源池和手工输入两种方式。"
                "用途：部署一个新的Kafka集群，包含zookeeper和broker组件。"
                "参数说明："
                "1. bk_biz_id：必填，业务ID"
                "2. cluster_name：必填，集群名称"
                "3. ip_source：主机来源(资源池resource_pool或手工输入manual_input)，默认资源池"
                "4. nodes：手工输入时必填，格式{'zookeeper': [...], 'broker': [...]}。zookeeper必须正好3个节点"
                "5. resource_spec：资源池时必填，格式{'zookeeper': {'count': 3, 'spec_id': xxx}, 'broker': {...}}"
                "6. db_app_abbr：必填，业务缩写，用于生成域名(kafka.{cluster_name}.{db_app_abbr}.db)"
                "7. city_code：必填，城市名称。用户说'随机'或不指定城市时，使用'default'；其他情况使用实际城市名称"
                "8. timezone：可选，时区，默认Asia/Shanghai"
                "9. region：可选，区域，默认default"
                "10. disaster_tolerance_level：可选，容灾级别，默认MAX_EACH_ZONE_EQUAL(各机房均衡)"
                "11. replication_num：可选，副本数，默认2，必须小于等于broker节点数量"
                "12. version：可选，Kafka版本，默认2.4.0"
                ""
                "注意事项："
                "1. zookeeper节点固定为3个，不可更改"
                "2. broker节点至少需要1个"
                "3. 副本数不能超过broker节点数量"
                "4. 系统自动生成用户名和密码，返回在结果中"
                "5. 当用户只提供IP地址时，必须先调用cluster_overview接口获取完整的节点信息(bk_host_id, bk_cloud_id)"
            )
        ),
        request_slz=SubmitBillKafkaApplyInputSerializer,
        response_slz=SubmitBillOutputSerializer,
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
