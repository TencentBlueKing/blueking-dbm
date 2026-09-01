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

import _ from 'lodash';
import { onBeforeUnmount, onMounted, type Ref, shallowRef } from 'vue';

export default function (tableContentRef: Ref<HTMLElement | null>) {
  const leftFixedStyles = shallowRef({});
  const rightFixedStyles = shallowRef({});
  const isFixedLeft = ref(false);
  const isFixedRight = ref(false);

  const handleHorizontalScroll = _.throttle(() => {
    const tableEl = tableContentRef.value as HTMLElement;
    if (!tableEl) return;
    const { scrollLeft } = tableEl;
    const tableWrapperWidth = tableEl.getBoundingClientRect().width;
    const tableWidth = tableEl.querySelector('table')!.getBoundingClientRect().width;
    if (scrollLeft === 0) {
      leftFixedStyles.value = {
        display: 'none',
      };
      isFixedLeft.value = false;
    } else {
      const fixedWidth = Array.from(tableEl.querySelectorAll('th.fixed-left-column')).reduce(
        (result, itemEl) => result + itemEl.getBoundingClientRect().width,
        0,
      );

      leftFixedStyles.value = {
        width: `${fixedWidth}px`,
      };
      isFixedLeft.value = true;
    }
    if (tableWrapperWidth + scrollLeft >= tableWidth) {
      rightFixedStyles.value = {
        display: 'none',
      };
      isFixedRight.value = false;
    } else {
      const fixedWidth = Array.from(tableEl.querySelectorAll('th.fixed-right-column')).reduce(
        (result, itemEl) => result + itemEl.getBoundingClientRect().width,
        0,
      );
      rightFixedStyles.value = {
        width: `${fixedWidth}px`,
      };
      isFixedRight.value = true;
    }
  }, 30);

  onMounted(() => {
    const tableEl = tableContentRef.value as HTMLElement;
    tableEl.addEventListener('scroll', handleHorizontalScroll);
    onBeforeUnmount(() => {
      tableEl.removeEventListener('scroll', handleHorizontalScroll);
    });
  });

  return {
    fixedLeft: isFixedLeft,
    fixedRight: isFixedRight,
    initalScroll: handleHorizontalScroll,
    leftFixedStyles,
    rightFixedStyles,
  };
}
