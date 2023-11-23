/*
  TencentBlueKing is pleased to support the open source community by making
  蓝鲸智云 - 审计中心 (BlueKing - Audit Center) available.
  Copyright (C) 2023 THL A29 Limited,
  a Tencent company. All rights reserved.
  Licensed under the MIT License (the "License");
  you may not use this file except in compliance with the License.
  You may obtain a copy of the License at http://opensource.org/licenses/MIT
  Unless required by applicable law or agreed to in writing,
  software distributed under the License is distributed on
  an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
  either express or implied. See the License for the
  specific language governing permissions and limitations under the License.
  We undertake not to change the open source license (MIT license) applicable
  to the current version of the project delivered to anyone in the future.
*/
import type {
  ObjectDirective,
} from 'vue';

import './index.css';

interface Cursor {
  __bk_dbm_cursor__: {
    mouseEnterHandler: (event: MouseEvent) => void;
    mouseMoveHandler: (event: MouseEvent) => void;
    mouseLeaveHandler: (event: MouseEvent) => void;
    element: HTMLElement;
  }
}

type TargetEl = HTMLElement & Cursor


/* eslint-disable no-param-reassign,no-underscore-dangle */

const init = function (el: HTMLElement & Cursor) {
  el.__bk_dbm_cursor__.mouseMoveHandler = function (event: MouseEvent): void {
    const { pageX, pageY } = event;
    const elLeft = pageX + 12;
    const elTop = pageY;
    el.__bk_dbm_cursor__.element.style.left = `${elLeft}px`;
    el.__bk_dbm_cursor__.element.style.top = `${elTop}px`;
  };
  el.__bk_dbm_cursor__.mouseEnterHandler = function () {
    const element = document.createElement('div');
    element.id = 'directive-ele';
    element.style.position = 'absolute';
    element.style.zIndex = '999999';
    element.style.width = '18px';
    element.style.height = '18px';
    el.__bk_dbm_cursor__.element = element;
    document.body.appendChild(element);

    element.classList.add('cursor-element');
    el.addEventListener('mousemove', el.__bk_dbm_cursor__.mouseMoveHandler);
  };

  el.__bk_dbm_cursor__.mouseLeaveHandler = function () {
    el.__bk_dbm_cursor__.element && el.__bk_dbm_cursor__.element.remove();
    el.__bk_dbm_cursor__ = {} as Cursor['__bk_dbm_cursor__'];
    el.removeEventListener('mousemove', el.__bk_dbm_cursor__.mouseMoveHandler);
  };
  el.addEventListener('mouseenter', el.__bk_dbm_cursor__.mouseEnterHandler);
  el.addEventListener('mouseleave', el.__bk_dbm_cursor__.mouseLeaveHandler);
};

const destroy = function (el: HTMLElement & Cursor) {
  el.__bk_dbm_cursor__.element && el.__bk_dbm_cursor__.element.remove();
  el.removeEventListener('mouseenter', el.__bk_dbm_cursor__.mouseEnterHandler);
  el.removeEventListener('mousemove', el.__bk_dbm_cursor__.mouseMoveHandler);
  el.removeEventListener('mouseleave', el.__bk_dbm_cursor__.mouseLeaveHandler);
  el.__bk_dbm_cursor__ = {} as Cursor['__bk_dbm_cursor__'];
};

export default {
  mounted(el: HTMLElement) {
    (el as TargetEl).__bk_dbm_cursor__ = {} as Cursor['__bk_dbm_cursor__'];
    init(el as TargetEl);
  },
  update(el: HTMLElement) {
    destroy(el as TargetEl);
    init(el as TargetEl);
  },
  unmounted(el: HTMLElement) {
    destroy(el as TargetEl);
  },
} as ObjectDirective;

