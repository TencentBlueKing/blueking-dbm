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

import tippy, { type Instance, type Placement, type Props, type ReferenceElement } from 'tippy.js';
import type { DirectiveBinding, ObjectDirective } from 'vue';

import './index.css';

interface TooltipsOptions {
  /** 是否展示箭头 */
  arrow: boolean;
  /** 提示内容，\n 会渲染为换行 */
  content: string;
  /** 展示延时，单位 ms */
  delay: number;
  /** 是否禁用 */
  disabled: boolean;
  /** 与目标元素的间距 */
  distance: number;
  /** 追加到弹层根节点的自定义类名 */
  extCls: string;
  onHide: () => void;
  onShow: () => void;
  placement: Placement;
  /** 初始化后立即展示 */
  showOnInit: boolean;
  theme: string;
  trigger: 'click' | 'hover';
}

type TooltipsValue = Partial<TooltipsOptions> | string;

const PLACEMENTS: string[] = [
  'auto',
  'auto-start',
  'auto-end',
  'top',
  'top-start',
  'top-end',
  'bottom',
  'bottom-start',
  'bottom-end',
  'right',
  'right-start',
  'right-end',
  'left',
  'left-start',
  'left-end',
];

const DEFAULT_OPTIONS: TooltipsOptions = {
  arrow: true,
  content: '',
  delay: 500,
  disabled: false,
  distance: 8,
  extCls: '',
  onHide: () => {},
  onShow: () => {},
  placement: 'top',
  showOnInit: false,
  theme: 'dark',
  trigger: 'hover',
};

/**
 * 解析指令入参，支持 v-bk-tooltips="'文案'"、v-bk-tooltips="{ ... }" 与 v-bk-tooltips.right 修饰符
 */
function resolveOptions(binding: DirectiveBinding<TooltipsValue>): TooltipsOptions {
  const options = { ...DEFAULT_OPTIONS };

  const modifierPlacement = Object.keys(binding.modifiers).find((key) => PLACEMENTS.includes(key));
  if (modifierPlacement) {
    options.placement = modifierPlacement as Placement;
  }

  if (typeof binding.value === 'object' && binding.value !== null) {
    Object.assign(options, binding.value);
  } else {
    options.content = binding.value ?? '';
  }

  return options;
}

function toTippyProps(options: TooltipsOptions): Partial<Props> {
  return {
    allowHTML: false,
    // 指定 document.body 可避免 tippy 在 interactive 模式下的无障碍告警
    appendTo: () => document.body,
    arrow: options.arrow,
    content: options.content,
    // 移出目标元素后延时隐藏，便于鼠标移入弹层
    delay: [options.delay, 100],
    hideOnClick: options.trigger === 'click',
    interactive: true,
    // 置空以清除 tippy 写在气泡节点上的行内 max-width，宽度交由样式控制（extCls 才能生效）
    maxWidth: '',
    offset: [0, options.distance],
    onHide: () => {
      options.onHide();
    },
    onShow: () => {
      options.onShow();
    },
    placement: options.placement,
    theme: options.theme === 'light' ? 'dbm-tooltips dbm-tooltips-light' : 'dbm-tooltips',
    trigger: options.trigger === 'click' ? 'click' : 'mouseenter',
  };
}

/**
 * extCls 需同时挂到定位根节点与气泡节点：z-index 作用于根节点，宽度、换行等样式作用于气泡节点
 */
function syncExtCls(instance: Instance, extCls: string) {
  const { popper } = instance;
  const staleCls = popper.getAttribute('data-ext-cls') ?? '';
  if (staleCls === extCls) {
    return;
  }

  const staleList = staleCls.split(' ').filter(Boolean);
  const nextList = extCls.split(' ').filter(Boolean);
  const classLists = [popper.classList];
  if (popper.firstElementChild) {
    classLists.push(popper.firstElementChild.classList);
  }

  classLists.forEach((classList) => {
    if (staleList.length > 0) {
      classList.remove(...staleList);
    }
    if (nextList.length > 0) {
      classList.add(...nextList);
    }
  });

  popper.setAttribute('data-ext-cls', extCls);
}

// eslint-disable-next-line no-underscore-dangle
const getInstance = (el: HTMLElement) => (el as ReferenceElement)._tippy;

export default {
  beforeUnmount(el) {
    getInstance(el)?.destroy();
  },
  mounted(el, binding) {
    const options = resolveOptions(binding);
    const instance = tippy(el, {
      ...toTippyProps(options),
      showOnCreate: options.showOnInit,
    });

    syncExtCls(instance, options.extCls);

    if (options.disabled) {
      instance.disable();
    }
  },
  updated(el, binding) {
    const instance = getInstance(el);
    if (!instance) {
      return;
    }

    const options = resolveOptions(binding);
    instance.setProps(toTippyProps(options));
    syncExtCls(instance, options.extCls);

    if (options.disabled) {
      instance.disable();
    } else {
      instance.enable();
    }
  },
} as ObjectDirective<HTMLElement, TooltipsValue>;
