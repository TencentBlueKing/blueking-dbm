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
from urllib.parse import urljoin

from django.utils.translation import ugettext_lazy as _

from ... import env
from ..base import BaseApi
from ..domains import BKBASE_APIGW_DOMAIN


class _BKBaseApi(BaseApi):
    MODULE = _("基础计算平台")
    BASE = BKBASE_APIGW_DOMAIN

    def __init__(self):
        self.sensitive_text_classification_normal = self.generate_data_api(
            method="POST",
            url="v3/aiops/serving/processing/sensitive_text_classification_normal/execute/",
            description=_("敏感信息识别"),
        )
        self.report_data = self.generate_data_api(
            method="POST",
            url="v4/report_data/",
            description=_("数据上报"),
        )

    def data_desensitization(self, text, bk_biz_id=env.DBA_APP_BK_BIZ_ID):
        """
        敏感信息识别，并把敏感信息转为*
        """
        from ...db_meta.models import AppCache

        app = AppCache.get_appcache("appcache_dict")[str(bk_biz_id)]

        detect_texts = self.sensitive_text_classification_normal(
            {
                "bkdata_authentication_method": "token",
                "bkdata_data_token": env.BKDATA_DATA_TOKEN,
                "bk_app_code": env.APP_CODE,
                "bk_app_secret": env.SECRET_KEY,
                "data": {"inputs": [{"target_content": text}]},
                "config": {
                    # 心跳超时时间
                    "timeout": 30,
                    # 返回结果不包含输入文本
                    "passthrough_input": False,
                    "predict_args": {
                        # 填入可选参数，也可不填入，保持为空即按默认配置检测
                        "input_config": "1,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22",
                        "is_masked": "yes",
                        # 必填参数
                        "bk_app_code": env.APP_CODE,
                        "bk_app_secret": env.SECRET_KEY,
                        "biz_name": f"{app['bk_biz_name']}(#{app['bk_biz_id']})",
                    },
                },
            }
        )
        masked_text = detect_texts["data"]["data"][0]["output"][0]["masked_text"]
        if masked_text == 0:
            # 当 masked_text 为 0 时，表示接口出问题了，直接返回原文本
            return text
        return masked_text

    def get_bkdata_frontend_report_url(self):
        if not env.BKDATA_FRONTEND_DATA_ID:
            return ""
        return urljoin(self.report_data.url, f"{env.BKDATA_FRONTEND_DATA_ID}/")


BKBaseApi = _BKBaseApi()
