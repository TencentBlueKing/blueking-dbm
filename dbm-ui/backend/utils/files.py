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


import hashlib
import os
from typing import IO, Any, List, Optional

import requests


class FileOpen:

    """
    文件上下文管理器
    与open对比，提供 file_obj - IO 作为文件输入的方式
    读取结束时，指针默认复位，避免影响 file_obj 复用，减少 open 次数
    """

    closed: bool
    # 标记是否通过路径打开
    is_name: bool
    file_obj: Optional[IO[Any]]

    def __init__(self, name: str = None, file_obj: Optional[IO[Any]] = None, mode: str = "rb", closed: bool = True):
        """
        :param name: 文件路径
        :param file_obj: 已 open 的文件，优先级：file_obj > name
        :param mode: 文件访问模式，同 open mode
        :param closed: 上下文结束时是否关闭
        """
        if not (file_obj or name):
            raise ValueError("nothing to open")

        self.closed = closed
        # 标记是否通过路径打开
        self.is_name = not file_obj

        if self.is_name:
            self.file_obj = open(name, mode=mode)
        else:
            self.file_obj = file_obj

    def __enter__(self) -> IO[Any]:
        return self.file_obj

    def __exit__(self, exc_type, exc_val, exc_tb):

        # 指针复位，避免 closed=False 场景下，影响上层逻辑对该文件对象的复用
        # 参考：https://stackoverflow.com/questions/3906137/why-cant-i-call-read-twice-on-an-open-file
        self.file_obj.seek(0)

        # 通过路径open的文件对象必须关闭
        # 传入的文件对象由上层逻辑决定是否显式传入不关闭
        if self.is_name or (not self.is_name and self.closed):
            self.file_obj.close()


def md5sum(name: str = None, file_obj: Optional[IO[Any]] = None, mode: str = "rb", closed: bool = True) -> str:
    """
    计算文件md5
    :param name: 文件路径
    :param file_obj: 已打开的文件文件对象，同时传 name 和 file_obj 后者优先使用
    :param mode: 文件打开模式，具体参考 open docstring，默认 rb
    :param closed: 是否返回时关闭文件对象，安全起见默认关闭
    :return: md5 str or "-1"
    """

    hash_md5 = hashlib.md5()

    with FileOpen(name=name, file_obj=file_obj, mode=mode, closed=closed) as fs:
        for chunk in iter(lambda: fs.read(4096), b""):
            if not chunk:
                continue
            hash_md5.update(chunk)

    return hash_md5.hexdigest()


def download_file(
    url: str,
    name: str = None,
    file_obj: Optional[IO[Any]] = None,
    mode: str = "wb",
    closed: bool = True,
) -> None:

    """
    下载文件
    :param url: 下载url
    :param name: 写入目标路径
    :param file_obj: 已打开的写入目标文件对象
    :param mode: 文件打开模式，具体参考 open docstring，默认 rb
    :param closed: 是否返回时关闭文件对象，安全起见默认关闭
    :return: None
    """

    with requests.get(url=url, stream=True) as rfs:

        rfs.raise_for_status()

        with FileOpen(name=name, file_obj=file_obj, mode=mode, closed=closed) as local_fs:
            for chunk in rfs.iter_content(chunk_size=4096):
                if not chunk:
                    continue
                local_fs.write(chunk)


def fetch_file_paths_from_dir(
    dir_path: str, ignored_dir_names: Optional[List[str]] = None, ignored_file_names: Optional[List[str]] = None
) -> List[str]:
    """
    获取目录下全部文件
    :param dir_path: 目录路径
    :param ignored_dir_names: 忽略的目录名称
    :param ignored_file_names: 忽略的文件名称
    :return: 文件路径列表
    """
    if not os.path.isdir(dir_path):
        raise NotADirectoryError(f"{dir_path} is not a directory or doesn't exist.")

    file_paths = []
    ignored_dir_paths = set()
    ignored_dir_names = set(ignored_dir_names or {})
    ignored_file_names = set(ignored_file_names or {})

    for child_dir_path, dir_names, file_names in os.walk(dir_path):

        # 记录忽略的目录路径
        for dir_name in dir_names:
            if dir_name in ignored_dir_names:
                ignored_dir_paths.add(os.path.join(child_dir_path, dir_name))

        if child_dir_path in ignored_dir_paths:
            continue

        # 将未忽略的文件路径加入到返回列表
        for file_name in file_names:
            if file_name in ignored_file_names:
                continue
            file_paths.append(os.path.join(child_dir_path, file_name))

    return file_paths
