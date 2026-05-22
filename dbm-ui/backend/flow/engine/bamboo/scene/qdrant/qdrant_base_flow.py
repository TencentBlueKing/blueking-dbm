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
from typing import Dict, Optional

logger = logging.getLogger("flow")


class K8sQdrantBaseFlow(object):
    """
    Qdrant Flow基类
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        :param root_id: flow的root_id
        :param data: flow的data
        """
        self.root_id = root_id
        self.data = data
        self.bk_cloud_id = data.get("bk_cloud_id")
        self.cluster = data.get("cluster")
        self.remark = data.get("remark")
        self.bk_biz_id = data.get("bk_biz_id")
        self.ticket_type = data.get("ticket_type")
        self.db_app_abbr = data.get("db_app_abbr")
        self.bk_biz_name = data.get("bk_biz_name")
        self.bk_cloud_region = data.get("bk_cloud_region")
        self.city_code = data.get("city_code")
        self.k8s_cluster_name = data.get("k8s_cluster_name")
        self.major_version = data.get("major_version")
        self.db_version = data.get("db_version")
        self.cluster_type = data.get("cluster_type")
        self.cluster_name = data.get("cluster_name")
        self.cluster_alias = data.get("cluster_alias")
        self.component_list = data.get("component_list")
