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


class DnsApiMock(object):
    """GcsDns的mock类"""

    @classmethod
    def recycle_domain_record(cls, payload):
        assert payload["app"] is not None
        assert payload["domains"] is not None

    @classmethod
    def delete_domain(cls, payload):
        assert payload["app"] is not None
        assert payload["domains"] is not None

    @classmethod
    def create_domain(cls, payload):
        assert payload["app"] is not None
        assert payload["domains"] is not None
