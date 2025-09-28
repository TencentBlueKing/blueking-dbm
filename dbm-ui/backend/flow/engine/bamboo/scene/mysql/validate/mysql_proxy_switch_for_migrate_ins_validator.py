"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from backend.flow.engine.bamboo.scene.mysql.validate.mysql_proxy_switch_validator import MySQLProxySwitchValidator
from backend.flow.engine.validate.exceptions import DuplicateIPException


class MySQLProxySwitchForMigrateInsValidator(MySQLProxySwitchValidator):
    """
    迁移proxy流程的validator方法(实例维度)
    """

    def __call__(self):
        # 阶段1 检测每个行的数据合法性
        error_msgs = []
        for index, info in enumerate(self.data["infos"]):
            error_msgs += self.run_check_for_info(info=info, index=index, is_migrate_ins_task=True)
        if error_msgs:
            return error_msgs

        # 阶段2 做聚合校验
        # 同一个flow，不能出现同一个集群
        err = self.pre_check_duplicate_cluster_ids("cluster_ids")
        if err:
            raise DuplicateIPException(err)

        return None
