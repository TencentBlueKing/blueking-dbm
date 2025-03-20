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

export default {
  checked: ['ip', 'cpu', 'bk_disk', 'host_name', 'alive'],
  fields: [
    {
      disabled: true,
      field: 'ip',
      label: 'IP',
    },
    {
      field: 'cpu',
      label: t('机型'),
    },
    {
      field: 'bk_idc_name',
      label: t('机房'),
    },
    {
      field: 'cloud_area',
      label: t('管控区域'),
    },
    {
      field: 'alive',
      label: t('Agent状态'),
    },
    {
      field: 'host_name',
      label: t('主机名称'),
    },
    {
      field: 'os_name',
      label: t('OS名称'),
    },
    {
      field: 'cloud_vendor',
      label: t('所属云厂商'),
    },
    {
      field: 'os_type',
      label: t('OS类型'),
    },
    {
      field: 'host_id',
      label: t('主机ID'),
    },
    {
      field: 'agent_id',
      label: 'Agent ID',
    },
  ],
};
