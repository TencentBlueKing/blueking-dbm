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

import { t } from '@locales/index';

import type { TableProps } from '@/types/bkui-vue';

const getSettings = (role?: string) => ({
  fields: [
    {
      label: role ? role.charAt(0).toUpperCase() + role.slice(1) : t('实例'),
      field: 'instance_address',
      disabled: true,
    },
    {
      label: t('角色'),
      field: 'role',
    },
    {
      label: t('实例状态'),
      field: 'status',
    },
    {
      label: t('云区域'),
      field: 'cloud_area',
    },
    {
      label: t('Agent状态'),
      field: 'alive',
    },
    {
      label: t('主机名称'),
      field: 'host_name',
    },
    {
      label: t('OS名称'),
      field: 'os_name',
    },
    {
      label: t('所属云厂商'),
      field: 'cloud_vendor',
    },
    {
      label: t('OS类型'),
      field: 'os_type',
    },
    {
      label: t('主机ID'),
      field: 'host_id',
    },
    {
      label: 'Agent ID',
      field: 'agent_id',
    },
  ],
  checked: ['instance_address', 'role', 'cloud_area', 'alive', 'host_name'],
} as TableProps['settings']);

export default getSettings;
