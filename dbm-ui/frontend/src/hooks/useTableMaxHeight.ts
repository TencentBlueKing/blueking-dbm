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

import type { Ref } from 'vue';

/**
 * 响应式获取 table 最大高度
 * @param occupiedHeight 被占用高度
 * @param minHeight 自定义最小高度，若剩余高度小于该值则返回该值
 * @returns 屏幕剩余高度 | 自定义最小高度
 */
export const useTableMaxHeight = (occupiedHeight: Ref<number> | number, minHeight = 200) => {
  const innerHeight = ref(window.innerHeight);

  const tableHeight = computed(() => {
    const remainingHeight = innerHeight.value - unref(occupiedHeight);
    return remainingHeight > minHeight ? remainingHeight : minHeight;
  });

  /**
   * resize handler
   */
  const handleResize = () => {
    innerHeight.value = window.innerHeight;
  };

  /**
   * listener resize
   */
  window.addEventListener('resize', handleResize);
  onBeforeUnmount(() => {
    window.removeEventListener('resize', handleResize);
  });

  return tableHeight;
};
