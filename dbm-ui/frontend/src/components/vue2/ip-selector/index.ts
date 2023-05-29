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
} from '@services/ip';

import { t } from '@locales/index';

import createFactory from './index.js';


/**
 * 创建 ip selector 组件
 */
export const ipSelector = createFactory({
  version: '1',
  panelList: ['staticTopo', 'manualInput'],
  unqiuePanelValue: false,
  hostTableCustomColumnList: [
    {
      key: 'cpu',
      index: 4,
      width: '100px',
      label: 'CPU',
      renderCell: (
        h: (tag: string, value: string) => any,
        row: any,
      ) => h('span', row.bk_cpu ? `${row.bk_cpu} ${t('核')}` : '--'),
    },
    {
      key: 'memo',
      index: 5,
      width: '100px',
      label: t('内存_MB'),
      field: 'bk_mem',
    },
    {
      key: 'disk',
      index: 6,
      width: '100px',
      label: t('磁盘_GB'),
      field: 'bk_disk',
    },
  ],
  hostTableRenderColumnList: ['ip', 'ipv6', 'cloudArea', 'alive', 'cpu', 'memo', 'disk'],
  fetchTopologyHostCount: getHostTopo,
  fetchTopologyHostsNodes: getHosts,
  fetchTopologyHostIdsNodes: getHostIdInfos,
  fetchHostsDetails: getHostDetails,
  fetchHostCheck: checkHost,
  fetchCustomSettings: getIpSelectorSettings,
  updateCustomSettings: updateIpSelectorSettings,
  fetchConfig: () => {
    const { pathname, origin } = window.location;

    const pathnames = pathname.split('/');
    pathnames.pop();
    pathnames.push('whitelist');
    return Promise.resolve({
      bk_dbm_whitelist: origin + pathnames.join('/'),
    });
  },
});
