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

from django.db import IntegrityError, transaction
from django.forms import model_to_dict
from django.utils.translation import gettext_lazy as _

from backend.db_meta import request_validator
from backend.db_meta.api.db_module.version import describe_module_version, validate_components
from backend.db_meta.dataclass import DBModuleComponentVersion
from backend.db_meta.exceptions import DbModuleExistException, DBModuleVersionException
from backend.db_meta.models import DBModule

logger = logging.getLogger("root")


@transaction.atomic
def create(
    bk_biz_id: int,
    name: str,
    cluster_type: str,
    alias: str = "",
    creator: str = "",
    db_versions: dict = None,
):
    """创建DB模块
    说明：这里的模块与cc无任何关系，仅用于关联配置文件，相当于场景化配置模板，比如gamedb,logdb等
    db_versions 为 {组件名: DBModuleComponentVersion}。纳入约束的集群类型必须带齐各层。
    """
    bk_biz_id = request_validator.validated_integer(bk_biz_id, min_value=0)
    name = request_validator.validated_str(name)
    alias_name = alias or name
    cluster_type = request_validator.validated_str(cluster_type)
    db_module = DBModule(
        bk_biz_id=bk_biz_id,
        cluster_type=cluster_type,
        db_module_name=name,
        alias_name=alias_name,
        creator=creator,
        updater=creator,
    )
    db_module.current_db_version = db_versions or {}
    validate_components(db_module.current_db_version)

    try:
        db_module.save()
    except IntegrityError:
        raise DbModuleExistException(db_module_name=name)

    result = model_to_dict(db_module)
    result["db_version_info"] = describe_module_version(db_module)
    return result


@transaction.atomic
def update_permit_os(bk_biz_id: int, db_module_id: int, db_versions: dict) -> dict:
    """只更新已有组件的操作系统约束，不改 db_version_id。"""
    bk_biz_id = request_validator.validated_integer(bk_biz_id, min_value=0)
    db_module_id = request_validator.validated_integer(db_module_id, min_value=1)
    if not db_versions:
        raise DBModuleVersionException(message=_("请指定要修改的组件操作系统"))
    try:
        db_module = DBModule.objects.get(bk_biz_id=bk_biz_id, db_module_id=db_module_id)
    except DBModule.DoesNotExist:
        raise DBModuleVersionException(message=_("模块 {} 不存在").format(db_module_id))

    current = db_module.current_db_version
    unset = sorted(set(db_versions) - set(current))
    if unset:
        raise DBModuleVersionException(message=_("组件 {} 尚未设置版本，不能只修改操作系统").format(",".join(unset)))

    layers = {
        component: DBModuleComponentVersion.from_dict({**raw, "db_version_id": current[component].db_version_id})
        for component, raw in db_versions.items()
    }
    validate_components(layers)
    db_module.current_db_version = layers
    db_module.save()
    return {"db_module_id": db_module.db_module_id, "db_version_info": describe_module_version(db_module)}
