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
from typing import Any, Dict, List, Union

from django.utils.translation import ugettext_lazy as _

from backend.components.exception import DataAPIException


def get_first_item_from_list(resp: Dict[str, Union[Any, List[Any]]]) -> Any:
    """获取列表中的第一个元素"""
    try:
        resp["data"] = resp["data"][0]
    except IndexError:
        raise DataAPIException(resp, _("接口返回数据为空，请检查接口数据是否正常"))
    return resp
