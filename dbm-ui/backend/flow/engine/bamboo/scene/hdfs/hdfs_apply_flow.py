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

from backend.flow.engine.bamboo.scene.hdfs.hdfs_apply_flow_v1 import HdfsApplyFlowV1
from backend.flow.engine.bamboo.scene.hdfs.hdfs_apply_flow_v2 import HdfsApplyFlowV2
from backend.flow.utils.hdfs.consts import V2_FLOW_VERSION_KEY

logger = logging.getLogger("flow")


class HdfsApplyFlow(object):
    """
    构建hdfs集群申请流程的抽象类
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data    : 单据传递参数
        """
        self.root_id = root_id
        self.data = data

    def _should_use_v2_flow(self) -> bool:
        """
        判断是否使用V2版本的流程
        当版本号包含 BK_BASE_KEYWORD 时使用V2流程，否则使用V1流程
        """
        if not self.data or "db_version" not in self.data:
            logger.warning("db_version field not found, using V1 flow by default")
            return False

        db_version = str(self.data["db_version"])

        # 判断逻辑：版本号中包含BK_BASE_KEYWORD时使用V2流程
        if V2_FLOW_VERSION_KEY in db_version.lower():
            logger.info(f"Version {db_version} contains {V2_FLOW_VERSION_KEY}, using V2 deployment flow")
            return True
        else:
            logger.info(f"Version {db_version} does not contain {V2_FLOW_VERSION_KEY}, using V1 deployment flow")
            return False

    def deploy_hdfs_flow(self):
        """
        定义部署hdfs集群的流程
        """
        if self._should_use_v2_flow():
            # 使用V2版本的流程
            v2_flow = HdfsApplyFlowV2(root_id=self.root_id, data=self.data)
            return v2_flow.deploy_hdfs_flow()
        else:
            # 使用V1版本的流程
            v1_flow = HdfsApplyFlowV1(root_id=self.root_id, data=self.data)
            return v1_flow.deploy_hdfs_flow()
