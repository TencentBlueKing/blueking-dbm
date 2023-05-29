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
from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Any, Callable, Dict, List, Union

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.core.files.storage import Storage
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _

from backend.components import JobApi

from . import constants, exceptions, models


class StorageFileOverwriteMixin:

    file_overwrite = settings.FILE_OVERWRITE

    def get_available_name(self, name, max_length=None):
        """重写获取文件有效名称函数，支持在 file_overwrite=True 时不随机生成文件名"""

        dir_name, file_name = os.path.split(name)
        file_root, file_ext = os.path.splitext(file_name)

        def _gen_random_name(_file_root) -> str:
            # 在文件名的起始位置添加随机串，源码规则为 "%s_%s%s" % (_file_root, get_random_string(7), file_ext)
            # 上述规则对 .tar.gz 不友好，会在类型后缀中间加随机串，所以改为随机串作为前缀
            return os.path.join(dir_name, "%s_%s%s" % (get_random_string(7), _file_root, file_ext))

        # not self.file_overwrite and self.exists(name) 利用 and 短路特点，如果 file_overwrite=True 就无需校验文件是否存在
        while (not self.file_overwrite and self.exists(name)) or (max_length and len(name) > max_length):
            # file_ext includes the dot.
            name = name if self.file_overwrite else _gen_random_name(file_root)

            if max_length is None:
                continue
            # Truncate file_root if max_length exceeded.
            truncation = len(name) - max_length
            if truncation > 0:
                file_root = file_root[:-truncation]
                # Entire file_root was truncated in attempt to find an available filename.
                if not file_root:
                    raise SuspiciousFileOperation(
                        'Storage can not find an available filename for "%s". '
                        "Please make sure that the corresponding file field "
                        'allows sufficient "max_length".' % name
                    )
                name = name if self.file_overwrite else _gen_random_name(file_root)
        return name


class BkJobMixin:
    @abstractmethod
    def _handle_file_source_list(
        self, file_source_list: List[Dict[str, Any]], extra_transfer_file_params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        预处理源文件列表，添加文件源等信息
        :param file_source_list: 源文件
        :param extra_transfer_file_params: transfer_files 的其他参数
        :return: 源文件对象列表
        """
        raise NotImplementedError

    @classmethod
    def gen_transfer_file_log(cls, file_target_path: str, file_source_list: List[Dict[str, Any]]) -> str:
        """
        生成文件分发日志
        :param file_target_path: 文件分发目标路径
        :param file_source_list: 源文件列表
        :return: 日志字符串
        """

        third_part_file_source_ids: List[str] = [
            file_source["file_source_id"]
            for file_source in file_source_list
            if file_source.get("file_type") == constants.JobFileType.THIRD_PART.value
        ]

        # 获取第三方文件源信息，判空避免无效IO
        if third_part_file_source_ids:
            third_part_file_source_infos = models.BKJobFileSource.objects.filter(
                file_source_id__in=third_part_file_source_ids
            ).values("file_source_id", "alias")
            file_source_id__info_map = {
                third_part_file_source_info["file_source_id"]: third_part_file_source_info
                for third_part_file_source_info in third_part_file_source_infos
            }
        else:
            file_source_id__info_map = {}

        # 源文件分发日志
        files_transfer_log_list: List[str] = []
        # 遍历源文件分发列表，一般来说该列表长度为1
        for file_source in file_source_list:
            file_type = file_source.get("file_type", constants.JobFileType.SERVER.value)
            file_type_alias = constants.JobFileType.get_member_value__alias_map().get(file_type, _("未知文件源"))

            if file_type == constants.JobFileType.THIRD_PART.value:
                source_info_str = _("{file_type_alias}-{file_source_alias}").format(
                    file_type_alias=file_type_alias,
                    file_source_alias=file_source_id__info_map[file_source["file_source_id"]]["alias"],
                )
            elif file_type == constants.JobFileType.SERVER.value:
                server_ip_str_set = {
                    f"{ip_info['bk_cloud_id']}-{ip_info['ip']}" for ip_info in file_source["server"]["ip_list"]
                }
                source_info_str = _("{file_type_alias}-{server_ips_str}").format(
                    file_type_alias=file_type_alias, server_ips_str=",".join(server_ip_str_set)
                )
            else:
                source_info_str = _("未知文件源-{file_type}").format(file_type=file_type)

            files_transfer_log_list.append(
                _("从 [{source_info_str}] 下发文件 [{file_list_str}] 到目标机器路径 [{file_target_path}]").format(
                    source_info_str=source_info_str,
                    file_list_str=",".join(file_source.get("file_list")),
                    file_target_path=file_target_path,
                )
            )

        return "\n".join(files_transfer_log_list)

    def process_query_params(
        self, job_api_func: Callable[[Dict[str, Any]], Dict[str, Any]], query_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        预处理请求参数
        :param job_api_func: JobApi method
        :param query_params: 请求参数
        :return: 预处理后的参数
        """
        # 如果后续预处理的job api增多，考虑拆分逻辑
        if job_api_func == JobApi.fast_transfer_file:
            query_params = deepcopy(query_params)
            query_params["file_source_list"] = self._handle_file_source_list(
                file_source_list=query_params.get("file_source_list", []), extra_transfer_file_params=query_params
            )
        return query_params

    def fast_transfer_file(
        self,
        bk_biz_id: int,
        task_name: str,
        timeout: int,
        account_alias: str,
        file_target_path: str,
        file_source_list: List[Dict[str, Any]],
        target_server: Dict[str, List[Dict[str, Union[str, int]]]],
        **kwargs,
    ) -> int:
        """
        分发文件
        :param bk_biz_id: 业务ID
        :param task_name: 任务名称
        :param timeout: 超时时间
        :param account_alias: 目标执行账号别名
        :param file_target_path: 文件目标路径
        :param file_source_list: 源文件路径列表
        :param kwargs: 额外的调用参数
        :param target_server: 目标服务器
            可选：
            1. ip_list - 静态IP列表
                bk_cloud_id - 云区域ID
                ip - IP地址
            2. dynamic_group_list - 动态分组ID列表
            3. topo_node_list - 动态topo节点列表
                id - 动态topo节点ID，对应CMDB API 中的 bk_inst_id
                node_type - 动态topo节点类型，对应CMDB API 中的 bk_obj_id,比如"module","set"
            target_server 示例
            {
                "ip_list": [
                    {"bk_cloud_id": 0, "ip": "127.0.0.1"},
                    {"bk_cloud_id": 0, "ip": "127.0.0.2"}
                ]
            }
        :return: 作业实例ID
        """

        base_transfer_file_params = deepcopy(
            {
                "bk_biz_id": bk_biz_id,
                "task_name": task_name,
                "timeout": timeout,
                "account_alias": account_alias,
                "file_target_path": file_target_path,
                "target_server": target_server,
                **kwargs,
            }
        )

        # 根据文件源对文件路径列表进行处理，并返回源文件对象数组
        file_source_list = self._handle_file_source_list(
            file_source_list=deepcopy(file_source_list), extra_transfer_file_params=base_transfer_file_params
        )

        try:
            job_instance_id = JobApi.fast_transfer_file(
                {"file_source_list": file_source_list, **base_transfer_file_params}
            )["job_instance_id"]

        except Exception as err:
            # 捕获异常并抛出当前层级的异常
            raise exceptions.FilesTransferError(_("文件分发错误：err_msg -> {err_msg}").format(err_msg=err))

        return job_instance_id


class BaseStorage(StorageFileOverwriteMixin, BkJobMixin, Storage, ABC):
    storage_type: str = None

    def get_file_md5(self, file_name: str) -> str:
        raise NotImplementedError
