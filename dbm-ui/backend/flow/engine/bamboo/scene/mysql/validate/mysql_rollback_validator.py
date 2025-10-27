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

from backend.flow.engine.validate.mysql_base_validate import MysqlBaseValidator

logger = logging.getLogger("root")


class TenDbHaRollbackFlowValidator(MysqlBaseValidator):
    """
    tendbHa 回档单据校验
    """

    def __call__(self):
        # logging.info(self.data)
        # print(self.data)
        # error_msgs = []
        # for data in self.data["infos"]:
        #     #  jia["infos"][0]["backupinfo"]["database_list"]
        #     msg, ok = check_rollback_databases(data["target_cluster_id"], data["backupinfo"]["database_list"])
        #     if not ok:
        #         error_msgs.append(msg)
        # if error_msgs:
        #     return error_msgs
        return None


class TenDbClusterRollbackFlowValidator(MysqlBaseValidator):
    """
    tendbHa 回档单据校验
    """

    def __call__(self):
        # logging.info(self.data)
        # print(self.data)
        # error_msgs = []
        # for index, info in enumerate(self.data["details"]["infos"]):
        #
        #     backup_handler = MySQLBackupHandler(
        #         cluster_id=info["source_cluster_id"],
        #         backup_id=info["backup_id"],
        #         backup_source=info["backup_source"],
        #     )
        #     backup_info = backup_handler.get_spider_rollback_backup_info()
        #     database_list = backup_info.get("database_list", [])
        #     msg, ok = check_rollback_databases(info["target_cluster_id"], database_list)
        #     if not ok:
        #         error_msgs.append(msg)
        # if error_msgs:
        #     return error_msgs
        return None
