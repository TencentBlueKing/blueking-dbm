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
from django.http import StreamingHttpResponse
from rest_framework.status import HTTP_200_OK

from backend import env
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
            # encoding = chardet.detect(zip_content[:100])["encoding"]
            zip_content = zip_content.decode("utf-8", errors="replace")
            return [{"path": file_path, "content": zip_content, "url": self.storage.url(file_path)}]

        # 如果是有多个文件，则制品库会打包文件，返回一个zip流
        file_stream = io.BytesIO(zip_content)
        unzip_files = zipfile.ZipFile(file=file_stream)
        for index, unzip_file_name in enumerate(unzip_files.namelist()):
            # 注意，这里解压缩的文件名和原路径会有差异(好像少一个层级)
            file_content_list.append(
                {
                    "path": unzip_file_name,
                    "content": unzip_files.read(unzip_file_name).decode("utf-8", errors="replace"),
                    "url": self.storage.url(unzip_file_name),
                }
            )

        return file_content_list

    def batch_download(self, file_path_list: List[str]) -> StreamingHttpResponse:
        """
        批量下载文件
        :param file_path_list: 文件列表
        """
        resp = self.storage.batch_download(file_path_list)
        resp = StreamingHttpResponse(
            resp.iter_content(),
            content_type="application/octet‑stream",
        )
        resp["Content-Disposition"] = 'attachment; filename="download.tar.gz"'
        return resp

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

    def create_bkrepo_access_token(self, path: str):
        """
        获取制品库临时凭证，并返回制品库相关信息
        :param path: 授权路径
        """
        # 过期时间默认一天，且限制访问1次
        expire_time = 3600 * 24
        permits = 1
        data = self.storage.client.create_bkrepo_access_token(paths=[path], expire_time=expire_time, permits=permits)
        return {
            "token": data[0]["token"],
            "url": env.BKREPO_FRONTEND_URL,
            "project": env.BKREPO_PROJECT,
            "repo": env.BKREPO_BUCKET,
            "path": path,
        }

    def download_dirs(self, file_path_list: list, force_download: bool):
        """
        指定目录下载，返回下载链接
        :param file_path_list: 下载目录列表
        :param force_download: 是否强制下载
        """
        return {path: self.storage.download_url(path, force_download) for path in file_path_list}
