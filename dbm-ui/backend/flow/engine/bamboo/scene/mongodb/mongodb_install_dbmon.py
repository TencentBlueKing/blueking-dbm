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
from collections import defaultdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _
from rest_framework import serializers

from backend import env
from backend.configuration.constants import DBType
from backend.db_package.models import Package
from backend.flow.consts import MediumEnum, MongoDBManagerUser
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.mongodb.base_flow import MongoBaseFlow
from backend.flow.engine.bamboo.scene.mongodb.sub_task.install_dbmon_sub import (
    InstallDBMonSubTask,
    PrepareInstanceInfo,
)
from backend.flow.engine.bamboo.scene.mongodb.sub_task.send_media import SendMedia
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs
from backend.flow.utils.mongodb.mongodb_repo import MongoNodeWithLabel, MongoRepository
from backend.flow.utils.mongodb.mongodb_util import MongoUtil

logger = logging.getLogger("flow")


def get_pkg_info():
    # repo_version 如果REPO_VERSION_FOR_DEV有值，则使用REPO_VERSION_FOR_DEV，否则使用最新版本
    # 正式环境中，REPO_VERSION_FOR_DEV为空
    # 个人测试环境中，REPO_VERSION_FOR_DEV 按需配置
    repo_version = env.REPO_VERSION_FOR_DEV if env.REPO_VERSION_FOR_DEV else MediumEnum.Latest

    actuator_pkg = Package.get_latest_package(
        version=repo_version, pkg_type=MediumEnum.DBActuator, db_type=DBType.MongoDB
    )

    dbtools_pkg = Package.get_latest_package(version=MediumEnum.Latest, pkg_type="dbtools", db_type=DBType.MongoDB)
    toolkit_pkg = Package.get_latest_package(
        version=MediumEnum.Latest, pkg_type="mongo-toolkit", db_type=DBType.MongoDB
    )
    dbmon_pkg = Package.get_latest_package(version=MediumEnum.Latest, pkg_type="dbmon", db_type=DBType.MongoDB)
    return {
        "actuator_pkg": actuator_pkg,
        "dbmon_pkg": dbmon_pkg,
        "dbtools_pkg": dbtools_pkg,
        "toolkit_pkg": toolkit_pkg,
    }


def add_install_dbmon(root_id, flow_data, pipeline, iplist, bk_cloud_id, allow_empty_instance=False):
    """
    allow_empty_instance 上架流程中，允许ip没有实例. allow_empty_instance = True
    """

    actuator_workdir = MongoUtil().get_mongodb_os_conf()["file_path"]
    pkg_info = get_pkg_info()
    file_list = [
        "{}/{}/{}".format(env.BKREPO_PROJECT, env.BKREPO_BUCKET, pkg_info.get("actuator_pkg").path),
        "{}/{}/{}".format(env.BKREPO_PROJECT, env.BKREPO_BUCKET, pkg_info.get("dbmon_pkg").path),
        "{}/{}/{}".format(env.BKREPO_PROJECT, env.BKREPO_BUCKET, pkg_info.get("dbtools_pkg").path),
        "{}/{}/{}".format(env.BKREPO_PROJECT, env.BKREPO_BUCKET, pkg_info.get("toolkit_pkg").path),
    ]

    sub_pipelines = []
    bk_host_list = []  # bk_host {ip:"
    logger.debug("add_install_dbmon iplist: {}".format(iplist))
    instances = MongoNodeWithLabel.from_hosts(iplist, bk_cloud_id=bk_cloud_id)
    if not allow_empty_instance and not instances:
        raise Exception("no instance found, ip_list:{}".format(iplist))

    result = MongoNodeWithLabel.append_password(instances, MongoDBManagerUser.MonitorUser.value)
    logger.debug("append_password result:{}".format(result))
    # group by ip
    instances_by_ip = defaultdict(list)
    for instance in instances:
        instances_by_ip[instance.ip].append(instance)

    for ip in iplist:
        nodes = instances_by_ip[ip]
        sub_pl, sub_bk_host_list = InstallDBMonSubTask.process_server(
            root_id=root_id,
            flow_data=flow_data,
            ip=ip,
            bk_cloud_id=bk_cloud_id,
            nodes=nodes,
            file_path=actuator_workdir,
            pkg_info=pkg_info,
            bk_monitor_beat_config=ActKwargs.get_mongodb_monitor_conf(),
        )
        if not sub_pl:
            raise Exception("sub_pl is None")
        if not sub_bk_host_list:
            raise Exception("sub_bk_host_list is None")
        bk_host_list.extend(sub_bk_host_list)
        sub_pipelines.append(sub_pl.build_sub_process(_("dbmon-{}").format(ip)))

    # 介质下发，包括actuator+dbmon+dbtools 如果文件没有变化，不会占用带宽
    pipeline.add_act(
        **SendMedia.act(
            act_name=_("CpFile: actuator+dbmon+dbtools+toolkit"),
            file_list=file_list,
            bk_host_list=bk_host_list,
            file_target_path=actuator_workdir,
        )
    )

    # 安装流程中，由prepare_instance_info来填充servers信息. 数据写在global_data -> 'ip' -> instances 中
    pipeline.add_act(
        **PrepareInstanceInfo.process_iplist(
            bk_cloud_id=bk_cloud_id,
            iplist=iplist,
            file_path=actuator_workdir,
            pkg_info=pkg_info,
            bk_monitor_beat_config=ActKwargs.get_mongodb_monitor_conf(),
        )
    )

    # 并行执行actuator
    pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)


class MongoInstallDBMonFlow(MongoBaseFlow):
    class Serializer(serializers.Serializer):
        uid = serializers.CharField()
        created_by = serializers.CharField()
        bk_biz_id = serializers.IntegerField()
        ticket_type = serializers.CharField()
        action = serializers.CharField()
        bk_cloud_id = serializers.IntegerField()
        infos = serializers.ListField(child=serializers.CharField())  # ip or cluster_id

    """MongoInstallDBMon flow
    分析 payload，检查输入，生成Flow """

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
        mongo_install_dbmon流程
        1. 解析输入 IP， 获得每个IP的实例列表，用户密码
        2. 得到介质列表
        """
        logger.debug("MongoInstallDBMon start, payload", self.payload)
        # 创建流程实例
        pipeline = Builder(root_id=self.root_id, data=self.payload)

        # parse iplist
        iplist = self.get_iplist(self.payload["infos"], bk_cloud_id=self.payload["bk_cloud_id"])

        add_install_dbmon(self, self.payload, pipeline, iplist, self.payload["bk_cloud_id"])
        # 运行流程
        pipeline.run_pipeline()

    @staticmethod
    def get_iplist(infos: list, bk_cloud_id: int) -> list[str]:
        iplist = []
        cluster_id_list = []
        cluster_domain_list = []
        for v in infos:
            if v.isdigit():
                cluster_id_list.append(int(v))
            elif v.endswith(".db"):
                cluster_domain_list.append(v)
            else:
                iplist.append(v)

        if cluster_domain_list:
            tmp_cluster_id_list = MongoRepository.get_cluster_id_by_domain(cluster_domain_list)
            cluster_id_list.extend(tmp_cluster_id_list)

        if cluster_id_list:
            cluster_id_list = list(set(cluster_id_list))  # unique
            clusters = MongoRepository.fetch_many_cluster(with_domain=False, id__in=cluster_id_list)
            for cluster in clusters:
                if cluster.bk_cloud_id == bk_cloud_id:
                    iplist.extend(cluster.get_iplist())
                else:
                    raise Exception("bk_cloud_id not match {} vs {}".format(bk_cloud_id, cluster.bk_cloud_id))

        return list(set(iplist))
