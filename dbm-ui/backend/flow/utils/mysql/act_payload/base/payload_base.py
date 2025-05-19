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


class PayloadBase(object):
    def __init__(self, bk_cloud_id: int, ticket_data: dict, cluster: dict, cluster_type: str = None):
        """
        @param bk_cloud_id 操作的云区域
        @param ticket_data 单据信息
        @param cluster 需要操作的集群信息
        @param cluster_type 表示操作的集群类型，会决定到db_config获取配置的空间
        """
        self.bk_cloud_id = bk_cloud_id
        self.ticket_data = ticket_data
        self.cluster = cluster
        self.cluster_type = cluster_type

        # todo 后面可能优化这个问题
        if self.ticket_data.get("module"):
            self.db_module_id = self.ticket_data["module"]
        elif self.ticket_data.get("db_module_id"):
            self.db_module_id = self.ticket_data["db_module_id"]
        elif self.cluster and self.cluster.get("db_module_id"):
            self.db_module_id = self.cluster["db_module_id"]
        else:
            self.db_module_id = 0

    @classmethod
    def payload_class_path(cls) -> str:
        return "{}.{}".format(cls.__module__, cls.__name__)
