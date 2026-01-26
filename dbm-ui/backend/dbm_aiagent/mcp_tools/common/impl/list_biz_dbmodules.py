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
from typing import List

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.db_meta.models import DBModule


def list_biz_dbmodules(bk_biz_id: int) -> List:
    dbmodule_objs = DBModule.objects.filter(bk_biz_id=bk_biz_id)

    res = []
    for dbmodule_obj in dbmodule_objs:
        try:
            c_res = DBConfigApi.query_conf_item(
                {
                    "bk_biz_id": str(bk_biz_id),
                    "level_name": LevelName.MODULE,
                    "level_value": str(dbmodule_obj.db_module_id),
                    "namespace": dbmodule_obj.cluster_type,
                    "conf_file": "deploy_info",
                    "conf_type": "deploy",
                    "format": FormatType.MAP,
                }
            )
            res.append(
                {
                    "bk_biz_id": bk_biz_id,
                    "cluster_type": dbmodule_obj.cluster_type,
                    "alias_name": dbmodule_obj.alias_name,
                    "db_module_id": dbmodule_obj.db_module_id,
                    "charset": c_res["content"]["charset"],
                    "db_version": c_res["content"]["db_version"],
                }
            )
        except Exception as e:
            raise e
    return res
