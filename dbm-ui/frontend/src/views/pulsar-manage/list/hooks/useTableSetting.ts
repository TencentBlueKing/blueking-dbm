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

const TABLE_COLUMN_CACHE = 'pulsar_cluster_list_columns';

export default function () {
  const cache = listColumnsCache.getItem(TABLE_COLUMN_CACHE) || {};
  const setting = shallowRef({
    fields: [
      {
        label: 'ID',
        field: 'id',
      },
      {
        label: t('集群名称'),
        field: 'cluster_name',
        disabled: true,
      },
      {
        label: t('域名'),
        field: 'domain',
      },
      {
        label: t('版本'),
        field: 'major_version',
      },
      {
        label: t('状态'),
        field: 'status',
      },
      {
        label: 'Bookkeeper',
        field: 'pulsar_bookkeeper',
      },
      {
        label: 'Zookeeper',
        field: 'pulsar_zookeeper',
      },
      {
        label: 'Broker',
        field: 'pulsar_broker',
      },
      {
        label: t('创建人'),
        field: 'creator',
      },
      {
        label: t('部署时间'),
        field: 'create_at',
      },
    ],
    checked: cache.columns || [
      'cluster_name',
      'domain',
      'major_version',
      'status',
      'pulsar_bookkeeper',
      'pulsar_zookeeper',
      'pulsar_broker',
      'creator',
      'create_at',
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
