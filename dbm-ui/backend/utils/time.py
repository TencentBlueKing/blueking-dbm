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
import datetime
import time
from bisect import bisect_right
from typing import List, Optional, Union

from dateutil.parser import ParserError as TimeParserError
from dateutil.parser import parse as time_parse
from django.utils import timezone
from django.utils.timezone import make_aware
from django.utils.translation import ugettext_lazy as _

from backend.constants import DATE_PATTERN, DATETIME_PATTERN
from backend.exceptions import AppBaseException, ValidationError


def strptime(
    date_string: Optional[str], time_fmt: str = DATETIME_PATTERN, raise_if_none: bool = False
) -> datetime.datetime:
    """
    将时间字符串转化为时间对象，若为None时且不指定抛出异常，默认返回当前时区此时此刻的时间对象
    """
    if isinstance(date_string, str):
        return make_aware(datetime.datetime.strptime(date_string, time_fmt))
    if date_string is None and raise_if_none:
        raise ValidationError("date_string can not be none")
    return timezone.now()


def remove_timezone(date_string: str, time_fmt: str = DATETIME_PATTERN) -> str:
    """
    去掉字符串中的时区
    """
    try:
        datetime_obj = time_parse(date_string)
        return datetime2str(datetime_obj, time_fmt)
    except TimeParserError:
        # 如果转换失败，则直接返回原值
        return date_string


def datetime2str(o_datetime: datetime.datetime, fmt: str = DATETIME_PATTERN) -> str:
    if isinstance(o_datetime, str):
        return o_datetime

    if timezone.is_aware(o_datetime):
        # translate to time in local timezone
        o_datetime = timezone.localtime(o_datetime)
    return datetime.datetime.strftime(o_datetime, fmt)


def str2datetime(datetime_str: str, fmt: str = DATETIME_PATTERN) -> datetime.datetime:
    if isinstance(datetime_str, datetime.datetime):
        return datetime_str

    return datetime.datetime.strptime(datetime_str, fmt)


def date2str(o_date: datetime.date, fmt: str = DATE_PATTERN) -> str:
    return datetime.date.strftime(o_date, fmt)


def datetime2timestamp(o_datetime: Optional[datetime.datetime]) -> float:
    if o_datetime:
        return time.mktime(o_datetime.timetuple())
    return 0.0


def calculate_cost_time(
    end_time: Optional[Union[datetime.datetime, str]],
    start_time: Optional[Union[datetime.datetime, str]],
) -> int:
    """计算耗时"""
    if isinstance(start_time, str) or start_time is None:
        start_time = strptime(start_time)
    if isinstance(end_time, str) or end_time is None:
        end_time = strptime(end_time)
    return (end_time - start_time).seconds


def timestamp2str(timestamp: int, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    timestamp = int(timestamp)
    return datetime2str(datetime.datetime.fromtimestamp(timestamp), fmt)


def countdown2str(countdown: Union[int, datetime.timedelta]) -> str:
    """
    自定义倒计时时间的格式化，格式为类似: 1day, 5h32m45s
    :param countdown: 倒计时，单位为s(即unix时间戳)
    """

    if isinstance(countdown, datetime.timedelta):
        countdown = int(countdown.total_seconds())

    time_unit_list = [("day, ", 24 * 60 * 60), ("h", 60 * 60), ("m", 60), ("s", 1)]
    countdown_format_str = []
    for unit in time_unit_list:
        unit_value = int(countdown // unit[1])
        countdown = countdown % unit[1]
        if unit_value:
            countdown_format_str.append(f"{unit_value}{unit[0]}")

    return "".join(countdown_format_str)


def find_nearby_time(
    time_keys: List[Union[datetime.datetime, str]], match_time: Union[datetime.datetime, str], flag: int
) -> int:
    """
    寻找最近的时间点index
    :param time_keys: 时间列表，请保证这个时间列表是有序的
    :param match_time: 待匹配时间
    :param flag: 搜索类型, 1 --> 小于等于；0 ---> 大于等于
    """
    if not time_keys:
        return 0

    if type(time_keys[0]) != type(match_time):
        raise AppBaseException(_("类型{}与类型{}之间不允许进行比较").format(type(time_keys[0]), type(match_time)))

    if match_time in time_keys:
        return time_keys.index(match_time)

    # 越界的情况抛出错误，交给业务逻辑处理
    index = bisect_right(time_keys, match_time) - flag
    if index < 0 or index >= len(time_keys):
        raise IndexError(_("无法找到合适的附近时间点"))

    return index
