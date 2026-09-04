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

import { h } from 'vue';

export const filterIcon = h(
  'span',
  {
    style: {
      alignItems: 'center',
      display: 'inline-flex',
      justifyContent: 'center',
    },
  },
  [
    h(
      'svg',
      {
        style: {
          fill: 'currentcolor',
          height: '1em',
          overflow: 'hidden',
          verticalAlign: 'middle',
          width: '1em',
        },
        viewBox: '0 0 1024 1024',
        xmlns: 'http://www.w3.org/2000/svg',
      },
      [
        h('path', {
          d: 'M860.8 128H163.2a32 32 0 0 0-27.36 52l295.2 336 0.96 0V896l160-82.72V516.8l0.96 0 295.2-336A32 32 0 0 0 860.8 128Z',
          style: '',
        }),
      ],
    ),
  ],
);

export const sortIcon = h(
  'span',
  {
    style: {
      alignItems: 'center',
      display: 'inline-flex',
      justifyContent: 'center',
    },
  },
  [
    h(
      'svg',
      {
        style: {
          fill: 'currentcolor',
          height: '1em',
          overflow: 'hidden',
          verticalAlign: 'middle',
          width: '1em',
        },
        viewBox: '0 0 1024 1024',
        xmlns: 'http://www.w3.org/2000/svg',
      },
      [
        h('path', {
          d: 'M512 704L96 256 187.04 256 512 256 836.96 256 928 256 512 704z',
          style: '',
        }),
      ],
    ),
  ],
);
