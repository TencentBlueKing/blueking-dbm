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

from django.utils.translation import ugettext_lazy as _

"""
这里定义的活动节点传入私用变量参数时做数据校验的方法
"""


def validator_exec_ip(exec_ip_value: str, get_trans_data_ip_var_values: str):
    """
    定义exec_ip属性的值做检验方法，这里有顺序要求, 在dataclass定义，exec_ip属性一定在get_trans_data_ip_var后面，才能生效
    @param exec_ip_value: 表示exec_ip当前的值
    @param get_trans_data_ip_var_values： 表示get_trans_data_ip_var当前的值
    """

    if exec_ip_value and get_trans_data_ip_var_values:
        raise ValueError(_("exec_ip变量和get_trans_data_ip_var变量不能同时赋值"))
    if not exec_ip_value and not get_trans_data_ip_var_values:
        raise ValueError(_("exec_ip变量和get_trans_data_ip_var变量不能同时为None"))
    return exec_ip_value
