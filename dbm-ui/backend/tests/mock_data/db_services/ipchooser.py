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
from backend.tests.mock_data.components.cc import MOCK_GET_BIZ_INTERNAL_MODULE_RETURN


class ResourceQueryHelperMock:
    """ResourceQueryHelper相关接口mock"""

    @staticmethod
    def get_biz_internal_module(*args, **kwargs):
        return MOCK_GET_BIZ_INTERNAL_MODULE_RETURN
