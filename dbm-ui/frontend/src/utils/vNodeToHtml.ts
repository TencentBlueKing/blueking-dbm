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

import type { VNode } from 'vue';

/**
 * vue node transform html string | element
 * @param vNode vue node
 * @returns html string | html element
 */
export function vNodeToHtml(vNode: VNode | string): string | HTMLElement {
  if  (typeof vNode === 'string') {
    return vNode;
  }

  const { type, children, props  } = vNode;
  if (typeof children === 'string') {
    return children;
  }

  const el = document.createElement(type as string);
  if (props) {
    const keys = Object.keys(props);
    for (const key of keys) {
      if (key === 'class') {
        el.className = props.class || '';
        continue;
      }
      if (key === 'style') {
        el.style.cssText = props.style || '';
        continue;
      }
      el.setAttribute(key, props[key]);
    }
  }

  if (Array.isArray(children)) {
    for (const childVNode of children) {
      el.append(vNodeToHtml(childVNode as VNode));
    }
  }

  return el;
}
