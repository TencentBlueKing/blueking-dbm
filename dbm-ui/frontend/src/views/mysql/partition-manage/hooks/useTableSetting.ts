/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
 */

import { shallowRef } from 'vue';

import { listColumnsCache } from '@helper/local-cache';

import { t } from '@locales/index';

const TABLE_COLUMN_CACHE = 'hdfs_cluster_list_columns';

export default function () {
  const cache = listColumnsCache.getItem(TABLE_COLUMN_CACHE) || {};

  const setting = shallowRef({
    fields: [
      {
        label: '策略 ID',
        field: 'id',
        disabled: true,
      },
      {
        label: t('集群域名'),
        field: 'immute_domain',
        disabled: true,
      },
      {
        label: t('DB 名'),
        field: 'dblike',
      },
      {
        label: t('表名'),
        field: 'tblike',
      },
      {
        label: t('分区字段'),
        field: 'partition_columns',
      },
      {
        label: t('分区字段类型'),
        field: 'partition_column_type',
      },
      {
        label: '分区间隔（天）',
        field: 'partition_time_interval',
      },
      {
        label: '数据过期时间（天）',
        field: 'expire_time',
      },
      {
        label: '最近一次执行状态',
        field: 'status',
      },
      {
        label: '最近一次执行时间',
        field: 'execute_time',
      },
    ],
    checked: cache.columns || [
      'id',
      'immute_domain',
      'dblike',
      'tblike',
      'partition_columns',
      'partition_column_type',
      'partition_time_interval',
      'expire_time',
      'status',
      'execute_time',
    ],
    size: cache.size || 'small',
  });

  const handleChange = ({ checked, size }: { checked: Array<string>; size: string }) => {
    listColumnsCache.setItem(TABLE_COLUMN_CACHE, {
      columns: checked,
      size,
    });

    setting.value = {
      ...setting.value,
      checked,
      size,
    };
  };

  return {
    setting,
    handleChange,
  };
}
