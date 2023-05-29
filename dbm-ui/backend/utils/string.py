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

import json
import re
from typing import Any, List, Optional, Tuple, Union

from django.utils.translation import ugettext

MIN_FORMAT_JSON_LENGTH = 30


def str2bool(string: Union[Optional[str], Any], strict: bool = True) -> bool:
    """
    字符串转布尔值
    对于bool(str) 仅在len(str) == 0 or str is None 的情况下为False，为了适配bool("False") 等环境变量取值情况，定义该函数
    参考：https://stackoverflow.com/questions/21732123/convert-true-false-value-read-from-file-to-boolean
    :param string:
    :param strict: 严格校验，非 False / True / false / true  时抛出异常，用于环境变量的转换
    :return:
    """

    # 如果本身就是bool，则直接返回
    if isinstance(string, bool):
        return string

    if string in ["False", "false"]:
        return False
    if string in ["True", "true"]:
        return True

    if strict:
        raise ValueError(f"{string} can not convert to bool")
    return bool(string)


def pascal_to_snake(camel_case: str):
    """
    大驼峰（帕斯卡）转蛇形
    eg:
     - ClusterAddress --> cluster_address
     - helloWorld ---> hello_world
    :param camel_case: 驼峰字符串
    """

    snake_case = re.sub(r"(?P<key>[A-Z])", r"_\g<key>", camel_case)
    return snake_case.lower().strip("_")


def snake_to_pascal(snake_case: str):
    """
    蛇形转大驼峰（帕斯卡）
    eg:
     - cluster_address --> ClusterAddress
     - hello_world ---> HelloWorld
    :param snake_case: 蛇形字符串
    """
    words = snake_case.split("_")
    return "".join(word.title() for word in words)


def format_json_string(msg: str) -> str:
    """
    将字符串中的字典进行json格式化
    eg: "ext: {a: {b:c}, d: 1}, this is ...., {a: 100}"
    其中{a: {b:c}, d: 1}和{a: 100}就需要被格式化
    我们获取最外层"{"或"["的位置，和最外层"}"或"]"的位置+1，得到一个坐标序列(额外包括首尾位置)：
    [0, 5, 21, 37, 45, 45]
    则偶数间隔区间，即[5: 21], [37: 45]区间需要被json格式化，其余区间不需要被格式化

    本机速率测试：
    字符数(个)    处理时间(s)
    1742000      0.36049
    8710000      1.77394
    87100000     17.8836
    平均每秒处理字符为：4.8e6/s

    :param msg: 待解析字符串
    """

    # TODO: 目前括号匹配实现会有一些处理不到的情况,
    #  比如: {"}": "hello", "{": "world"}, {"]": "hello", "[": "world"}
    #  这类字符串解析出来的格式会乱掉，因为没有考虑去掉被""包裹的括号。
    #  不过如果要排除这种情况实现会相对复杂，而且考虑这种情况较少，所以暂时忽略。

    if not msg:
        return ""

    if not isinstance(msg, str):
        msg = str(msg)

    bracket_match_index_list: List[int] = [0]
    bracket_stack: List[Tuple[str, int]] = []

    # 获取需要格式化的字符区间坐标
    bracket_match_map = {"}": "{", "]": "["}
    for index, char in enumerate(msg):

        # 如果不属于括号的匹配，则排除
        if char not in bracket_match_map.values() and char not in bracket_match_map.keys():
            continue

        # 如果栈为空时字符为反括号，则排除
        if not bracket_stack and char in ["}", "]"]:
            continue

        # 如果是正向括号则放入栈中
        if char in bracket_match_map.values():
            bracket_stack.append((char, index))

        # 如果是反向括号则尝试进行匹配
        if char in bracket_match_map.keys() and bracket_match_map[char] == bracket_stack[-1][0]:
            match_bracket_tuple = bracket_stack.pop()
            # 匹配到格式化区间，加入坐标序
            if not bracket_stack:
                bracket_match_index_list.append(match_bracket_tuple[1])
                bracket_match_index_list.append(index + 1)

    bracket_match_index_list.append(len(msg))

    # 如果json格式化区间字符数过少会导致性能低且格式效果不佳，考虑进行区间合并
    index: int = 0
    merged_bracket_match_index_list: List[List[int]] = []
    while index < len(bracket_match_index_list) - 1:
        be, ed = bracket_match_index_list[index], bracket_match_index_list[index + 1]
        if not (index % 2) or ed - be >= MIN_FORMAT_JSON_LENGTH:
            merged_bracket_match_index_list.append([be, ed])
        else:
            # 合并上一个区间和下一个区间
            index += 1
            merged_bracket_match_index_list[-1][1] = bracket_match_index_list[index + 1]

        index += 1

    # 切割字符，格式化命中区间
    format_msg_list = []
    for index in range(len(merged_bracket_match_index_list)):
        be, ed = merged_bracket_match_index_list[index]
        if not msg[be:ed]:
            continue

        # 偶数区间为非命中区间，忽略。
        if not (index % 2):
            format_msg = msg[be:ed]
        # 用json格式化字典数据字符串
        else:
            try:
                # 注意因为json的限制，字典里的引号必须为双引号
                format_msg = json.dumps(json.loads(msg[be:ed].replace("'", '"')), indent=2)
            except json.JSONDecodeError:
                # 如果用json无法尝试解析，则尝试用eval解析 TODO：⚠️ eval解析比json解析慢10倍, 是否需要兼容?
                try:
                    format_msg = json.dumps(eval(msg[be:ed]), indent=2)
                except Exception:  # pylint: disable=broad-except
                    format_msg = msg[be:ed]

        format_msg_list.append(format_msg)

    return "\n".join(format_msg_list)


def i18n_str(string):
    # 翻译字符串
    if isinstance(string, str):
        return ugettext(string)

    return string
