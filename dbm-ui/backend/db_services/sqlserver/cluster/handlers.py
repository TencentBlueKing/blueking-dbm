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
from datetime import datetime
from typing import Dict, List

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils.translation import ugettext as _

from backend.db_services.dbbase.cluster.handlers import ClusterServiceHandler as BaseClusterServiceHandler
from backend.db_services.sqlserver.rollback.handlers import SQLServerRollbackHandler
from backend.exceptions import ValidationError
from backend.flow.utils.sqlserver import sqlserver_db_function
from backend.utils.excel import ExcelHandler


class ClusterServiceHandler(BaseClusterServiceHandler):
    def __init__(self, bk_biz_id: int):
        self.bk_biz_id = bk_biz_id

    @classmethod
    def get_dbs_for_drs(cls, cluster_id: int, db_list: list, ignore_db_list: list) -> list:
        """根据传入的db列表正则匹配和忽略db列表的正则匹配，获取真实的db名称"""
        return sqlserver_db_function.get_dbs_for_drs(cluster_id, db_list, ignore_db_list)

    @classmethod
    def multi_get_dbs_for_drs(cls, cluster_ids: list, db_list: list, ignore_db_list: list) -> dict:
        """根据库正则批量查询集群的正式DB列表"""
        return sqlserver_db_function.multi_get_dbs_for_drs(cluster_ids, db_list, ignore_db_list)

    @classmethod
    def check_cluster_database(cls, cluster_id: int, db_list: list):
        """根据存入的db名称，判断库名是否在集群存在"""
        check_dbs_infos = sqlserver_db_function.check_sqlserver_db_exist(cluster_id, db_list)
        check_dbs_map = {info["name"]: info["is_exists"] for info in check_dbs_infos}
        return check_dbs_map

    @classmethod
    def import_db_struct(
        cls,
        cluster_id: int,
        db_list: list,
        ignore_db_list: list,
        db_excel: InMemoryUploadedFile,
        backup_logs: list = None,
        restore_time: datetime = None,
    ) -> List[Dict]:
        """
        根据集群ID(或者备份记录)和库表正则和导入的excel解析数据
        """
        # 解析excel的构造DB数据
        db_data_list = ExcelHandler.paser(db_excel.file)
        header_map = {_("构造 DB 名称"): "db_name", _("构造后 DB 名称"): "target_db_name", _("已存在的 DB"): "rename_db_name"}
        for data in db_data_list:
            for header in header_map:
                data[header_map[header]] = data.pop(header)
        source_data_dbs = [data["db_name"] for data in db_data_list]

        # 根据库正则查询匹配的库表
        if backup_logs:
            source_cluster_dbs = [data["db_name"] for data in backup_logs]
        elif restore_time:
            restore_backup_file = SQLServerRollbackHandler(cluster_id).query_latest_backup_log(restore_time)
            source_cluster_dbs = [data["db_name"] for data in restore_backup_file["logs"]]
        else:
            source_cluster_dbs = cls.get_dbs_for_drs(cluster_id, db_list, ignore_db_list)

        # 校验excel的源DB是否和集群的DB匹配
        if set(source_data_dbs) != set(source_cluster_dbs):
            raise ValidationError(_("导入的源DB不与集群DB匹配，请检查excel数据"))

        return db_data_list
