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
import pytest

from backend.core.encrypt.constants import AsymmetricCipherConfigType
from backend.core.encrypt.serializers import FetchPublicKeysSerializer


class TestFetchPublicKeysSerializer:
    def test_default_is_password(self):
        serializer = FetchPublicKeysSerializer(data={})
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["names"] == [AsymmetricCipherConfigType.PASSWORD.value]

    def test_password_allowed(self):
        serializer = FetchPublicKeysSerializer(data={"names": [AsymmetricCipherConfigType.PASSWORD.value]})
        assert serializer.is_valid(), serializer.errors

    @pytest.mark.parametrize(
        "names",
        [
            [AsymmetricCipherConfigType.PROXYPASS.value],
            [AsymmetricCipherConfigType.CLOUD.value],
            [AsymmetricCipherConfigType.get_cipher_cloud_name(0)],
            [AsymmetricCipherConfigType.PASSWORD.value, AsymmetricCipherConfigType.PROXYPASS.value],
        ],
    )
    def test_internal_keys_rejected(self, names):
        serializer = FetchPublicKeysSerializer(data={"names": names})
        assert not serializer.is_valid()
        assert "names" in serializer.errors
