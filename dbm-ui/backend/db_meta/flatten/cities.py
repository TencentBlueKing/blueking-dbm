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
from typing import Dict, List

from django.db.models import QuerySet
from django.forms import model_to_dict


def cities(cities_qs: QuerySet) -> List[Dict]:
    city_list = list(
        cities_qs.prefetch_related(
            "logical_city",
        )
    )
    return [{**model_to_dict(city), **{"logical_city": model_to_dict(city.logical_city)}} for city in city_list]
