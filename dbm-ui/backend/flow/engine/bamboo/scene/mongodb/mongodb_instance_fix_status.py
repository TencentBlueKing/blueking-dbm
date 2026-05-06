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
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from django.utils.translation import gettext as _
from rest_framework import serializers

from backend.configuration.constants import DBType
from backend.flow.consts import MongoDBActuatorActionEnum, MongoDBManagerUser
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mongodb.base_flow import MongoBaseFlow
from backend.flow.engine.bamboo.scene.mongodb.sub_task.instance_op import InstanceOpSubTask
from backend.flow.engine.bamboo.scene.mongodb.sub_task.send_media import SendMedia
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job2 import ExecJobComponent2
from backend.flow.plugins.components.collections.mongodb.fix_instance_status import (
    ExecFixInstanceStatusOperationComponent,
)
from backend.flow.utils.mongodb.mongodb_dataclass import CommonContext
from backend.flow.utils.mongodb.mongodb_repo import MongoNodeWithLabel
from backend.flow.utils.mongodb.mongodb_util import MongoUtil

logger = logging.getLogger("flow")


@dataclass
class MetaStatusInfo:
    require: bool = False  # 是否需要修复
    current: str = None  # 当前值
    required: str = None  # 修复值

    def __json__(self):
        return {
            "require": self.require,
            "current": self.current,
            "required": self.required,
        }


@dataclass
class BindEntryInfo:
    entry_type: str = ""  # 绑定类型: DNS, CLB
    entry_id: int = -1  # 绑定ID
    entry_info: str = None  # 绑定信息

    def __json__(self):
        return {
            "entry_type": self.entry_type,
            "entry_id": self.entry_id,
            "entry_info": self.entry_info,
        }


@dataclass
class InstanceInfo:
    ip: str = ""
    port: int = 0
    bk_cloud_id: int = -1
    cluster_id: int = -1
    cluster_type: str = ""
    role: str = ""
    status: str = ""
    bind_entry_info_list: List[BindEntryInfo] = field(default_factory=list)
    meta_status_info: MetaStatusInfo = field(default_factory=MetaStatusInfo)

    def __init__(self, ip: str, port: int, bk_cloud_id: int, cluster_id: int, cluster_type: str, role: str):
        self.ip = ip
        self.port = port
        self.bk_cloud_id = bk_cloud_id
        self.cluster_id = cluster_id
        self.cluster_type = cluster_type
        self.role = role
        self.bind_entry_info_list = []
        self.meta_status_info = MetaStatusInfo()

    def __json__(self):
        return {
            "ip": self.ip,
            "port": self.port,
            "bk_cloud_id": self.bk_cloud_id,
            "cluster_id": self.cluster_id,
            "cluster_type": self.cluster_type,
            "role": self.role,
            "status": self.status,
        }


class MongoDBInstanceFixStatusFlow(MongoBaseFlow):
    class Serializer(serializers.Serializer):
        class DataRow(serializers.Serializer):
            bk_cloud_id = serializers.IntegerField()
            ip = serializers.CharField()
            port = serializers.IntegerField()
            dry_run = serializers.BooleanField()

        uid = serializers.CharField()
        created_by = serializers.CharField()
        bk_biz_id = serializers.IntegerField()
        ticket_type = serializers.CharField()
        infos = DataRow(many=True)

    """MongoDB Mongos/instance 状态修复flow"""

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        传入参数
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """

        super().__init__(root_id, data)
        self.check_payload()

    def check_payload(self):
        s = self.Serializer(data=self.payload)
        if not s.is_valid():
            raise Exception("payload is invalid {}".format(s.errors))

    def start(self):
        """
        Mongos/instance 状态修复流程
        1. 确认mongod/mongos的服务正常
        2. 修复DnsEntry 和 ClbEntry
        """
        logger.debug("MongoDBInstanceFixStatusFlow start, payload", self.payload)
        # actuator_workdir 在部署的时候就创建好的
        actuator_workdir = MongoUtil().get_mongodb_os_conf()["file_path"]
        # 创建流程实例
        pipeline = Builder(root_id=self.root_id, data=self.payload)
        bk_host_list = []
        instance_list = []
        instance_pipes = []
        for row in self.payload["infos"]:
            ip = row.get("ip")
            port = row.get("port")
            bk_cloud_id = row.get("bk_cloud_id")
            nodes = MongoNodeWithLabel.from_hosts([ip], bk_cloud_id)
            if not nodes:
                raise Exception("instance not found ip:{} port:{} bk_cloud_id:{}".format(ip, port, bk_cloud_id))
            instance = None
            for node in nodes:
                if node.ip == ip and node.port == port:
                    instance = InstanceInfo(
                        ip=ip,
                        port=port,
                        bk_cloud_id=bk_cloud_id,
                        cluster_id=node.cluster_id,
                        cluster_type=node.cluster_type,
                        role=node.role_type,
                    )
                    break
            if not instance:
                raise Exception("instance not found ip:{} port:{} bk_cloud_id:{}".format(ip, port, bk_cloud_id))
            instance_list.append(instance)
            bk_host_list.append({"ip": instance.ip, "bk_cloud_id": instance.bk_cloud_id})
            instance_sb = self.process_instance(actuator_workdir, instance)
            instance_pipes.append(
                instance_sb.build_sub_process(f"instance_fix_status ({instance.ip}:{instance.port})")
            )

        # 介质下发 bk_host_list 在SendMedia.act会去重.
        self.push_media(
            bk_host_list=bk_host_list,
            file_list=GetFileList(db_type=DBType.MongoDB).mongodb_actuator_pkg(),
            file_target_path=actuator_workdir,
            parent_sb=pipeline,
        )
        sb = SubBuilder(root_id=self.root_id, data=self.payload)
        sb.add_parallel_sub_pipeline(sub_flow_list=instance_pipes)
        pipeline.add_sub_pipeline(sb.build_sub_process("[job]instance_fix_status"))
        pipeline.run_pipeline()

    def push_media(self, bk_host_list: list, file_list: list, file_target_path: str, parent_sb: Builder):
        """push_media"""
        sb = SubBuilder(root_id=self.root_id, data=self.payload)
        sb.add_act(
            **SendMedia.act(
                act_name=_("MongoDB-介质下发({})".format(len(set[Any]([host["ip"] for host in bk_host_list])))),
                file_list=file_list,
                bk_host_list=bk_host_list,
                file_target_path=file_target_path,
            )
        )
        parent_sb.add_sub_pipeline(sub_flow=sb.build_sub_process("[file]push_media"))

    def process_instance(self, actuator_workdir: str, instance: InstanceInfo):
        """process_instance
        已获得instance的信息，在instance_list中.
        # 1. 获得instance的status
        # 2. 获得dns绑定情况
        # 3. 获得clb的绑定情况"""
        instance_sb = SubBuilder(root_id=self.root_id, data=self.payload)
        self.service_status_check(actuator_workdir, instance, instance_sb)
        self.fix_service_status(instance, instance_sb)
        return instance_sb

    def service_status_check(self, actuator_workdir: str, instance: InstanceInfo, parent_sb: SubBuilder):
        """
        service_status_check.
        1. mongod: 检查rs的status，必须为PRIMARY或者SECONDARY.
        2. mongos: 检查mongos的status，show dbs 必须有admin, config, local三个库. config.shards的内容输出正常.

        """
        sb = SubBuilder(root_id=self.root_id, data=self.payload)
        act = {
            "act_name": f"service_status_check {instance.ip}:{instance.port}:{instance.bk_cloud_id}",
            "act_component_code": ExecJobComponent2.code,
            "kwargs": InstanceOpSubTask.make_kwargs(
                file_path=actuator_workdir,
                exec_node=instance,
                op="service_status_check",
                username=MongoDBManagerUser.MonitorUser.value,
            ),
        }
        sb.add_act(**act)
        parent_sb.add_sub_pipeline(sub_flow=sb.build_sub_process("[job]service_status_check"))

    def fix_service_status(self, instance: InstanceInfo, parent_sb: SubBuilder):
        """
        # update dbmeta instance status.
        """
        # saas fix service status.
        sb = SubBuilder(root_id=self.root_id, data=self.payload)
        kwargs = {
            "set_trans_data_dataclass": CommonContext.__name__,
            "get_trans_data_ip_var": None,
            "trans_data_var": {
                "instance": {
                    "ip": instance.ip,
                    "port": instance.port,
                    "bk_cloud_id": instance.bk_cloud_id,
                    "cluster_id": instance.cluster_id,
                    "cluster_type": instance.cluster_type,
                    "role": instance.role,
                    "status": instance.status,
                }
            },
            "db_act_template": {
                "action": MongoDBActuatorActionEnum.FixServiceStatus.value,
                "payload": {
                    "ip": instance.ip,
                    "port": instance.port,
                    "op": "fix_service_status",
                },
            },
        }
        act = {
            "act_name": f"fix_service_status {instance.ip}:{instance.port}",
            "act_component_code": ExecFixInstanceStatusOperationComponent.code,
            "kwargs": kwargs,
        }
        sb.add_act(**act)
        parent_sb.add_sub_pipeline(sub_flow=sb.build_sub_process("[saas]fix_service_status"))
