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
import os
import tempfile

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.core.storages.storage import get_storage
from backend.flow.plugins.components.collections.common.base_service import BaseService


class UploadFileService(BaseService):
    """
    上传文件到制品库
    """

    def _execute(self, data, parent_data) -> bool:
        global_data = data.get_one_of_inputs("global_data") or {}
        kwargs = data.get_one_of_inputs("kwargs") or {}
        content = kwargs["content"]
        path = kwargs["path"]
        storage = get_storage(file_overwrite=False)

        # 如果上传的是sql内容, 则创建一个sql文件
        if content:
            sql_file = tempfile.NamedTemporaryFile(suffix=".sql")
            sql_file.write(str.encode(content, encoding="utf-8"))
        else:
            self.log_error(_("分区sql为空无需上传"))
            return False

        sql_path = storage.save(name=path, content=sql_file)
        self.log_info(sql_path)
        self.log_info(_("单据id{}".format(global_data["uid"])))
        self.log_info(_("分区sql文件上传成功"))
        return True


class UploadFileServiceComponent(Component):
    name = __name__
    code = "upload_file"
    bound_service = UploadFileService
