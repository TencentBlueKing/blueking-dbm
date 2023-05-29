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

import type { DirectiveBinding } from 'vue';

import './index.less';

interface CursorElement extends HTMLElement {
  dbCursor: HTMLElement | null,
  mouseEnterHandler: (event: MouseEvent) => void,
  mouseMoveHandler: (event: MouseEvent) => void,
  mouseLeaveHandler: (event: MouseEvent) => void,
}

const defaultOptions = {
  active: true,
  offset: [
    12, 0,
  ],
  cls: 'db-cursor',
};

const init = function (el: CursorElement, binding: DirectiveBinding) {
  // eslint-disable-next-line
  el.mouseEnterHandler = function () {
    const element = document.createElement('div');
    element.id = 'directive-ele';
    element.style.position = 'absolute';
    element.style.zIndex = '999999';
    element.style.width = '18px';
    element.style.height = '18px';
    // eslint-disable-next-line
    el.dbCursor = element;
    document.body.appendChild(element);

    element.classList.add(binding.value?.cls || defaultOptions.cls);
    el.addEventListener('mousemove', el.mouseMoveHandler);
  };

  // eslint-disable-next-line
  el.mouseMoveHandler = function (event) {
    const { pageX, pageY } = event;
    const elLeft = pageX + defaultOptions.offset[0];
    const elTop = pageY + defaultOptions.offset[1];
    if (el.dbCursor) {
      // eslint-disable-next-line
      el.dbCursor.style.left = `${elLeft}px`;
      // eslint-disable-next-line
      el.dbCursor.style.top = `${elTop}px`;
    }
  };

  // eslint-disable-next-line
  el.mouseLeaveHandler = function () {
    el.dbCursor && el.dbCursor.remove();
    // eslint-disable-next-line
    el.dbCursor = null;
    el.removeEventListener('mousemove', el.mouseMoveHandler);
  };
  if (binding.value.active) {
    el.addEventListener('mouseenter', el.mouseEnterHandler);
    el.addEventListener('mouseleave', el.mouseLeaveHandler);
  }
};

const destroy = function (el: CursorElement) {
  el.dbCursor && el.dbCursor.remove();
  // eslint-disable-next-line
  el.dbCursor = null;
  el.removeEventListener('mouseenter', el.mouseEnterHandler);
  el.removeEventListener('mousemove', el.mouseMoveHandler);
  el.removeEventListener('mouseleave', el.mouseLeaveHandler);
};

const cursor = {
  mounted(el: CursorElement, binding: DirectiveBinding) {
    // eslint-disable-next-line
    binding.value = Object.assign({}, defaultOptions, binding.value);
    init(el, binding);
  },
  updated(el: CursorElement, binding: DirectiveBinding) {
    // eslint-disable-next-line
    binding.value = Object.assign({}, defaultOptions, binding.value);
    destroy(el);
    init(el, binding);
  },
  beforeUnmount(el: CursorElement) {
    destroy(el);
  },
};

export default cursor;
