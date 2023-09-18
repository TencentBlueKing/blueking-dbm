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

import type { Instance, Props } from 'tippy.js';
import type { DirectiveBinding } from 'vue';

import { dbTippy } from '@common/tippy';

type TippyProps = Partial<Props>;

const placements = [
  'top',
  'bottom',
  'right',
  'left',
  'auto',
  'auto-start',
  'auto-end',
  'top-start',
  'top-end',
  'bottom-start',
  'bottom-end',
  'right-start',
  'right-end',
  'left-start',
  'left-end',
];

/**
 * 判断元素是否溢出容器
 * @param {*} el
 * @returns
 */
export function checkOverflow(el: Element) {
  if (!el) return false;

  const createDom = (el: Element, css: CSSStyleDeclaration) => {
    const dom = document.createElement('div');
    const width = parseFloat(css.width) ? `${Math.ceil(parseFloat(css.width))}px` : css.width;
    dom.style.cssText = `
      width: ${width};
      line-height: ${css.lineHeight};
      font-size: ${css.fontSize};
      word-break: ${css.wordBreak};
      padding: ${css.padding};
    `;
    dom.textContent = el.textContent;
    return dom;
  };

  let isOverflow = false;
  try {
    const css = window.getComputedStyle(el, null);
    const lineClamp = css.webkitLineClamp;
    if (lineClamp !== 'none') {
      const targetHeight = parseFloat(css.height);
      const dom = createDom(el, css);
      document.body.appendChild(dom);
      const domHeight = window.getComputedStyle(dom, null).height;
      document.body.removeChild(dom);
      isOverflow = targetHeight < parseFloat(domHeight);
    } else {
      isOverflow = el.clientWidth < el.scrollWidth || el.clientHeight < el.scrollHeight;
    }
  } catch (e) {
    console.warn('There is an error when check element overflow state: ', e);
  }
  return isOverflow;
}


function beforeShow(instance: Instance) {
  const { reference } = instance;
  const { props } = reference._bk_overflow_tips_;
  const isOverflow = checkOverflow(reference as Element);
  if (isOverflow) {
    let { content } = props;
    if (!content) {
      content = props.allowHTML ? reference.innerHTML : reference.textContent;
    }
    instance.setContent(content);
    return true;
  }
  return false;
}

function setupOnShow(props: TippyProps, customProps: TippyProps) {
  props.onShow = (instance) => {
    if (typeof customProps.onShow === 'function') {
      const result = customProps.onShow(instance);
      if (!result) return false;
    }
    const isShow = beforeShow(instance);
    if (!isShow) return false;
  };
}

function setupTheme(props: TippyProps, customProps: TippyProps) {
  const theme = ['db-tippy bk-overflow-tips'];
  if (customProps.theme) {
    theme.push(customProps.theme);
  }
  props.theme = theme.join(' ');
}

function formatModifiers(modifiers: Record<string, boolean>) {
  const keys = Object.entries(modifiers)
    // .filter(([key, value]) => value)
    .map(item => item[0]);
  if (keys.length === 0) return {};

  const props: Record<string, any> = {};
  // 设置 placement
  for (const key of keys) {
    if (placements.includes(key)) {
      props.placement = key;
    }
  }

  return props;
}

const defaultProps = {
  arrow: true,
  interactive: true,
  delay: 150,
  allowHTML: false,
  maxWidth: 600,
  // boundary: 'window',
  placement: 'top',
  appendTo: () => document.body,
};

const overflowTips = {
  mounted(el: Element, binding: DirectiveBinding) {
    const customProps = typeof binding.value === 'object' ? binding.value : formatModifiers(binding.modifiers);
    const props = Object.assign({ ...defaultProps }, customProps);
    setupOnShow(props, customProps);
    setupTheme(props, customProps);
    el._bk_overflow_tips_ = {
      props, // 指令配置的props单独存储方便后续做判断
      instance: dbTippy(el, props),
    };
  },
  updated(el: Element, binding: DirectiveBinding) {
    const { props, instance } = el._bk_overflow_tips_;
    const customProps = typeof binding.value === 'object' ? binding.value : formatModifiers(binding.modifiers);
    Object.assign(props, customProps);
    setupOnShow(props, customProps);
    setupTheme(props, customProps);
    instance.setProps(props);
  },
  beforeUnmount(el: Element) {
    el._tippy && el._tippy.destroy();
    delete el._bk_overflow_tips_;
  },
};


export default overflowTips;
