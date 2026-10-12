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
from rest_framework import serializers

from backend.dbm_aiagent.mcp_tools.oracle.constants import ORACLE_MAX_ROWS
from backend.dbm_aiagent.mcp_tools.oracle.serializers.basic_info import OracleAddrMixin


class GetTablespaceUsageInputSerializer(OracleAddrMixin):
    limit = serializers.IntegerField(required=False, default=ORACLE_MAX_ROWS, min_value=1, max_value=ORACLE_MAX_ROWS)


class GetTablespaceUsageOutputSerializer(serializers.Serializer):
    tablespaces = serializers.ListField(child=serializers.DictField())
    count = serializers.IntegerField()


class GetUndoUsageInputSerializer(OracleAddrMixin):
    pass


class GetUndoUsageOutputSerializer(serializers.Serializer):
    undo_extents = serializers.ListField(child=serializers.DictField())


class GetSgaPgaUsageInputSerializer(OracleAddrMixin):
    pass


class GetSgaPgaUsageOutputSerializer(serializers.Serializer):
    sga = serializers.ListField(child=serializers.DictField())
    pga = serializers.ListField(child=serializers.DictField())
