"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""


def get_mysql_real_version(package_name: str) -> str:
    """
    通过传入正确的mysql介质包名称获取到对应的真实版本名称：
    @param  package_name: 介质包名称 例子：mysql-5.7.8-linux-x86_64-tmysql-3.1-gcs.tar.gz
    获取到的真实版本为：5.7.8
    """
    return package_name.split("-")[1]


def get_spider_real_version(package_name: str) -> str:
    """
    通过传入正确的spider介质包名称获取到对应的真实版本名称：
    @param  package_name: 介质包名称 例子：mariadb-10.3.7-linux-x86_64-tspider-3.7.8-gcs.tar.gz
    获取到的真实版本为：3.7.8
    """
    return package_name.split("-")[-2]


def get_proxy_real_version(package_name: str) -> str:
    """
    通过传入正确的spider介质包名称获取到对应的真实版本名称：
    @param  package_name: 介质包名称 例子：mysql-proxy-0.82.10.tar.gz
    获取到的真实版本为：0.82.10
    """
    return package_name.split("-")[-1].replace(".tar.gz", "")
