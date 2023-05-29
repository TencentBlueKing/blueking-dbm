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
import logging
import operator
from collections import ChainMap
from functools import reduce

from django.db.models import Q
from iam import Converter, DjangoQuerySetConverter
from iam.eval.constants import KEYWORD_BK_IAM_PATH_FIELD_SUFFIX, OP
from iam.eval.expression import field_value_convert

logger = logging.getLogger("root")


class MoreLevelIamPathConverter(DjangoQuerySetConverter):
    def _iam_path_(self, left, right):
        return reduce(operator.and_, [Q(**{field: right[field]}) for field in left.split(",")])

    def operator_map(self, operator, field, value):
        if field.endswith(KEYWORD_BK_IAM_PATH_FIELD_SUFFIX) and operator == OP.STARTS_WITH:
            return self._iam_path_


class NotifyGroupDjangoQuerySetConverter(MoreLevelIamPathConverter):
    """告警组的策略转换器"""

    def _iam_path_(self, left, right):
        return reduce(operator.and_, [Q(**{field: right[field]}) for field in left.split(",") if field in right])


class InterfaceConverter(Converter):
    """接口转换器，接口转换只考虑支持and查询"""

    def __init__(self, key_mapping=None, value_hooks=None):
        super(InterfaceConverter, self).__init__(key_mapping)

        self.value_hooks = value_hooks or {}

    def _positive(self, fmt, left, right):
        kwargs = {fmt.format(left): right}
        return kwargs

    def _not_eq(self, left, right):
        pass

    def _not_in(self, left, right):
        pass

    def _not_contains(self, left, right):
        pass

    def _starts_with(self, left, right):
        pass

    def _not_starts_with(self, left, right):
        pass

    def _ends_with(self, left, right):
        pass

    def _not_ends_with(self, left, right):
        pass

    def _lt(self, left, right):
        pass

    def _lte(self, left, right):
        pass

    def _gt(self, left, right):
        pass

    def _gte(self, left, right):
        pass

    def _any(self, left, right):
        pass

    def _or(self, content):
        pass

    def _in(self, left, right):
        return self._positive("{}s", left, right)

    def _eq(self, left, right):
        return self._positive("{}", left, right)

    def _contains(self, left, right):
        return self._positive("{}__contains", left, right)

    def _string_contains(self, left, right):
        return self._positive("{}__contains", left, right)

    def _and(self, content):
        return dict(ChainMap(*[self.convert(c) for c in content]))

    def operator_map(self, operator, field, value):
        return None

    def convert(self, data):
        op = data["op"]

        if op == OP.AND:
            return self._and(data["content"])

        # 只支持and的策略过滤
        value, field = data["value"], data["field"]
        op_func = self.operator_map(op, field, value)

        if not op_func:
            op_func = {OP.EQ: self._eq, OP.IN: self._in}.get(op)

        if op_func is None:
            raise ValueError("invalid op %s" % op)

        # 权限中心保留字预处理
        field, value = field_value_convert(op, field, value)

        # key mapping
        if self.key_mapping and field in self.key_mapping:
            field = self.key_mapping.get(field)
        # value hooks
        if (field in self.value_hooks) and callable(self.value_hooks[field]):
            value = self.value_hooks[field](value)

        return op_func(field, value)
