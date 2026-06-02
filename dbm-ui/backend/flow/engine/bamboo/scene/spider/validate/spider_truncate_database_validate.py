"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from backend.flow.engine.validate.exceptions import DuplicateClusterIDException
from backend.flow.engine.validate.mysql_base_validate import MysqlBaseValidator


class SpiderTruncateDatabaseFlowValidator(MysqlBaseValidator):
    """
    SpiderTruncateDatabaseFlow类对应的validate类
    判断传入flow的data参数合法性
    校验内容：
    聚合校验：
        检验1：同一个flow，不能出现重复的cluster_id
    """

    def __call__(self):
        """
        发起校验, 实例函数化
        """

        # 检测同一个flow中，不能出现重复的cluster_id
        err = self.pre_check_duplicate_cluster_ids("cluster_id")
        if err:
            raise DuplicateClusterIDException(err)

        return None
