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
import re

from django.utils.translation import gettext as _

from backend.db_meta.models import Cluster
from backend.flow.consts import MySQLBackupTypeEnum, RollbackType
from backend.flow.engine.validate.mysql_base_validate import MysqlBaseValidator
from backend.flow.utils.mysql.db_table_filter.tools import replace_glob

logger = logging.getLogger("root")


# class TenDbClusterRollbackFlowValidator(MysqlBaseValidator):
#     def __call__(self):
#         return None


# class TenDbHaRollbackFlowValidator(MysqlBaseValidator):
#     def __call__(self):
#         return None


class TenDbHaRollbackFlowValidator(MysqlBaseValidator):
    def __call__(self):
        error_msgs = []
        for index, info in enumerate(self.data["infos"]):
            # source_cluster_id = info["cluster_id"]
            # target_cluster_id = info["target_cluster_id"]
            # rollback_time = info["rollback_time"]
            rollback_type = info["rollback_type"]
            rollback_databases = info["databases"]
            affect_database_list = info.get("affect_database_list", [])

            backup_info = info["backupinfo"]
            backup_database_list = backup_info["database_list"]
            backup_type = backup_info["backup_type"]
            # backup_method = backup_info.get("backup_method", "")
            # backup_source = "remote"
            # consistent_backup_time = backup_info.get("consistent_backup_time", "")
            # backup_charset = backup_info.get("backup_charset", "")

            # 验证回档的DB
            if len(rollback_databases) == 0:
                error_msgs.append(msg_format(index, _("回档的DB不能为空")))
                return error_msgs
            if len(backup_database_list) == 0:
                error_msgs.append(msg_format(index, _("备份文件中不存在DB")))
            all_db_rollback = False
            if "*" in rollback_databases:
                all_db_rollback = True
            else:
                # 1. 匹对指定的回档DB在备份中是否存在
                backup_pattern_dbs = []
                # 替换数据库的模糊匹配为正则匹配.
                rollback_databases_parts = ["{}$".format(replace_glob(db)) for db in rollback_databases]
                for db_pattern in rollback_databases_parts:
                    db_patterns = [db for db in backup_database_list if re.match(db_pattern, db)]
                    backup_pattern_dbs.extend(db_patterns)
                if len(backup_pattern_dbs) == 0:
                    error_msgs.append(msg_format(index, _("备份文件中不存在回档的DB: {}").format(rollback_databases)))

            # 2. 指定DB回档不能是物理别分或者指定时间的回档
            if not all_db_rollback:
                if backup_type == MySQLBackupTypeEnum.PHYSICAL.value:
                    error_msgs.append(msg_format(index, _("指定DB回档不能使用物理备份")))
                if rollback_type in [RollbackType.REMOTE_AND_TIME, RollbackType.LOCAL_AND_TIME]:
                    error_msgs.append(msg_format(index, _("指定时间回档只能是全服回档，不能指定DB")))

            # 3. 如果是指定备份记录的回档，不能有影响的DB
            if (
                rollback_type in [RollbackType.REMOTE_AND_BACKUPID, RollbackType.LOCAL_AND_BACKUPID]
                and backup_type != MySQLBackupTypeEnum.PHYSICAL.value
            ):
                if len(affect_database_list) > 0:
                    error_msgs.append(msg_format(index, _("指定备份记录的回档不能有 受影响的DB,请先清理或者提单rename目标集群的影响DB")))
            if (
                rollback_type in [RollbackType.REMOTE_AND_TIME, RollbackType.LOCAL_AND_TIME]
                and backup_type == MySQLBackupTypeEnum.LOGICAL.value
            ):
                if len(affect_database_list) > 0:
                    error_msgs.append(msg_format(index, _("指定时间时间且使用逻辑备份的回档不能有 受影响的DB,请先清理或者提单rename目标集群的影响DB")))
        if len(error_msgs) > 0:
            return error_msgs
        return None


class TenDbClusterRollbackFlowValidator(MysqlBaseValidator):
    """
    tendbHa 回档单据校验
    """

    def __call__(self):
        error_msgs = []
        for index, info in enumerate(self.data["infos"]):
            if self.data["rollback_cluster_type"] != "BUILD_INTO_NEW_CLUSTER":
                source_cluster_id = info["cluster_id"]
                target_cluster_id = info["target_cluster_id"]
                source_obj = Cluster.objects.get(id=source_cluster_id)
                target_obj = Cluster.objects.get(id=target_cluster_id)
                shards = source_obj.tendbclusterstorageset_set.filter()
                new_shards = target_obj.tendbclusterstorageset_set.filter()
                if len(shards) != len(new_shards):
                    error_msgs.append(msg_format(index, _("源集群和目标集群的分片数不一致")))

            # rollback_time = info["rollback_time"]
            rollback_type = info["rollback_type"]
            rollback_databases = info["databases"]
            affect_database_list = info.get("affect_database_list", [])

            backup_info = info["backupinfo"]
            backup_database_list = backup_info["database_list"]
            backup_type_list = backup_info["backup_type_list"]
            # backup_method = backup_info.get("backup_method", "")
            # backup_source = "remote"
            # consistent_backup_time = backup_info.get("consistent_backup_time", "")
            # backup_charset = backup_info.get("backup_charset", "")

            # 验证回档的DB
            if len(rollback_databases) == 0:
                error_msgs.append(msg_format(index, _("回档的DB不能为空")))
                return error_msgs
            if len(backup_database_list) == 0:
                error_msgs.append(msg_format(index, _("备份文件中不存在DB")))
            all_db_rollback = False
            if "*" in rollback_databases:
                all_db_rollback = True
            else:
                # 1. 匹对指定的回档DB在备份中是否存在
                backup_pattern_dbs = []
                rollback_databases_parts = ["{}$".format(replace_glob(db)) for db in rollback_databases]
                for db_pattern in rollback_databases_parts:
                    db_patterns = [db for db in backup_database_list if re.match(db_pattern, db)]
                    backup_pattern_dbs.extend(db_patterns)
                if len(backup_pattern_dbs) == 0:
                    error_msgs.append(msg_format(index, _("备份文件中不存在回档的DB: {}").format(rollback_databases)))
            # 2. 指定DB回档不能是物理别分或者指定时间的回档
            if not all_db_rollback:
                if MySQLBackupTypeEnum.PHYSICAL.value in backup_type_list:
                    error_msgs.append(msg_format(index, _("指定DB回档不能使用物理备份")))
                if rollback_type in [RollbackType.REMOTE_AND_TIME, RollbackType.LOCAL_AND_TIME]:
                    error_msgs.append(msg_format(index, _("指定时间回档只能是全服回档，不能指定DB")))

            # 3. 如果是指定备份记录的回档，不能有影响的DB
            if (
                rollback_type in [RollbackType.REMOTE_AND_BACKUPID, RollbackType.LOCAL_AND_BACKUPID]
                and MySQLBackupTypeEnum.PHYSICAL.value not in backup_type_list
            ):
                if len(affect_database_list) > 0:
                    error_msgs.append(msg_format(index, _("指定备份记录的回档不能有 受影响的DB,请先清理或者提单rename目标集群的影响DB")))
            if (
                rollback_type in [RollbackType.REMOTE_AND_TIME, RollbackType.LOCAL_AND_TIME]
                and MySQLBackupTypeEnum.PHYSICAL.value not in backup_type_list
            ):
                if len(affect_database_list) > 0:
                    error_msgs.append(msg_format(index, _("指定时间时间且使用逻辑备份的回档不能有 受影响的DB,请先清理或者提单rename目标集群的影响DB")))
        if len(error_msgs) > 0:
            return error_msgs
        return None


def msg_format(index: int = 0, msg="") -> str:
    index = index + 1
    return _("第{}行:{}").format(index, msg)
