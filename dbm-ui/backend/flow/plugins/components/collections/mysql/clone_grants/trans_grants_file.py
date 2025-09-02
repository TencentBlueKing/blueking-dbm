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

from pipeline.component_framework.component import Component

from backend.flow.consts import MediumFileTypeEnum
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileService


class TransGrantsFileService(TransFileService):
    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")

        if not trans_data.report_result:
            return False

        if "report_result" not in trans_data.report_result:
            return False

        report_result = trans_data.report_result["report_result"]

        if "file_list" not in report_result:
            return False

        file_list = report_result["file_list"]

        priv_filename = ""
        for ele in file_list:
            if ele["file_name"].endswith(".priv"):
                priv_filename = ele["file_name"]
                break

        if not priv_filename:
            return False

        data.get_one_of_inputs("kwargs")["file_list"] = [f"/data/dbbak/{priv_filename}"]
        data.get_one_of_inputs("kwargs")["file_type"] = MediumFileTypeEnum.Server.value
        data.get_one_of_inputs("kwargs")["account"] = {"alias": "mysql"}
        data.get_one_of_inputs("kwargs")["file_target_path"] = f"/data/install/dbactuator-{kwargs['bill_id']}"

        trans_data.priv_filename = priv_filename
        data.outputs["trans_data"] = trans_data

        return super()._execute(data=data, parent_data=parent_data)


class TransGrantsFileComponent(Component):
    name = __name__
    code = "mysql_trans_grants_file"
    bound_service = TransGrantsFileService
