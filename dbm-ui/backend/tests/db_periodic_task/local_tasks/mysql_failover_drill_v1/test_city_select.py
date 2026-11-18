# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

每座城市一行，只取已启用且城市名非空的配置。
"""

from backend.db_periodic_task.models import MysqlFailoverDrillV1Config


def _conf(city, enabled=True):
    return MysqlFailoverDrillV1Config(cluster_type="tendbha", city=city, enabled=enabled)


def test_enabled_rows_keep_input_order():
    configs = [_conf("上海"), _conf("深圳"), _conf("广州")]
    chosen = MysqlFailoverDrillV1Config.select_enabled(configs)
    assert [conf.city for conf in chosen] == ["上海", "深圳", "广州"]


def test_disabled_row_is_skipped():
    configs = [_conf("上海"), _conf("深圳", enabled=False), _conf("广州")]
    chosen = MysqlFailoverDrillV1Config.select_enabled(configs)
    assert [conf.city for conf in chosen] == ["上海", "广州"]


def test_blank_city_is_skipped():
    configs = [_conf(""), _conf("  ", enabled=True), _conf("上海")]
    chosen = MysqlFailoverDrillV1Config.select_enabled(configs)
    assert [conf.city for conf in chosen] == ["上海"]
