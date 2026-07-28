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

import { defineStore } from 'pinia';
import { reactive, ref } from 'vue';

import { FilterType } from '@common/const';

/**
 * 全局搜索状态管理 Store
 */
export const useSystemSearchStore = defineStore('SystemSearch', () => {
  // 搜索关键词
  const keyword = ref('');
  // 表单数据（业务、DB类型、资源类型等筛选条件）
  const formData = reactive({
    bk_biz_ids: [] as number[],
    db_types: [] as string[],
    filter_type: FilterType.EXACT,
    resource_types: [] as string[],
  });
  // 是否需要刷新结果页
  const shouldRefresh = ref(false);

  /**
   * 触发结果页刷新（结果页场景下点击搜索/回车时调用）
   */
  const triggerRefresh = (searchKeyword: string, data?: Record<string, any>) => {
    keyword.value = searchKeyword;
    if (data) {
      Object.assign(formData, data);
    }
    shouldRefresh.value = true;
  };

  /**
   * 清除刷新状态（结果页消费后调用）
   */
  const consumeRefresh = () => {
    shouldRefresh.value = false;
  };

  return {
    consumeRefresh,
    formData,
    keyword,
    shouldRefresh,
    triggerRefresh,
  };
});
