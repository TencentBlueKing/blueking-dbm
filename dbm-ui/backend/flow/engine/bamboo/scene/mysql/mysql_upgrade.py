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
import copy
import logging.config
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import MYSQL8_VER_PARSE_NUM, DBType
from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import StorageInstance
from backend.db_package.models import Package
from backend.flow.consts import MediumEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DBMetaOPKwargs, DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta
from backend.flow.utils.mysql.mysql_version_parse import mysql_version_parse

logger = logging.getLogger("flow")


class MySQLLocalUpgradeFlow(object):
    """
    mysql 本地升级场景,只允许升级slave实例
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data
        self.uid = data["uid"]
        self.new_mysql_version = data["new_mysql_version"]
        self.new_version_num = mysql_version_parse(self.__get_pkg_name_by_version(self.new_mysql_version))
        if self.new_version_num > MYSQL8_VER_PARSE_NUM:
            self.new_version_num = self.__convert_mysql8_version_num(self.new_version_num)

    def __get_mysql_instance_by_host(self, ip: str) -> list:
        return StorageInstance.objects.filter(machine__ip=ip)

    def __get_pkg_name_by_version(self, version: str) -> str:
        # 获取大版本的最新的包名
        mysql_pkg = Package.get_latest_package(version=version, pkg_type=MediumEnum.MySQL, db_type=DBType.MySQL)
        return mysql_pkg.name

    def __convert_mysql8_version_num(self, verno: int) -> int:
        # MySQL的发行版本号并不连续 MySQL 5.5 5.6 5.7 8.0
        # 为了方便比较将8.0 装换成 parse 之后的5.8的版本号来做比较
        return 5008 * 1000 + verno % 1000

    def upgrade_mysql_flow(self):
        proxy_upgrade_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []
        cluster_ids = []
        # 声明子流程
        for mysql in self.data["mysql_ip_list"]:
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("mysql_ip_list")
            ports = []
            mysql_instances = self.__get_mysql_instance_by_host(mysql["ip"])
            if len(mysql_instances) <= 0:
                raise DBMetaException(message=_("根据mysql 机器ip {} 无法找到对应的实例记录").format(mysql["ip"]))
            for mysql_instance in mysql_instances:
                cluster_ids.append(mysql_instance.cluster.get().id)
                ports.append(mysql_instance.port)
                current_version = mysql_version_parse(mysql_instance.version)
                if current_version >= self.new_version_num:
                    logger.error(
                        "the upgrade version {} needs to be larger than the current verion {}".format(
                            self.new_version_num, current_version
                        )
                    )
                    raise DBMetaException(message=_("待升级版本大于等于新版本，请确认升级的版本"))
                if self.new_version_num // 1000 - current_version // 1000 > 1:
                    logger.error("upgrades across multiple major versions are not allowed")
                    raise DBMetaException(message=_("不允许跨多个大版本升级"))

            sub_pipeline = SubBuilder(
                root_id=self.root_id, data=copy.deepcopy(sub_flow_context), need_random_pass_cluster_ids=cluster_ids
            )
            sub_pipeline.add_sub_pipeline(
                sub_flow=self.upgrade_mysql_subflow(
                    bk_cloud_id=mysql["bk_cloud_id"],
                    ip=mysql["ip"],
                    proxy_ports=ports,
                )
            )
            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("本地升级MySQL版本")))
        proxy_upgrade_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        proxy_upgrade_pipeline.run_pipeline(is_drop_random_user=True)
        return

    def upgrade_mysql_subflow(
        self,
        ip: str,
        bk_cloud_id: int,
        proxy_ports: list = None,
    ):
        """
        定义upgrade mysql 的flow
        """
        sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)

        sub_pipeline.add_act(
            act_name=_("下发升级的安装包"),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(
                DownloadMediaKwargs(
                    bk_cloud_id=bk_cloud_id,
                    exec_ip=ip,
                    file_list=GetFileList(
                        db_type=DBType.MySQL,
                    ).mysql_upgrade_package(db_version=self.new_mysql_version),
                )
            ),
        )

        cluster = {"run": False, "ports": proxy_ports, "version": self.new_mysql_version}
        exec_act_kwargs = ExecActuatorKwargs(cluster=cluster, bk_cloud_id=bk_cloud_id)
        exec_act_kwargs.exec_ip = ip
        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_mysql_upgrade_payload.__name__
        # 执行本地升级
        sub_pipeline.add_act(
            act_name=_("执行本地升级前置检查"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(exec_act_kwargs),
        )

        cluster = {"run": True, "ports": proxy_ports, "version": self.new_mysql_version}
        exec_act_kwargs = ExecActuatorKwargs(cluster=cluster, bk_cloud_id=bk_cloud_id)
        exec_act_kwargs.exec_ip = ip
        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_mysql_upgrade_payload.__name__
        # 执行本地升级
        sub_pipeline.add_act(
            act_name=_("执行本地升级"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(exec_act_kwargs),
        )
        # 更新proxy instance version 信息
        sub_pipeline.add_act(
            act_name=_("更新proxy version meta信息"),
            act_component_code=MySQLDBMetaComponent.code,
            kwargs=asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=MySQLDBMeta.update_proxy_instance_version.__name__,
                    cluster={"proxy_ip": ip, "version": self.new_version_num},
                )
            ),
        )
        return sub_pipeline.build_sub_process(sub_name=_("proxy实例升级"))
