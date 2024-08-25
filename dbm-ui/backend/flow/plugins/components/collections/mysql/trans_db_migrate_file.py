"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import os

from pipeline.component_framework.component import Component

from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileService


class DbMigrateTransFileService(TransFileService):
    def __get_file_list(self, fileInfo: dict) -> list:
        file_name_list = fileInfo["file_name_list"]
        file_dir_path = fileInfo["file_dir_path"]
        file_list = []
        for file_name in file_name_list:
            file_path = os.path.join(file_dir_path, file_name)
            file_list.append(file_path)

        return file_list

    def _execute(self, data, parent_data) -> bool:
        trans_data = data.get_one_of_inputs("trans_data")
        # 用于数据迁移
        data.get_one_of_inputs("kwargs")["file_list"] += self.__get_file_list(trans_data.file_list_info)
        return super()._execute(data, parent_data)


class DbMigrateTransFileComponent(Component):
    name = __name__
    code = "db_migrate_trans_file"
    bound_service = DbMigrateTransFileService
