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

import type { ISearchValue } from 'bkui-vue/lib/search-select/utils';

/**
 * 获取 search selector 参数结果
 * @param data search select 组件选择结果
 * @returns 由每项 id 和 values id 字符串组成的对象
 */
export function getSearchSelectorParams<T extends Record<string, any>>(data: ISearchValue[]): T {
  const params = {};
  data.forEach((value: ISearchValue) => {
    Object.assign(params, { [value.id]: (value.values || []).map((item) => item.id).join(',') });
  });

  return params as T;
}
