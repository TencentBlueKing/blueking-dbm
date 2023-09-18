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

const TABLE_COLUMN_CACHE = 'resource_pool_list_columns';

export default function () {
  const cache = listColumnsCache.getItem(TABLE_COLUMN_CACHE) || {};
  const setting = shallowRef({
    fields: [
      {
        label: 'IP',
        field: 'ip',
        disabled: true,
      },
      {
        label: t('管控区域'),
        field: 'bk_cloud_name',
      },
      {
        label: t('Agent 状态'),
        field: 'agent_status',
      },
      {
        label: t('专用业务'),
        field: 'for_bizs',
        disabled: true,
      },
      {
        label: t('专用 DB'),
        field: 'resource_types',
        disabled: true,
      },
      {
        label: t('机型'),
        field: 'device_class',
      },
      {
        label: t('地域'),
        field: 'city',
      },
      {
        label: t('园区'),
        field: 'sub_zone',
      },
      {
        label: t('CPU(核)'),
        field: 'bk_cpu',
      },
      {
        label: t('内存(G)'),
        field: 'bk_mem',
      },
      {
        label: t('磁盘容量(G)'),
        field: 'bk_disk',
      },
    ],
    checked: cache.columns || [
      'ip',
      'bk_cloud_name',
      'agent_status',
      'for_bizs',
      'resource_types',
      'device_class',
      'city',
      'sub_zone',
      'bk_cpu',
      'bk_mem',
      'bk_disk',
    ],
    size: cache.size || 'small',
  });

  const handleChange = ({ checked, size }: { checked: Array<string>, size: string }) => {
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
