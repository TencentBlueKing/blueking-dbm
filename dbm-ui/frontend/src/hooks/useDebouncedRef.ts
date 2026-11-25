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

import { customRef } from 'vue';

export const useDebouncedRef = <T>(value: T, delay = 200) => {
  // setTimeout 在 DOM / Node 类型下返回值不同，用 ReturnType 兼容；首次 clearTimeout 时尚未赋值
  let timeout: ReturnType<typeof setTimeout> | undefined;
  let localValue = value;
  return customRef<T>((track, trigger) => ({
    get() {
      track();
      return localValue;
    },
    set(newValue: T) {
      clearTimeout(timeout);
      timeout = setTimeout(() => {
        localValue = newValue;
        trigger();
      }, delay);
    },
  }));
};
