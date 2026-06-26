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

import logging
from typing import List

from django.utils.translation import gettext as _

from backend.core.storages.constants import STAGING_PREFIX
from backend.exceptions import PermissionDeniedError
from backend.flow.consts import MediumEnum
from backend.iam_app.dataclass.actions import ActionEnum, ActionMeta
from backend.iam_app.dataclass.resources import ResourceEnum, ResourceMeta
from backend.iam_app.handlers.drf_perm.base import ResourceActionPermission, get_request_key_id

logger = logging.getLogger("root")


class StoragePermission(ResourceActionPermission):
    """
    制品库相关鉴权。制品库的路径分为两种：
    1. {db_type}/{pkg_type}/{version}/{filename} -- 表示版本介质文件
        鉴权根据db_type
    2. {db_type}/{file_type}/{bk_biz_id}/... -- 表示业务临时文件(sql文件，dump文件等)
        鉴权根据bk_biz_id
    暂存区路径为上述路径加上 /staging 前缀，鉴权时按剔除前缀后的正式路径判定。
    """

    def __init__(self, actions: List[ActionMeta] = None, resource_meta: ResourceMeta = None) -> None:
        instance_ids_getter = self.instance_id_getter
        super().__init__(actions, resource_meta, instance_ids_getter)

    @staticmethod
    def trim_staging_prefix(path: str) -> str:
        """剔除暂存区前缀，使暂存区路径与正式路径的段位对齐"""
        segments = path.strip("/").split("/")
        if segments and segments[0] == STAGING_PREFIX.strip("/"):
            segments = segments[1:]
        return "/".join(segments)

    def instance_id_getter(self, request, view):
        file_path = get_request_key_id(request, "file_path")
        file_path_list = get_request_key_id(request, "file_path_list") or [file_path]
        # 暂存区文件与正式文件的权限语义一致，统一按正式路径解析
        file_path_list = [self.trim_staging_prefix(path) for path in file_path_list if path]
        medium_types = MediumEnum.get_values()

        # 解析路径下的文件类型
        try:
            is_all_pkg = set([(path.strip("/").split("/")[1] in medium_types) for path in file_path_list])
        except IndexError:
            raise PermissionDeniedError(_("文件操作路径{}不合法，请联系管理员").format(file_path_list))

        # 保证文件列表都是同种类型，即不允许同时操作介质文件和业务文件(一般也无此需求)
        if len(is_all_pkg) > 1:
            raise PermissionDeniedError(_("不允许同时操作业务临时文件和介质文件"))

        # 版本文件 对应 PACKAGE_MANAGE，业务文件 对应 DB_MANAGE
        try:
            if is_all_pkg.pop():
                self.actions = [ActionEnum.PACKAGE_VIEW]
                self.resource_meta = ResourceEnum.DBTYPE
                db_types = set([path.strip("/").split("/")[0] for path in file_path_list])
                return list(db_types)
            else:
                self.actions = [ActionEnum.DB_MANAGE]
                self.resource_meta = ResourceEnum.BUSINESS
                bk_biz_ids = set([int(path.strip("/").split("/")[2]) for path in file_path_list])
                return list(bk_biz_ids)
        except Exception:
            logger.error(_("文件操作路径{}不合法，请联系管理员").format(file_path_list))
            # TODO: 暂时屏蔽校验，一个月后放开
            # raise PermissionDeniedError(_("文件操作路径{}不合法，请联系管理员").format(file_path_list))
