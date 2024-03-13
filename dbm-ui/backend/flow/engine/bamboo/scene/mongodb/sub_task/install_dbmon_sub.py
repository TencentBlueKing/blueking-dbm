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
from typing import Dict, List, Optional, Tuple

from django.utils.translation import ugettext as _

from backend.flow.consts import MongoDBActuatorActionEnum
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.mongodb.sub_task.base_subtask import BaseSubTask
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job2 import ExecJobComponent2
from backend.flow.plugins.components.collections.mongodb.prepare_instance_info import (
    ExecPrepareInstanceInfoOperationComponent,
)
from backend.flow.utils.mongodb.mongodb_dataclass import CommonContext
from backend.flow.utils.mongodb.mongodb_repo import MongoNodeWithLabel


# RestoreSubTask 处理某个Cluster的Restore
class InstallDBMonSubTask(BaseSubTask):
    """
    ip: 执行的ip
    nodes: instances in ip

    """

    @classmethod
    def make_kwargs(
        cls,
        ip: str,
        bk_cloud_id: int,
        nodes: List[MongoNodeWithLabel],
        file_path: str,
        pkg_info: Dict,
        bk_monitor_beat_config: Dict,
    ) -> dict:
        payload_func = {
            "module": "backend.flow.utils.mongodb.mongodb_dataclass",
            "function": "payload_func_install_dbmon",
        }
        v = {
            "set_trans_data_dataclass": CommonContext.__name__,
            "get_trans_data_ip_var": None,
            "bk_cloud_id": bk_cloud_id,
            "exec_ip": ip,
            "payload_func": payload_func,
            "db_act_template": {
                "exec_ip": ip,  # 用于 payload_func
                "action": MongoDBActuatorActionEnum.InstallDBMon,
                "file_path": file_path,
                "exec_account": "root",
                "sudo_account": "mysql",
                "payload": {
                    "bk_dbmon_pkg": {
                        "pkg": pkg_info["dbmon_pkg"].path,
                        "pkg_md5": pkg_info["dbmon_pkg"].md5,
                    },
                    "dbtools_pkg": {
                        "pkg": pkg_info["dbtools_pkg"].path,
                        "pkg_md5": pkg_info["dbtools_pkg"].md5,
                    },
                    "action": "install_or_update",
                    "report_save_dir": "/home/mysql/report",
                    "report_left_day": 60,
                    "http_address": "127.0.0.1:6677",
                    "bkmonitorbeat": bk_monitor_beat_config,
                    "servers": [],  #
                },
            },
        }
        return v

    @classmethod
    def process_server(
        cls,
        root_id: str,
        ip: str,
        bk_cloud_id: int,
        flow_data: dict,
        nodes: List[MongoNodeWithLabel],
        file_path: str,
        pkg_info: Dict,
        bk_monitor_beat_config: Optional[Dict],
    ) -> Tuple[SubBuilder, List]:
        """
        process_server
        """

        # 创建子流程
        sub_pipeline = SubBuilder(root_id=root_id, data=flow_data)
        kwargs = cls.make_kwargs(ip, bk_cloud_id, nodes, file_path, pkg_info, bk_monitor_beat_config)
        acts_list = [
            {
                "act_name": _("node-{}".format(kwargs["exec_ip"])),
                "act_component_code": ExecJobComponent2.code,
                "kwargs": kwargs,
            }
        ]
        sub_pipeline.add_parallel_acts(acts_list=acts_list)
        sub_bk_host_list = [{"ip": ip, "bk_cloud_id": bk_cloud_id}]
        return sub_pipeline, sub_bk_host_list

    @classmethod
    def make_kwargs_for_prepare_instance_info(
        cls, host_list: List, bk_cloud_id: int, file_path: str, pkg_info: Dict, bk_monitor_beat_config: Dict
    ) -> dict:
        return {
            "set_trans_data_dataclass": CommonContext.__name__,
            "get_trans_data_ip_var": None,
            "host_list": host_list,
            "bk_cloud_id": bk_cloud_id,
            "db_act_template": {
                "action": MongoDBActuatorActionEnum.InstallDBMon,
                "file_path": file_path,
                "exec_account": "root",
                "sudo_account": "mysql",
                "payload": {
                    "bk_dbmon_pkg": {
                        "pkg": pkg_info["dbmon_pkg"].path,
                        "pkg_md5": pkg_info["dbmon_pkg"].md5,
                    },
                    "dbtools_pkg": {
                        "pkg": pkg_info["dbtools_pkg"].path,
                        "pkg_md5": pkg_info["dbtools_pkg"].md5,
                    },
                    "action": "install_or_update",
                    "report_save_dir": "/home/mysql/report",
                    "report_left_day": 60,
                    "http_address": "127.0.0.1:6677",
                    "bkmonitorbeat": bk_monitor_beat_config,
                    "servers": [],
                },
            },
        }

    @classmethod
    def prepare_instance_info(
        cls,
        bk_cloud_id: int,
        host_list: List[Dict],
        file_path: str,
        pkg_info: Dict,
        bk_monitor_beat_config: Optional[Dict],
    ) -> dict:
        """
        prepare_instance_info for dbmon

        """
        kwargs = cls.make_kwargs_for_prepare_instance_info(
            host_list, bk_cloud_id, file_path, pkg_info, bk_monitor_beat_config
        )
        return {
            "act_name": _("prepare_instance_info:{} ip".format(len(host_list))),
            "act_component_code": ExecPrepareInstanceInfoOperationComponent.code,
            "kwargs": kwargs,
        }
