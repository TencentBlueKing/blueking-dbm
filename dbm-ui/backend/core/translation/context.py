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

import typing
from contextlib import contextmanager

import wrapt
from django.utils import translation


@contextmanager
def respect_language(language):
    """Context manager that changes the current translation language for
    all code inside the following block.
    Can e.g. be used inside tasks like this::
        from celery import task
        from apps.utils.translation import respect_language
        @task
        def my_task(language=None):
            with respect_language(language):
                pass
    """
    if language:
        prev = translation.get_language()
        translation.activate(language)
        try:
            yield
        finally:
            translation.activate(prev)
    else:
        yield


GetLanguageFuncT = typing.Callable[
    [typing.Callable, typing.Any, typing.Tuple[typing.Any], typing.Dict[str, typing.Any]], typing.Optional[str]
]


class RespectsLanguage:
    language: typing.Optional[str] = None
    get_language_func: typing.Optional[GetLanguageFuncT] = None

    @staticmethod
    def default_get_language_func(
        wrapped: typing.Callable,
        instance: typing.Any,
        args: typing.Tuple[typing.Any],
        kwargs: typing.Dict[str, typing.Any],
    ) -> typing.Optional[str]:
        language = kwargs.pop("language", None)
        if language:
            return language
        return translation.get_language()

    def __init__(
        self, get_language_func: typing.Optional[GetLanguageFuncT] = None, language: typing.Optional[str] = None
    ):
        """
        :param get_language_func: 获取语言方法
        :param language: 指定语言，优先于 get_language_func
        """
        self.language = language
        self.get_language_func = get_language_func or self.default_get_language_func

    @wrapt.decorator
    def __call__(
        self,
        wrapped: typing.Callable,
        instance: typing.Any,
        args: typing.Tuple[typing.Any],
        kwargs: typing.Dict[str, typing.Any],
    ) -> typing.Any:
        """
        :param wrapped: 被装饰的函数或类方法
        :param instance:
            - 如果被装饰者为普通类方法，该值为类实例
            - 如果被装饰者为 classmethod / 类方法，该值为类
            - 如果被装饰者为类/函数/静态方法，该值为 None
        :param args: 位置参数
        :param kwargs: 关键字参数
        :return:
        """
        language = self.language or self.get_language_func(wrapped, instance, args, kwargs)
        with respect_language(language):
            return wrapped(*args, **kwargs)
