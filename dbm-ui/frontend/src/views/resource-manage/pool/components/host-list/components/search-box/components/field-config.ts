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

import _ from 'lodash';

import { getBizs } from '@services/source/cmdb';
import { fetchMountPoints } from '@services/source/dbresourceResource';
import { getResourceSpec } from '@services/source/dbresourceSpec';
import { fetchDbTypeList } from '@services/source/infras';
import { getCloudList } from '@services/source/ipchooser';

import { ipv4 } from '@common/regex';

import { t } from '@locales/index';

type Config = {
  component: string;
  flex?: number;
  getNameByKey?: (value: string | number, item: any) => string | undefined;
  label: string;
  service?: (params?: any) => Promise<Array<any>> | Promise<any>;
  type: 'number' | 'string' | 'array' | 'rang';
  validator?: (value: any) => boolean | string;
};

export default {
  agent_status: {
    component: 'agent_status',
    label: t('Agent 状态'),
    type: 'number',
  },
  bk_cloud_ids: {
    component: 'bk_cloud_ids',
    getNameByKey: (value: string, item: { bk_cloud_id: number; bk_cloud_name: string }) => {
      if (value === `${item.bk_cloud_id}`) {
        return item.bk_cloud_name;
      }
      return undefined;
    },
    label: t('管控区域'),
    service: getCloudList,
    type: 'array',
  },
  city: {
    component: 'city',
    label: t('地域 - 园区'),
    type: 'string',
  },
  cpu: {
    component: 'cpu',
    label: t('CPU(核)'),
    type: 'rang',
    validator: (value: undefined | [number, number]) => {
      if (!value || value.length < 1) {
        return true;
      }
      const [min, max] = value;
      if (min && max && min > max) {
        return t('请输入合理的范围值');
      }
      return true;
    },
  },
  device_class: {
    component: 'device_class',
    label: t('机型'),
    type: 'string',
  },
  disk: {
    component: 'disk',
    label: t('磁盘(G)'),
    type: 'rang',
    validator: (value: undefined | [number, number]) => {
      if (!value || value.length < 1) {
        return true;
      }
      const [min, max] = value;
      if (min && max && min > max) {
        return t('请输入合理的范围值');
      }
      return true;
    },
  },
  disk_type: {
    component: 'disk_type',
    label: t('磁盘类型'),
    type: 'string',
  },
  for_biz: {
    component: 'for_biz',
    getNameByKey: (value: string, item: { bk_biz_id: number; display_name: string }) => {
      if (value === `${item.bk_biz_id}`) {
        return item.display_name;
      }
      return undefined;
    },
    label: t('所属业务'),
    service: getBizs,
    type: 'string',
  },
  hosts: {
    component: 'hosts',
    flex: 2,
    label: 'IP',
    type: 'array',
    validator: (value: string[]) => {
      if (!value || value.length < 1) {
        return true;
      }
      const errorValue = value.filter((item) => !ipv4.test(_.trim(item)));
      if (errorValue.length > 0) {
        return t('IP 格式错误:n', { n: errorValue.join(',') });
      }
      return true;
    },
  },
  labels: {
    component: 'labels',
    label: t('标签'),
    type: 'string',
  },
  mem: {
    component: 'mem',
    label: t('内存(G)'),
    type: 'rang',
    validator: (value: undefined | [number, number]) => {
      if (!value || value.length < 1) {
        return true;
      }
      const [min, max] = value;
      if (min && max && min > max) {
        return t('请输入合理的范围值');
      }
      return true;
    },
  },
  mount_point: {
    component: 'mount_point',
    label: t('磁盘挂载点'),
    service: fetchMountPoints,
    type: 'string',
  },
  os_type: {
    component: 'os_type',
    label: t('操作系统类型'),
    type: 'string',
  },
  resource_type: {
    component: 'resource_type',
    getNameByKey: (value: string, item: { id: string; name: string }) => {
      if (value === item.id) {
        return item.name;
      }
      return undefined;
    },
    label: t('所属DB类型'),
    service: fetchDbTypeList,
    type: 'string',
  },
  spec_id: {
    component: 'spec',
    getNameByKey: (value: number, item: { spec_id: number; spec_name: string }) => {
      if (value === item.spec_id) {
        return item.spec_name;
      }
      return undefined;
    },
    label: t('规格'),
    service: (value: number) => getResourceSpec({ spec_id: value }),
    type: 'number',
  },
  subzone_ids: {
    component: 'city',
    label: t('地域 - 园区'),
    type: 'array',
  },
} as Record<string, Config>;
