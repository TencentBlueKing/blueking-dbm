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

from typing import Dict, Optional

from backend.flow.utils.mongodb.mongodb_dataclass import MongoDBCluster


def start():
    pass
    """
    fix me
    """


class MongoBaseFlow(object):
    """MongoRemoveNsFlowflow
    分析 payload，检查输入，生成Flow"""

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        传入参数
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """

        self.root_id = root_id
        self.payload = data

    # 检查 cluster 和 输入中的bk_biz_id字段是否相同.
    @classmethod
    def check_cluster(cls, cluster: MongoDBCluster, payload):
        if cluster is None:
            raise Exception("row.cluster_domain is not exists.")
        if str(cluster.bk_biz_id) != payload["bk_biz_id"]:
            raise Exception(
                "bad bk_biz_id {} vs {} {} {}".format(
                    cluster.bk_biz_id, payload["bk_biz_id"], type(cluster.bk_biz_id), type(payload["bk_biz_id"])
                )
            )
