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
import base64
import json
import tempfile

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.core.storages.storage import get_storage
from backend.flow.plugins.components.collections.common.base_service import BaseService


class UploadFileService(BaseService):
    """
    上传文件到制品库

    支持通过 kwargs["encoding"] 指定内容编码方式:
      - "text"   : content 视为文本，按 utf-8 编码写入(默认)
      - "base64" : content 视为 base64 编码后的二进制内容，先 b64decode 再按字节写入
                   适用于 Oracle 密码文件等二进制文件，避免走 JSON/UTF-8 通道时被替换成 U+FFFD
    """

    def _execute(self, data, parent_data) -> bool:
        global_data = data.get_one_of_inputs("global_data") or {}
        kwargs = data.get_one_of_inputs("kwargs") or {}
        trans_data = data.get_one_of_inputs("trans_data")

        content = kwargs.get("content")
        content_var = kwargs.get("content_var")
        encoding = (kwargs.get("encoding") or "text").lower()

        # 如果指定了content_var，从上下文trans_data中获取content
        if content_var and trans_data:
            trans_content = getattr(trans_data, content_var, None)
            if trans_content is not None:
                if isinstance(trans_content, dict) and "content" in trans_content:
                    content = trans_content["content"]
                elif isinstance(trans_content, str):
                    content = trans_content
                else:
                    content = json.dumps(trans_content)

        path = kwargs["path"]
        storage = get_storage(file_overwrite=True)

        if not content:
            self.log_error(_("文件为空无需上传"))
            return False

        file = tempfile.NamedTemporaryFile(suffix=".tmp")
        if encoding == "base64":
            # 二进制文件场景：content 是 base64 字符串，解码后按字节写入
            try:
                raw_bytes = base64.b64decode(content, validate=False)
            except Exception as e:
                self.log_error(_("base64 解码失败: {}").format(e))
                return False
            file.write(raw_bytes)
            self.log_info(_("以 base64 方式写入二进制文件，字节数={}").format(len(raw_bytes)))
        else:
            # 文本文件场景：按 utf-8 编码写入
            file.write(str.encode(content, encoding="utf-8"))
        file.seek(0)

        sql_path = storage.save(name=path, content=file)
        self.log_info(sql_path)
        self.log_info(_("单据id{}".format(global_data["uid"])))
        self.log_info(_("文件上传成功"))
        return True


class UploadFileServiceComponent(Component):
    name = __name__
    code = "upload_file"
    bound_service = UploadFileService
