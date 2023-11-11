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

from pipeline.component_framework.component import Component

from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileService

logger = logging.getLogger("flow")


class TBinlogDumperTransFileService(TransFileService):
    def _execute(self, data, parent_data) -> bool:
        """
        执行传输文件的原子任务, 针对tbinlogdumper的全量同步
        """
        trans_data = data.get_one_of_inputs("trans_data")
        data.get_one_of_inputs("kwargs")["file_list"] = [f"{trans_data.backup_info['backup_dir']}/*"]
        data.get_one_of_inputs("kwargs")["file_target_path"] = trans_data.backup_info["backup_dir"]

        return super()._execute(data, parent_data)


class TBinlogDumperTransFileComponent(Component):
    name = __name__
    code = "tbinlogdumper_trans_file"
    bound_service = TBinlogDumperTransFileService
