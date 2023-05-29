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

import { getCurrentScope, onScopeDispose, type Ref } from 'vue';

import {
  type MaybeElementRef,
  unrefElement,
  useResizeObserver,
} from '@vueuse/core';

function getFooter(el: HTMLElement) {
  const nodes = Array.from(el.parentElement?.children || []) as Array<HTMLElement>;

  return nodes.find(child => child.className.includes('bk-modal-footer'));
}

/**
 * 用于 side slider 设置底部按钮 sticky 布局
 */
export const useStickyFooter = (
  target: MaybeElementRef,
  footerTarget?: MaybeElementRef,
  stickyClass = 'is-sticky-footer',
): {
    isTriggered: Ref<boolean>,
    stop: () => void,
  } => {
  const isTriggered = ref(false);

  const stop = watch(() => unrefElement(target), (el) => {
    const content = el?.closest?.('.bk-modal-content') as HTMLElement;
    if (content) {
      const footer = unrefElement(footerTarget) ?? getFooter(content);
      if (footer === undefined) return;

      useResizeObserver(content, () => {
        isTriggered.value = content.scrollHeight !== content.offsetHeight;
        if (isTriggered.value) {
          footer.classList.add(stickyClass);
        } else {
          footer.classList.remove(stickyClass);
        }
      });
    }
  }, { immediate: true, flush: 'post' });

  if (getCurrentScope()) {
    onScopeDispose(stop);
  }

  return {
    isTriggered,
    stop,
  };
};

export type useStickyFooterReturn = ReturnType<typeof useStickyFooter>;
