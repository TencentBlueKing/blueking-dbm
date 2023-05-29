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

from backend.db_meta import request_validator
from backend.db_meta.exceptions import DbModuleExistException
from backend.db_meta.models import DBModule

logger = logging.getLogger("root")


@transaction.atomic
def create(bk_biz_id: int, name: str, cluster_type: str, creator: str = ""):
    """创建DB模块
    说明：这里的模块与cc无任何关系，仅用于关联配置文件，相当于场景化配置模板，比如gamedb,logdb等
    """
    bk_biz_id = request_validator.validated_integer(bk_biz_id, min_value=0)
    name = request_validator.validated_str(name)
    cluster_type = request_validator.validated_str(cluster_type)

    try:
        db_module = DBModule.objects.create(
            bk_biz_id=bk_biz_id,
            cluster_type=cluster_type,
            db_module_name=name,
        )
    except IntegrityError:
        raise DbModuleExistException(db_module_name=name)

    return model_to_dict(db_module)
