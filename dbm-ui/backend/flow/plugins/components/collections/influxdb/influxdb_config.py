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
import base64
import logging
from typing import List

from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend.components.mysql_priv_manager.client import DBPrivManagerApi
from backend.db_meta.api import common
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import StorageInstance
from backend.flow.consts import MySQLPrivComponent, NameSpaceEnum
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


class InfluxdbConfigService(BaseService):
    """
    更新config
    """

    def _execute(self, data, parent_data) -> bool:
        global_data = data.get_one_of_inputs("global_data")

        storage_instances = []
        for influxdb in global_data["nodes"]["influxdb"]:
            storage_instances.append(
                {
                    "ip": influxdb["ip"],
                    "port": global_data["port"],
                    "instance_role": InstanceRole.INFLUXDB.value,
                }
            )

        storage_objs = common.filter_out_instance_obj(storage_instances, StorageInstance.objects.all())
        for storage_obj in storage_objs:
            # Writing to password service, using instance_id as ip
            self.log_info("Writing password to service...")
            # 把用户名当密码存
            query_params = {
                "instances": [{"ip": str(storage_obj.id), "port": 0, "bk_cloud_id": global_data["bk_cloud_id"]}],
                "password": base64.b64encode(str(global_data["username"]).encode("utf-8")).decode("utf-8"),
                "username": MySQLPrivComponent.INFLUXDB_FAKE_USER.value,
                "component": NameSpaceEnum.Influxdb,
                "operator": "admin",
            }
            DBPrivManagerApi.modify_password(params=query_params)
            # 存真实的用户名密码
            query_params = {
                "instances": [{"ip": str(storage_obj.id), "port": 0, "bk_cloud_id": global_data["bk_cloud_id"]}],
                "password": base64.b64encode(str(global_data["password"]).encode("utf-8")).decode("utf-8"),
                "username": global_data["username"],
                "component": NameSpaceEnum.Influxdb,
                "operator": "admin",
            }
            DBPrivManagerApi.modify_password(params=query_params)

        self.log_info("InfluxDB config rewrite successfully")
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]

    def outputs_format(self) -> List:
        return [Service.OutputItem(name="command result", key="result", type="str")]


class InfluxdbConfigComponent(Component):
    name = __name__
    code = "influxdb_config"
    bound_service = InfluxdbConfigService
