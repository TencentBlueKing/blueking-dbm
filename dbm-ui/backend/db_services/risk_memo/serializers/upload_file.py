"""
Tencent is pleased to support the open source community by making 蓝鲸智云PaaS平台社区版 (BlueKing PaaS Community
Edition) available.
Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at
http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from django.utils.translation import ugettext as _
from rest_framework import serializers

from backend.db_services.risk_memo.constants import IMAGE_MAX_MB, SUPPORTED_IMAGE_TYPES


class UploadImageSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        if value.size // 1024 // 1024 > IMAGE_MAX_MB:
            raise serializers.ValidationError(_(f"Image size exceeds the maximum limit of {IMAGE_MAX_MB}MB"))

        if value.name.split(".")[-1] not in SUPPORTED_IMAGE_TYPES:
            raise serializers.ValidationError(
                _(
                    f"Image type not supported. Please upload a file of the following types: {','.join(SUPPORTED_IMAGE_TYPES)}"
                )
            )

        return value


class UploadFileResponseSerializer(serializers.Serializer):
    url = serializers.URLField()
