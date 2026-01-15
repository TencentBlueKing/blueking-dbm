"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

import ipaddress

from django.utils.translation import gettext_lazy as _


def sort_by_ip_port(data_list):
    """
    按照IP地址和端口号对列表进行排序

    参数:
        data_list: 包含字典的列表，每个字典需要有'ip'和'port'字段

    返回:
        排序后的列表
    """

    def sort_key(item):
        # 将IP地址转换为整数以便正确排序
        ip_int = int(ipaddress.IPv4Address(item["ip"]))
        port = item["port"]
        return (ip_int, port)

    return sorted(data_list, key=sort_key)


def bytes_to_human(self, size: int, precision: int = 2) -> str:
    """
    将字节数自动转换为带单位的字符串（B / KB / MB / GB / TB / PB）

    :param size: 字节数（可以是 int 或 float，但通常是 int）
    :param precision: 保留小数位数
    :return: 例如 "123.46 MB"
    """
    # 处理负数
    if size < 0:
        raise ValueError(_("size 不能为负数"))

    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    index = 0
    size = float(size)

    while size >= 1024 and index < len(units) - 1:
        size /= 1024.0
        index += 1

    return f"{size:.{precision}f} {units[index]}"
