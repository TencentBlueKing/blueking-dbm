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

import {
  checkHost,
  getHostDetails,
  getHostIdInfos,
  getHosts,
  getHostTopo,
  getIpSelectorSettings,
  updateIpSelectorSettings,
} from '@services/source/ipchooser';

import { t } from '@locales/index';

import createFactory from './index.js';

/**
 * 创建 ip selector 组件
 */
export const ipSelector = createFactory({
  fetchConfig: () => {
    const { origin, pathname } = window.location;

    const pathnames = pathname.split('/');
    pathnames.pop();
    pathnames.push('whitelist');
    return Promise.resolve({
      bk_dbm_whitelist: origin + pathnames.join('/'),
    });
  },
  fetchCustomSettings: getIpSelectorSettings,
  fetchHostCheck: checkHost,
  fetchHostsDetails: getHostDetails,
  fetchTopologyHostCount: getHostTopo,
  fetchTopologyHostIdsNodes: getHostIdInfos,
  fetchTopologyHostsNodes: getHosts,
  hostTableCustomColumnList: [
    {
      index: 4,
      key: 'bk_rack_id',
      label: t('机架ID'),
      renderCell: (h: (tag: string, value: string) => any, row: any) => h('span', row.bk_rack_id || '--'),
      width: '100px',
    },
    {
      index: 5,
      key: 'bk_svr_device_class_name',
      label: t('机型'),
      renderCell: (h: (tag: string, value: string) => any, row: any) => h('span', row.bk_svr_device_class_name || '--'),
      width: '120px',
    },
    {
      index: 7,
      key: 'cpu',
      label: 'CPU',
      renderCell: (h: (tag: string, value: string) => any, row: any) =>
        h('span', row.bk_cpu ? `${row.bk_cpu} ${t('核')}` : '--'),
      width: '100px',
    },
    {
      field: 'bk_mem',
      index: 8,
      key: 'memo',
      label: t('内存_MB'),
      width: '100px',
    },
    {
      field: 'bk_disk',
      index: 9,
      key: 'disk',
      label: t('磁盘_GB'),
      width: '100px',
    },
    {
      field: 'bk_sub_zone',
      index: 10,
      key: 'zone',
      label: t('所在园区'),
      width: '100px',
    },
  ],
  hostTableRenderColumnList: [
    'ip',
    'ipv6',
    'zone',
    'bk_rack_id',
    'bk_svr_device_class_name',
    'cloudArea',
    'alive',
    'cpu',
    'memo',
    'disk',
  ],
  panelList: ['staticTopo', 'manualInput'],
  unqiuePanelValue: false,
  updateCustomSettings: updateIpSelectorSettings,
  version: '2',
});
