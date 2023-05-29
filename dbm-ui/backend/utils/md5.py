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

import hashlib


def _count_md5(content):
    if content is None:
        return None
    m2 = hashlib.md5()
    if isinstance(content, str):
        m2.update(content.encode("utf8"))
    else:
        m2.update(content)
    return m2.hexdigest()


def count_md5(content, dict_sort=True):
    if dict_sort and isinstance(content, dict):
        # dict的顺序受到hash的影响，所以这里先排序再计算MD5
        return count_md5([(str(k), count_md5(content[k])) for k in sorted(content.keys())])
    elif isinstance(content, (list, tuple)):
        content = sorted([count_md5(k) for k in content])
    return _count_md5(str(content))
