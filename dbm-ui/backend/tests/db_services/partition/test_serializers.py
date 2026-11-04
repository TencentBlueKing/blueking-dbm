# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import pytest

from backend.db_services.partition.serializers import PartitionFieldTypeV2Serializer


@pytest.mark.parametrize("partition_column", ["id", "create_time", "column_1"])
def test_partition_field_type_v2_serializer_accepts_valid_column_name(partition_column):
    serializer = PartitionFieldTypeV2Serializer(
        data={
            "bk_biz_id": 1,
            "cluster_id": 1,
            "dblikes": ["test_db"],
            "tblikes": ["test_table"],
            "partition_column": partition_column,
        }
    )

    assert serializer.is_valid(), serializer.errors


@pytest.mark.parametrize("partition_column", ["name' OR '1'='1", "column-name", "1column", "字段"])
def test_partition_field_type_v2_serializer_rejects_invalid_column_name(partition_column):
    serializer = PartitionFieldTypeV2Serializer(
        data={
            "bk_biz_id": 1,
            "cluster_id": 1,
            "dblikes": ["test_db"],
            "tblikes": ["test_table"],
            "partition_column": partition_column,
        }
    )

    assert not serializer.is_valid()
    assert "partition_column" in serializer.errors
