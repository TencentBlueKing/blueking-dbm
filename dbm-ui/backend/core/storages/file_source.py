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

from typing import Any, Dict, Optional

from django.utils.translation import ugettext_lazy as _

from backend.components import JobApi
from backend.utils.md5 import count_md5

from ... import env
from . import constants, exceptions, models


def get_valid_storage_alias(storage_type: str) -> str:
    storage_type_alias = constants.StorageType.get_member_value__alias_map().get(storage_type)
    if storage_type_alias is None:
        raise exceptions.FilesStorageTypeError(
            _("storage_type must be one of {choices}").format(choices={constants.StorageType.list_choices()})
        )
    return storage_type_alias


class BkJobFileCredentialManager:
    # 文件凭证名称
    CREDENTIAL_NAME_TMPL: str = "DBM_{storage_type}"
    CREDENTIAL_DESCRIPTION_TMPL = _("DBM[biz-{bk_biz_id}]{storage_type_alias}文件凭证")

    @classmethod
    def gen_credential_name(cls, storage_type: str) -> str:
        """
        生成凭证名称
        :param storage_type: 文件源类型
        :return: 凭证名称
        """
        return cls.CREDENTIAL_NAME_TMPL.format(storage_type=storage_type)

    @classmethod
    def gen_credential_description(cls, bk_biz_id: int, storage_type: str) -> str:
        """
        生成凭证描述
        :param bk_biz_id: 业务ID
        :param storage_type: 文件源类型
        :return: 凭证描述
        """
        return cls.CREDENTIAL_DESCRIPTION_TMPL.format(
            bk_biz_id=bk_biz_id, storage_type_alias=get_valid_storage_alias(storage_type=storage_type)
        )

    @classmethod
    def register_credential(
        cls,
        bk_biz_id: int,
        storage_type: str,
        credential_type: str,
        credential_auth_info: Dict[str, str],
    ) -> models.BKJobFileCredential:
        """
        注册文件凭证
        :param bk_biz_id: 业务ID
        :param storage_type: 文件源类型，参考 constants.StorageType
        :param credential_type: 凭证认证类型
        :param credential_auth_info: 凭证认证信息
            credential_access_key 凭证类型为ACCESS_KEY_SECRET_KEY时填写
            credential_secret_key 凭证类型为 ACCESS_KEY_SECRET_KEY / SECRET_KEY 时填写
            credential_username 凭证类型为 USERNAME_PASSWORD 时填写
            credential_password 凭证类型为 USERNAME_PASSWORD / PASSWORD 时填写
        :return: models.BKJobFileCredential
        """

        name = cls.gen_credential_name(storage_type=storage_type)
        description = cls.gen_credential_description(bk_biz_id=bk_biz_id, storage_type=storage_type)

        # 交给作业平台执行参数校验，无需冗余校验
        create_credential_query_params = {
            "bk_biz_id": bk_biz_id,
            "type": credential_type,
            "name": name,
            "description": description,
            **credential_auth_info,
        }
        try:
            credential_id = JobApi.create_credential(create_credential_query_params)["id"]
        except Exception as err:
            raise exceptions.FilesRegisterCredentialError(
                _("注册凭证失败：bk_biz_id -> {bk_biz_id}, err_msg -> {err_msg}").format(bk_biz_id=bk_biz_id, err_msg=err)
            )

        # 查询 bk_biz_id & storage_type 是否已存在注册凭证，有则更新，无则创建
        credential_obj, __ = models.BKJobFileCredential.objects.update_or_create(
            bk_biz_id=bk_biz_id,
            storage_type=storage_type,
            defaults={
                "name": name,
                "type": credential_type,
                "credential_id": credential_id,
                "description": description,
            },
        )

        return credential_obj

    @classmethod
    def get_or_create_credential(
        cls,
        bk_biz_id: int,
        storage_type: str,
        credential_type: str,
        credential_auth_info: Dict[str, str],
    ) -> models.BKJobFileCredential:
        """
        获取业务文件凭证，不存在会先行创建
        :param bk_biz_id: 业务ID
        :param storage_type: 文件源类型，参考 constants.StorageType
        :param credential_type: 凭证认证类型
        :param credential_auth_info: 凭证认证信息
            credential_access_key 凭证类型为ACCESS_KEY_SECRET_KEY时填写
            credential_secret_key 凭证类型为 ACCESS_KEY_SECRET_KEY / SECRET_KEY 时填写
            credential_username 凭证类型为 USERNAME_PASSWORD 时填写
            credential_password 凭证类型为 USERNAME_PASSWORD / PASSWORD 时填写
        :return: models.BKJobFileCredential
        """
        try:
            credential = models.BKJobFileCredential.objects.get(bk_biz_id=bk_biz_id, storage_type=storage_type)
            return credential
        except models.BKJobFileCredential.DoesNotExist:
            return cls.register_credential(
                bk_biz_id=bk_biz_id,
                storage_type=storage_type,
                credential_type=credential_type,
                credential_auth_info=credential_auth_info,
            )


class BkJobFileSourceManager:

    FILE_SOURCE_CODE_TMPL: str = "DBM_{storage_type}"
    # 文件源别名
    FILE_SOURCE_ALIAS_TMPL = _("DBM{storage_type_alias}文件源")

    FILE_SOURCE_CACHE: Dict[str, models.BKJobFileSource] = {}

    @classmethod
    def gen_file_source_code(cls, storage_type: str) -> str:
        """
        生成文件源编码
        :param storage_type: 文件源类型
        :return: 文件源编码
        """
        return cls.FILE_SOURCE_CODE_TMPL.format(storage_type=storage_type)

    @classmethod
    def gen_file_source_alias(cls, bk_biz_id: int, storage_type: str) -> str:
        """
        生成文件源别名
        :param bk_biz_id: 业务ID
        :param storage_type: 文件源类型
        :return: 文件源名称
        """
        return cls.FILE_SOURCE_ALIAS_TMPL.format(
            bk_biz_id=bk_biz_id, storage_type_alias=get_valid_storage_alias(storage_type=storage_type)
        )

    @classmethod
    def register_file_source(
        cls,
        credential: models.BKJobFileCredential,
        access_params: Optional[Dict[str, Any]] = None,
    ) -> models.BKJobFileSource:
        """
        注册文件源
        :param credential: 文件凭证model对象
        :param access_params: 文件源接入参数
        :return: models.BKJobFileSource
        """
        access_params = access_params or {}

        # code固定为env.APP_CODE
        # code = cls.gen_file_source_code(storage_type=credential.storage_type)
        code = env.APP_CODE
        alias = cls.gen_file_source_alias(bk_biz_id=credential.bk_biz_id, storage_type=credential.storage_type)

        create_file_source_query_params = {
            "type": credential.storage_type,
            "bk_biz_id": credential.bk_biz_id,
            "credential_id": credential.credential_id,
            "code": code,
            "alias": alias,
            "access_params": access_params,
        }

        try:
            file_source_id = JobApi.create_file_source(create_file_source_query_params)["id"]
        except Exception as err:
            raise exceptions.FilesRegisterCredentialError(
                _("注册文件源失败：bk_biz_id -> {bk_biz_id}, err_msg -> {err_msg}").format(
                    bk_biz_id=credential.bk_biz_id, err_msg=err
                )
            )

        file_source_obj, __ = models.BKJobFileSource.objects.update_or_create(
            credential_id=credential.credential_id,
            defaults={"file_source_id": file_source_id, "code": code, "alias": alias, "access_params": access_params},
        )
        return file_source_obj

    @classmethod
    def get_or_create_file_source(
        cls,
        bk_biz_id: int,
        storage_type: str,
        credential_type: str,
        credential_auth_info: Dict[str, str],
        access_params: Optional[Dict[str, Any]] = None,
    ) -> models.BKJobFileSource:
        """
        获取文件源，不存在会先行创建
        :param bk_biz_id: 业务ID
        :param storage_type: 文件源类型，参考 constants.StorageType
        :param credential_type: 凭证认证类型
        :param credential_auth_info: 凭证认证信息
            credential_access_key 凭证类型为ACCESS_KEY_SECRET_KEY时填写
            credential_secret_key 凭证类型为 ACCESS_KEY_SECRET_KEY / SECRET_KEY 时填写
            credential_username 凭证类型为 USERNAME_PASSWORD 时填写
            credential_password 凭证类型为 USERNAME_PASSWORD / PASSWORD 时填写
        :param access_params: 文件源接入参数
        :return: models.BKJobFileCredential
        """

        credential_info = {
            "bk_biz_id": bk_biz_id,
            "storage_type": storage_type,
            "credential_type": credential_type,
            "credential_auth_info": credential_auth_info,
        }
        query_file_source_params_md5 = count_md5({**credential_info, "access_params": access_params})

        if query_file_source_params_md5 in cls.FILE_SOURCE_CACHE:
            return cls.FILE_SOURCE_CACHE[query_file_source_params_md5]

        credential = BkJobFileCredentialManager.get_or_create_credential(**credential_info)
        try:
            file_source = models.BKJobFileSource.objects.get(credential_id=credential.credential_id)
        except models.BKJobFileSource.DoesNotExist:
            file_source = cls.register_file_source(credential=credential, access_params=access_params)

        file_source.credential = credential
        cls.FILE_SOURCE_CACHE[query_file_source_params_md5] = file_source
        return file_source
