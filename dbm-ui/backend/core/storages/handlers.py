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
import logging
import posixpath
import zipfile
from typing import Any, Dict, List

from bkstorages.exceptions import RequestError as BKStorageError
from django.http import StreamingHttpResponse
from django.utils.translation import gettext as _
from rest_framework.status import HTTP_200_OK

from backend import env
from backend.core.storages.constants import STAGING_PREFIX
from backend.core.storages.exceptions import StagingFileError
from backend.core.storages.storage import CustomBKRepoStorage, get_storage
from backend.exceptions import ApiRequestError, ApiResultError

logger = logging.getLogger("root")


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
        file_path_list = list(set(file_path_list))

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
        # 分块下载默认1M
        chunk_size = 1024 * 1024
        content_disposition = resp.headers.get("Content-Disposition", 'attachment; filename="download.tar.gz"')
        resp = StreamingHttpResponse(
            resp.iter_content(chunk_size=chunk_size),
            content_type="application/octet‑stream",
            headers={"Content-Disposition": content_disposition},
        )
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

    def move_file(self, source_path: str, target_dir: str, overwrite: bool = False) -> str:
        """
        将文件从一个目录挪到另一个目录（同一制品库仓库内，文件名保持不变）
        :param source_path: 源文件完整路径
        :param target_dir: 目标目录
        :param overwrite: 目标已存在同名文件时是否覆盖
        :return: 移动后的文件完整路径
        """
        # 目标路径 = 目标目录 + 源文件名（制品库路径恒为 POSIX 风格）
        file_name = posixpath.basename(source_path.rstrip("/"))
        target_path = posixpath.join(target_dir, file_name)

        try:
            self.storage.client.move_file(source_path, target_path, overwrite=overwrite)
        except BKStorageError as e:
            raise ApiRequestError(e)

        return target_path

    def move_staging_file_to_formal(self, staging_path: str, overwrite: bool = True) -> str:
        """
        将暂存区文件移动到正式目录（去除 /staging 前缀）

        例如: /staging/mysql/mysql-dumper/latest/xxxx.py -> /mysql/mysql-dumper/latest/xxxx.py

        非暂存区路径（如 CI 同步直接给出的正式路径）不做处理，原样返回；
        暂存区文件已不存在但正式目录已有该文件时，视为此前已转正，幂等返回正式路径；
        暂存区路径不合法、或暂存与正式目录均无该文件时抛出异常，避免把失效路径写入 DB。

        :param staging_path: 暂存区文件完整路径
        :param overwrite: 正式目录已存在同名文件时是否覆盖
        :return: 移动后的正式目录文件路径；非暂存区路径原样返回
        :raises StagingFileError: 暂存区路径非法，或文件在暂存与正式目录中均不存在
        """
        # 1. 非暂存区路径无需转正，原样返回
        prefix = STAGING_PREFIX.rstrip("/") + "/"
        if not staging_path or not staging_path.startswith(prefix) or staging_path == prefix:
            return staging_path

        # 2. 不允许包含 . / .. 等路径段（防止路径穿越）
        segments = [seg for seg in staging_path.split("/") if seg != ""]
        if any(seg in (".", "..") for seg in segments):
            raise StagingFileError(_("非法的暂存区路径: {}").format(staging_path))

        # 去除 /staging 前缀得到正式路径
        formal_path = staging_path[len(STAGING_PREFIX.rstrip("/")) :]

        # 3. 暂存区文件不存在时，若正式目录已有该文件，说明此前已转正（如批量提交部分成功后重试），
        if not self.storage.exists(staging_path):
            if self.storage.exists(formal_path):
                logger.info(_("[move_staging_file_to_formal] 文件已转正，跳过移动: %s"), formal_path)
                return formal_path
            raise StagingFileError(_("暂存区文件不存在，可能已被清理: {}").format(staging_path))

        # 4. 按正式目录移动
        target_dir = posixpath.dirname(formal_path)
        moved_path = self.move_file(staging_path, target_dir, overwrite=overwrite)
        logger.info(_("[move_staging_file_to_formal] 移动成功: %s -> %s"), staging_path, moved_path)
        return moved_path

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

    def batch_create_bkrepo_access_token(self, file_path_list: List[str]) -> List[Dict[str, Any]]:
        """
        批量获取制品库临时凭证，为多个文件路径创建临时访问凭证
        :param file_path_list: 文件路径列表
        :return: 包含每个文件路径凭证信息的列表
        """
        # 去重处理
        file_path_list = list(set(file_path_list))

        # 过期时间默认一天，且限制访问1次
        expire_time = 3600 * 24
        permits = 1

        # 批量创建临时凭证
        tokens_data = self.storage.client.create_bkrepo_access_token(
            paths=file_path_list, expire_time=expire_time, permits=permits
        )

        # 保证文件路径和凭证信息一一对应
        result = []
        for token_data in tokens_data:
            # TODO: 取消校验文件路径，因为制品库会自动添加前缀‘/’
            # if token_data["fullPath"] in file_path_list:
            result.append(
                {
                    "token": token_data["token"],
                    "url": env.BKREPO_FRONTEND_URL,
                    "project": env.BKREPO_PROJECT,
                    "repo": env.BKREPO_BUCKET,
                    "path": token_data["fullPath"],
                }
            )

        return result

    def download_dirs(self, file_path_list: list, force_download: bool):
        """
        指定目录下载，返回下载链接
        :param file_path_list: 下载目录列表
        :param force_download: 是否强制下载
        """
        return {path: self.storage.download_url(path, force_download) for path in file_path_list}
