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
import re

from django.utils.crypto import get_random_string


def generate_valid_domain(cluster_name: str, prefix: str = "rb", suffix: str = "db", max_length: int = 48) -> str:
    """
    生成符合规则的域名

    根据cluster_name生成域名，并进行长度限制和正则校验。
    如果生成的域名不符合规则，则生成随机域名。

    @param cluster_name: 集群名称
    @param prefix: 域名前缀，默认为 "rb"
    @param suffix: 域名后缀，默认为 "db"
    @param max_length: 域名最大长度，默认为 48
    @return: 符合规则的域名字符串

    域名格式: {prefix}.{cluster_name}.{suffix}
    域名规则:
    1. 长度不超过 max_length 个字符
    2. 符合正则表达式: ^[a-z0-9A-Z]([a-z0-9A-Z\\-_.]*[a-z0-9A-Z])?$
    """
    # 生成初始域名
    domain = "{}.{}.{}".format(prefix, cluster_name, suffix)

    # 检查域名长度，如果超过限制则截断
    if len(domain) > max_length:
        # 计算固定部分长度: "prefix." + ".suffix" = len(prefix) + len(suffix) + 2
        fixed_part_len = len(prefix) + len(suffix) + 2
        max_cluster_name_len = max_length - fixed_part_len
        cluster_name_truncated = cluster_name[:max_cluster_name_len]
        domain = "{}.{}.{}".format(prefix, cluster_name_truncated, suffix)

    # 校验域名是否符合正则规则，如果不符合则随机生成
    domain_pattern = r"^[a-z0-9A-Z]([a-z0-9A-Z\-_.]*[a-z0-9A-Z])?$"
    if not re.match(domain_pattern, domain):
        # 生成随机域名: {prefix}.{random}.{suffix}
        random_part = get_random_string(8, allowed_chars="abcdefghijklmnopqrstuvwxyz0123456789")
        domain = "{}.{}.{}".format(prefix, random_part, suffix)

    return domain
