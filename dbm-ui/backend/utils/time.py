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

from dateutil.parser import parse as time_parse
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from backend.constants import DATE_PATTERN, DATETIME_PATTERN
from backend.exceptions import AppBaseException, ValidationError


def strptime(date_string: Optional[str], raise_if_none: bool = False) -> datetime.datetime:
    """
    将时间字符串转化为时间对象，若为None时且不指定抛出异常，默认返回当前时区此时此刻的时间对象
    """
    if isinstance(date_string, str):
        # return make_aware(datetime.datetime.strptime(date_string, time_fmt))
        return str2datetime(date_string)
    if date_string is None and raise_if_none:
        raise ValidationError("date_string can not be none")
    return timezone.now()


def timezone2timestamp(date: Union[str, datetime.datetime]) -> int:
    """
    将带时区时间(如果时间无时区则取的是环境时区)转换为时间戳(精确到s)
    """
    if isinstance(date, (int, float)):
        return date
    if isinstance(date, datetime.datetime):
        return int(date.timestamp())
    return int(time_parse(date).timestamp())


def datetime2str(o_datetime: datetime.datetime, fmt: str = DATETIME_PATTERN, aware_check: bool = True) -> str:
    """
    将时间对象转换为时间字符串，可选时区强校验
    """
    if isinstance(o_datetime, str):
        return o_datetime

    if aware_check and not timezone.is_aware(o_datetime):
        raise ValidationError(f"[{timezone}] Time zone check failed...")

    o_datetime = timezone.localtime(o_datetime)
    # 可读性优化，暂时去掉毫秒单位。TODO：时间是否需要完全精准？
    o_datetime = o_datetime.replace(microsecond=0)
    # return datetime.datetime.strftime(o_datetime, fmt)
    return o_datetime.isoformat()


def str2datetime(datetime_str: str, fmt: str = DATETIME_PATTERN, aware_check: bool = True) -> datetime.datetime:
    """
    将时间字符串转换为时间对象，可选时区强校验
    """
    if isinstance(datetime_str, datetime.datetime):
        return datetime_str

    o_datetime = time_parse(datetime_str)

    if aware_check and not timezone.is_aware(o_datetime):
        raise ValidationError(f"[{timezone}] Time zone check failed...")

    return o_datetime


def compare_time(time1: str, time2: str):
    time1 = time1 if isinstance(time1, datetime.datetime) else str2datetime(time1)
    time2 = time2 if isinstance(time2, datetime.datetime) else str2datetime(time2)
    return time1 > time2


def standardized_time_str(datetime_str: str):
    """
    将不带时区的时间字符串转换为带时区的字符串，时区为服务器时区
    """
    o_datetime = str2datetime(datetime_str, aware_check=False).astimezone(timezone.utc)
    return datetime2str(o_datetime)


def datetime2timestamp(o_datetime: Optional[datetime.datetime]) -> float:
    if o_datetime:
        return time.mktime(o_datetime.timetuple())
    return 0.0


def date2str(o_date: datetime.date, fmt: str = DATE_PATTERN) -> str:
    return datetime.date.strftime(o_date, fmt)


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


def timestamp2str(timestamp: int) -> str:
    timestamp = int(timestamp)
    return datetime2str(datetime.datetime.fromtimestamp(timestamp).astimezone())


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

    # 统一转换成timestamp进行比较
    if isinstance(match_time, str):
        match_time = time_parse(match_time).timestamp()
        time_keys = [time_parse(t).timestamp() for t in time_keys]
    elif isinstance(match_time, datetime.datetime):
        match_time = match_time.timestamp()
        time_keys = [t.timestamp() for t in time_keys]

    # 越界的情况抛出错误，交给业务逻辑处理
    index = bisect_right(time_keys, match_time) - flag
    if index < 0 or index >= len(time_keys):
        raise IndexError(_("无法找到合适的附近时间点"))

    return index
