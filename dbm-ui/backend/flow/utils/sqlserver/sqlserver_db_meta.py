"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import logging

from backend.db_meta.api.cluster.sqlserverha.handler import SqlserverHAClusterHandler
from backend.db_meta.api.cluster.sqlserversingle.handler import SqlserverSingleClusterHandler

logger = logging.getLogger("flow")


class SqlserverDBMeta(object):
    """
    根据单据信息和集群信息，更新cmdb
    类的方法一定以单据类型的小写进行命名，否则不能根据单据类型匹配对应的方法
    """

    def __init__(self, global_data: dict, trans_data: dict):
        """
        @param global_data : 子流程单据信息,全局只读上下文
        @param trans_data: 子流程单据信息，可交互上下文
        """
        self.global_data = global_data
        self.trans_data = trans_data

    def sqlserver_single_apply(self):
        """
        单节点集群部署录入元数据
        """
        def_resource_spec = {"sqlserver_single": {"id": 0}}
        SqlserverSingleClusterHandler.create(
            bk_biz_id=self.global_data["bk_biz_id"],
            major_version=self.global_data["db_version"],
            ip=self.global_data["master_ip"],
            clusters=self.global_data["clusters"],
            db_module_id=self.global_data["db_module_id"],
            creator=self.global_data["created_by"],
            time_zone="+08:00",
            bk_cloud_id=int(self.global_data["bk_cloud_id"]),
            resource_spec=self.global_data.get("resource_spec", def_resource_spec),
            region=self.global_data["region"],
        )
        return True

    def sqlserver_ha_apply(self):
        """
        ha集群部署录入你元数据
        """
        def_resource_spec = {"sqlserver_ha": {"id": 0}}
        SqlserverHAClusterHandler.create(
            bk_biz_id=self.global_data["bk_biz_id"],
            db_module_id=self.global_data["db_module_id"],
            major_version=self.global_data["db_version"],
            master_ip=self.global_data["master_ip"],
            slave_ip=self.global_data["slave_ip"],
            clusters=self.global_data["clusters"],
            creator=self.global_data["created_by"],
            time_zone="+08:00",
            bk_cloud_id=int(self.global_data["bk_cloud_id"]),
            resource_spec=self.global_data.get("resource_spec", def_resource_spec),
            region=self.global_data["region"],
            sync_type=self.global_data["sync_type"],
        )
        return True
