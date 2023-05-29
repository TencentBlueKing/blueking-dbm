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

// import type { ComponentResolver, SideEffectsInfo } from '../../types'
// import { kebabCase } from '../utils'
// type ComponentResolver = {};
// type SideEffectsInfo = {};
export function kebabCase(key: string) {
  const result = key.replace(/([A-Z])/g, ' $1').trim();
  return result.split(' ').join('-')
    .toLowerCase();
}

export interface BkuiVueResolverOptions {
  /**
   * import style along with components
   * @default 'css'
   */
  importStyle?: boolean | 'css' | 'less'
  /**
   * resolve `bkui-vue' icons
   * @default false
   */
  resolveIcons?: boolean
}

function getSideEffects(importName: string, options: BkuiVueResolverOptions): string | undefined {
  const { importStyle = 'css' } = options;

  if (!importStyle) return;

  const compName = kebabCase(importName);
  let fileName = kebabCase(importName);

  if (['menu-item', 'menu-group'].includes(compName)) return;

  if (compName === 'submenu') {
    fileName = 'menu';
  }

  if (importStyle === 'less') {
    return `bkui-vue/lib/${fileName}/${compName}.less`;
  }

  return `bkui-vue/lib/${fileName}/${compName}.css`;
}

export function BkuiVueResolver(options: BkuiVueResolverOptions = {}) {
  return {
    type: 'component',
    resolve: (name: string) => {
      if (name.match(/^Bk/)) {
        const importName = name.slice(2);
        return {
          name: importName,
          from: 'bkui-vue/lib',
          sideEffects: getSideEffects(importName, options),
        };
      }
    },
  };
}
