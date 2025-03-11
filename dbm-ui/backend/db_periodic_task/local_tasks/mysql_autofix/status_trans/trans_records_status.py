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
from .inplace_status import trans_to_replace, update_inplace_status
from .replace_status import skip_replace, update_replace_status


def trans_records_status():
    # 更新原地自愈记录的状态
    update_inplace_status()
    # 原地自愈失败的, 流转到替换自愈
    trans_to_replace()
    # 原地自愈成功的, 结束自愈, 跳过替换自愈步骤
    skip_replace()
    # 更新替换自愈状态
    update_replace_status()
