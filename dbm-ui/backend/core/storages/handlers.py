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

import io
import zipfile
from typing import Any, Dict, List

from bkstorages.exceptions import RequestError as BKStorageError
from rest_framework.status import HTTP_200_OK

from backend.core.storages.storage import CustomBKRepoStorage, get_storage
from backend.exceptions import ApiRequestError, ApiResultError


class StorageHandler(object):
    """处理storage视图函数的相关操作"""

    # 默认储存类型是制品库类型
    storage: CustomBKRepoStorage = None

    def __init__(self, storage=None):
        self.storage = storage or get_storage()

    @staticmethod
    def validate_response(response):
        if response.status_code != HTTP_200_OK:
            raise ApiResultError(response.content)

        return response

    def batch_fetch_file_content(self, file_path_list: List[str]) -> List[Dict[str, Any]]:
        """
        批量获取文件内容
        TODO: 是否需要限制文件大小，比如文件太大就不支持提供文件内容，只提供url下载链接
        :param file_path_list: 文件列表
        """

        file_content_list: List[Dict[str, Any]] = []
        resp = self.validate_response(self.storage.client.batch_download(file_path_list))
        zip_content = resp.content

        # 如果文件只有一个，则返回的是文件本身
        if len(file_path_list) == 1:
            file_path = file_path_list[0]
            return [{"path": file_path, "content": zip_content.decode("utf-8"), "url": self.storage.url(file_path)}]

        # 如果是有多个文件，则制品库会打包文件，返回一个zip流
        file_stream = io.BytesIO(zip_content)
        unzip_files = zipfile.ZipFile(file=file_stream)
        for index, unzip_file_name in enumerate(unzip_files.namelist()):
            # 注意，这里解压缩的文件名和原路径会有差异(好像会少一个层级)
            file_path = file_path_list[index]
            file_content_list.append(
                {
                    "path": file_path,
                    "content": unzip_files.read(unzip_file_name).decode("utf-8"),
                    "url": self.storage.url(file_path),
                }
            )

        return file_content_list

    def delete_file(self, file_path) -> bool:
        """
        从制品库删除文件
        :param file_path: 带删除文件路径
        """

        try:
            self.storage.client.delete_file(file_path)
        except BKStorageError as e:
            raise ApiRequestError(e)

        return True
