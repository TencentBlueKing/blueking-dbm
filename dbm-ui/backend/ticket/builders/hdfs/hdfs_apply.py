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
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext as _
from rest_framework import serializers

from backend.db_services.dbbase.constants import HDFS_DEFAULT_HTTP_PORT, HDFS_DEFAULT_RPC_PORT, IpSource
from backend.flow.engine.controller.hdfs import HdfsController
from backend.ticket import builders
from backend.ticket.builders.common import constants
from backend.ticket.builders.common.bigdata import BaseHdfsTicketFlowBuilder, BigDataApplyDetailsSerializer
from backend.ticket.builders.common.constants import BigDataRole
from backend.ticket.constants import TicketType


class HdfsApplyDetailSerializer(BigDataApplyDetailsSerializer):
    def validate(self, attrs):
        """
        hdfs上架限制：
        1. Datanode机器 至少需要2台，与前面角色（Namenode/ZooKeeper/JournalNode）的机器互斥
        2. Namenode机器有且必须是2台
        3. ZooKeeper/JournalNode 的机器有且必须是3台，（这三台可以与前面的Namenode重复，即不互斥）
        目前来说ZooKeeper/JournalNode的单据参数角色是zookeeper
        """

        # 判断Datanode是否与Namenode/ZooKeeper/JournalNode互斥
        super().validate(attrs=attrs)

        # 判断datanode是不是>=2台
        datanode_count = self.get_node_count(attrs, BigDataRole.Hdfs.DATANODE.value)
        if datanode_count < constants.HDFS_DATANODE_MIN:
            raise serializers.ValidationError(_("Datanode节点数量<2台，请增加Datanode节点数量"))

        # 判断namenode数量是否为2
        namenode_count = self.get_node_count(attrs, BigDataRole.Hdfs.NAMENODE.value)
        if namenode_count != constants.HDFS_NAMENODE_NEED:
            raise serializers.ValidationError(_("Namenode节点数量不等于2台，请确保Namenode数量为2台"))

        # 判断zk/jn数量是否为3
        zk_jn_node_count = self.get_node_count(attrs, BigDataRole.Hdfs.ZK_JN.value)
        if attrs["ip_source"] == IpSource.RESOURCE_POOL:
            if zk_jn_node_count < 1 or zk_jn_node_count > 3:
                raise serializers.ValidationError(_("资源池部署ZooKeeper/JournalNode的角色数量为1-3台"))
        else:
            if zk_jn_node_count != constants.HDFS_ZK_JN_NEED:
                raise serializers.ValidationError(_("ZooKeeper/JournalNode节点数量不等于3台，请确保ZooKeeper/JournalNode数量为3台"))

        return attrs


class HdfsApplyFlowParamBuilder(builders.FlowParamBuilder):
    controller = HdfsController.hdfs_apply_scene

    def format_ticket_data(self):
        """
        {
            "uid": 354,
            "ticket_type": "HDFS_APPLY",
            "rpc_port": 9000,
            "nodes": {
                "zookeeper": [
                    {
                        "ip": "127.0.0.1",
                        "bk_cloud_id": 0
                    },
                    {
                        "ip": "127.0.0.2",
                        "bk_cloud_id": 0
                    },
                    {
                        "ip": "127.0.0.3",
                        "bk_cloud_id": 0
                    }
                ],
                "namenode": [
                    {
                        "ip": "127.0.0.4",
                        "bk_cloud_id": 0
                    },
                    {
                        "ip": "127.0.0.5",
                        "bk_cloud_id": 0
                    }
                ],
                "datanode": [
                    {
                        "ip": "127.0.0.6",
                        "bk_cloud_id": 0
                    },
                    {
                        "ip": "127.0.0.7",
                        "bk_cloud_id": 0
                    }
                ]
            },
            "ip_source": "manual_input",
            "http_port": 50070,
            "haproxy_passwd": "UJF2847Q",
            "db_version": "2.7.1",
            "created_by": "admin",
            "cluster_name": "hdfs-cluster",
            "city_code": "深圳",
            "bk_biz_id": 2005000002,
            "db_app_abbr": "blueking"
        }
        """
        haproxy_passwd = get_random_string(8)
        self.ticket_data.update(
            {
                "http_port": HDFS_DEFAULT_HTTP_PORT,
                "rpc_port": HDFS_DEFAULT_RPC_PORT,
                "haproxy_passwd": haproxy_passwd,
                "domain": f"hdfs.{self.ticket_data['cluster_name']}.{self.ticket_data['db_app_abbr']}.db",
            }
        )


class HdfsApplyResourceParamBuilder(builders.ResourceApplyParamBuilder):
    def post_callback(self):
        """如果ZK_JN申请机器不够3台，则与NAMENODE共用机器"""
        next_flow = self.ticket.next_flow()
        node_infos = next_flow.details["ticket_data"]["nodes"]

        diff = 3 - len(node_infos[BigDataRole.Hdfs.ZK_JN])
        node_infos[BigDataRole.Hdfs.ZK_JN].extend(node_infos[BigDataRole.Hdfs.NAMENODE][:diff])

        next_flow.details["ticket_data"].update(nodes=node_infos)
        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.HDFS_APPLY)
class HdfsApplyFlowBuilder(BaseHdfsTicketFlowBuilder):
    serializer = HdfsApplyDetailSerializer
    inner_flow_builder = HdfsApplyFlowParamBuilder
    inner_flow_name = _("HDFS 集群部署")
    resource_apply_builder = HdfsApplyResourceParamBuilder
