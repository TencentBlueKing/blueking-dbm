# -*- coding: utf-8 -*-
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
import os
import requests

import backend.version_log.config as config

from datetime import datetime
from dateutil.relativedelta import relativedelta

from backend.version_log.utils import get_latest_version


def auto_sync_version_log():
    response = requests.get("https://api.github.com/repos/TencentBlueKing/blueking-dbm/releases")
    res_data = response.json()
    latest_version = get_latest_version()
    for release in res_data:
        log_time = release.get("published_at") if release.get("published_at") else release.get("created_at")
        given_date = datetime.fromisoformat(log_time.replace("Z", "+00:00")).date()
        current_utc = datetime.now().date()
        one_month_ago = current_utc - relativedelta(months=1)
        # 判断是不是一个月内的
        if one_month_ago <= given_date:
            dt = datetime.strptime(log_time, "%Y-%m-%dT%H:%M:%SZ")
            formatted_date = dt.strftime("%Y%m%d")
            file_name = "V{}_{}.md".format(release["name"], formatted_date)
            # 数据返回是从最新时间在前，所以当拿到当前的最新版本与返回的版本相匹配上说明已全部加载
            if latest_version in file_name:
                return
            file_path = os.path.join(config.MD_FILES_DIR, file_name)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("## {} - {}\n\n{}".format(release["name"], dt.strftime("%Y-%m-%d"), release["body"]))


if __name__ == '__main__':
    auto_sync_version_log()
